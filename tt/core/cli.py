#!/usr/bin/env python3
"""
Main CLI entry point for tt-cli
Handles argument parsing and command dispatch
"""

import sys
import argparse
from pathlib import Path

# Import command handlers
from tt.commands import serve, env, device, firmware, status, model, workflow, config, metal, stack, run, ps, logs, chat, doctor
from tt.utils.similarity import find_similar_command


class SmartArgumentParser(argparse.ArgumentParser):
    """
    ArgumentParser with 'did you mean?' suggestions for typos.

    Extends argparse.ArgumentParser to provide helpful suggestions when users
    mistype commands, similar to slack CLI, brew, gh, etc.

    This improves the user experience by helping users quickly recover from
    common typos without having to re-read the entire command list.
    """

    def error(self, message: str):
        """
        Override error() to add 'did you mean?' suggestions.

        Detects invalid choice errors and suggests similar valid commands
        using fuzzy string matching (Ratcliff/Obershelp algorithm via difflib).

        Args:
            message: The error message from argparse
        """
        # Check if this is an "invalid choice" error
        if "invalid choice:" in message:
            # Extract the invalid choice and valid choices from error message
            # Format: "invalid choice: 'X' (choose from 'a', 'b', 'c')"
            try:
                # Parse out the invalid choice
                invalid_start = message.find("'") + 1
                invalid_end = message.find("'", invalid_start)
                invalid_choice = message[invalid_start:invalid_end]

                # Parse out valid choices
                choices_start = message.find("(choose from") + len("(choose from")
                choices_text = message[choices_start:].strip(" )")
                # Extract choices from format: 'a', 'b', 'c'
                valid_choices = [c.strip().strip("'\"") for c in choices_text.split(",")]

                # Find similar command using fuzzy matching
                suggestion = find_similar_command(invalid_choice, valid_choices)

                if suggestion:
                    # Add suggestion to error message
                    message = message.rstrip(")")
                    message += f"\n\nDid you mean '{suggestion}'?"

            except (ValueError, IndexError):
                # If parsing fails, just use original message
                # This ensures we never break existing error handling
                pass

        # Call parent error() which prints message and exits
        super().error(message)


def create_parser():
    """Create argument parser with all subcommands."""
    parser = SmartArgumentParser(
        prog='tt',
        description='Unified CLI for Tenstorrent hardware development',
        epilog='''Run "tt <command> --help" for more information on a command.

Examples:
  tt status                    # Show system status
  tt doctor                    # Check system health
  tt run llama-3.1-8b          # Run a model
  tt ps                        # Show running models
  tt chat                      # Chat with running model
  tt logs my-model             # View model logs
  tt stop my-model             # Stop a model
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--version',
        action='version',
        version='tt-cli 0.1.0',
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output',
    )

    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=False,
    )

    # ========================================================================
    # tt run - Simple model runner (primary workflow)
    # ========================================================================
    run.add_run_parser(subparsers)

    # ========================================================================
    # tt serve - Server management
    # ========================================================================
    serve_parser = subparsers.add_parser(
        'serve',
        help='Manage vLLM servers',
        description='Start and manage vLLM servers',
        epilog='''Examples:
  tt serve start my-model                # Start vLLM server
  tt serve start qwen3 --port 8001       # Use different port
  tt serve status                         # Show running servers
  tt serve status --json                  # JSON output
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    serve_subparsers = serve_parser.add_subparsers(
        dest='serve_command',
        help='Server management commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt serve start
    start_parser = serve_subparsers.add_parser(
        'start',
        help='Start vLLM server',
        description='Start vLLM server with auto-detected optimal parameters',
    )
    start_parser.add_argument(
        'model',
        nargs='?',  # Make model optional - will use active stack if not provided
        help='Model name (e.g., llama-3.1-8b, meta-llama/Llama-3.1-8B-Instruct). If not provided, uses active stack.',
    )
    start_parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Server port (default: 8000)',
    )
    start_parser.add_argument(
        '--max-model-len',
        type=int,
        default=None,
        dest='max_model_len',
        help='Maximum model context length',
    )
    start_parser.add_argument(
        '--max-num-seqs',
        type=int,
        default=None,
        dest='max_num_seqs',
        help='Maximum number of sequences to process in parallel',
    )
    start_parser.add_argument(
        '--tensor-parallel',
        type=int,
        default=None,
        dest='tensor_parallel',
        help='Tensor parallel size',
    )
    start_parser.add_argument(
        '--detach',
        action='store_true',
        help='Run server in background',
    )
    start_parser.add_argument(
        '--models-dir',
        type=str,
        default=None,
        dest='models_dir',
        help='Models directory',
    )
    start_parser.add_argument(
        '--pid-dir',
        type=str,
        default=None,
        dest='pid_dir',
        help='PID file directory',
    )
    start_parser.add_argument(
        '--device-id',
        type=int,
        default=None,
        dest='device_id',
        help='Specific device ID to use (0-3 for 4-chip system). If not specified, uses all devices.',
    )
    start_parser.set_defaults(func=serve.start)

    # tt serve status
    status_parser = serve_subparsers.add_parser(
        'status',
        help='Show running servers',
        description='Show status of running vLLM servers',
    )
    status_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    status_parser.add_argument(
        '--pid-dir',
        type=str,
        default=None,
        dest='pid_dir',
        help='PID file directory',
    )
    status_parser.set_defaults(func=serve.status)

    # ========================================================================
    # tt ps - Show running models (docker-like interface)
    # ========================================================================
    ps_parser = subparsers.add_parser(
        'ps',
        help='Show running models',
        description='List running models in a clean table format (like docker ps)',
        epilog='''Examples:
  tt ps                           # Show all running models
  tt ps --json                    # JSON output
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ps_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    ps_parser.add_argument(
        '--pid-dir',
        type=str,
        default=None,
        dest='pid_dir',
        help='PID file directory',
    )
    ps_parser.set_defaults(func=ps.ps)

    # ========================================================================
    # tt logs - View model logs
    # ========================================================================
    logs.add_logs_parser(subparsers)

    # ========================================================================
    # tt chat - Interactive chat with running model
    # ========================================================================
    chat.add_chat_parser(subparsers)

    # ========================================================================
    # tt stop - Stop server
    # ========================================================================
    stop_parser = subparsers.add_parser(
        'stop',
        help='Stop running server',
    )
    stop_parser.add_argument(
        'model',
        nargs='?',
        help='Model name (omit to stop all)',
    )
    stop_parser.add_argument(
        '--all',
        action='store_true',
        help='Stop all servers',
    )
    stop_parser.add_argument(
        '--device-id',
        type=int,
        default=None,
        dest='device_id',
        help='Specific device ID (for single-device instances)',
    )
    stop_parser.add_argument(
        '--pid-dir',
        type=str,
        default=None,
        dest='pid_dir',
        help='PID file directory',
    )
    stop_parser.set_defaults(func=serve.stop)

    # ========================================================================
    # tt restart - Restart server
    # ========================================================================
    restart_parser = subparsers.add_parser(
        'restart',
        help='Restart server',
    )
    restart_parser.add_argument(
        'model',
        help='Model name',
    )
    restart_parser.set_defaults(func=serve.restart)

    # ========================================================================
    # tt env - Environment management
    # ========================================================================
    env_parser = subparsers.add_parser(
        'env',
        help='Manage Python environments',
        epilog='''Examples:
  tt env ls                              # List available environments
  tt env use vllm                        # Switch to vLLM environment
  tt env check                           # Validate current environment
  tt env fix                             # Auto-fix common issues
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    env_subparsers = env_parser.add_subparsers(
        dest='env_command',
        help='Environment commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt env use
    use_parser = env_subparsers.add_parser(
        'use',
        help='Switch to environment',
    )
    use_parser.add_argument(
        'name',
        help='Environment name (or metal@version for specific version)',
    )
    use_parser.set_defaults(func=env.use)

    # tt env list (and alias: tt env ls)
    list_parser = env_subparsers.add_parser(
        'list',
        help='List available environments',
    )
    list_parser.set_defaults(func=env.list_envs)

    # tt env ls (alias for list)
    ls_parser = env_subparsers.add_parser(
        'ls',
        help='List available environments (alias for list)',
    )
    ls_parser.set_defaults(func=env.list_envs)

    # tt env setup
    setup_parser = env_subparsers.add_parser(
        'setup',
        help='Create new environment',
    )
    setup_parser.add_argument(
        'name',
        help='Environment name',
    )
    setup_parser.add_argument(
        '--python',
        help='Python version (requires uv)',
    )
    setup_parser.set_defaults(func=env.setup)

    # tt env check
    check_parser = env_subparsers.add_parser(
        'check',
        help='Validate current environment',
    )
    check_parser.set_defaults(func=env.check)

    # tt env fix
    fix_parser = env_subparsers.add_parser(
        'fix',
        help='Auto-fix common issues',
    )
    fix_parser.add_argument(
        '--export',
        action='store_true',
        help='Output export commands for eval (use: eval "$(tt env fix --export)")',
    )
    fix_parser.set_defaults(func=env.fix)

    # tt env install-uv
    uv_parser = env_subparsers.add_parser(
        'install-uv',
        help='Install uv for faster operations',
    )
    uv_parser.set_defaults(func=env.install_uv)

    # ========================================================================
    # tt metal - TT-Metal installation management
    # ========================================================================
    metal_parser = subparsers.add_parser(
        'metal',
        help='Manage TT-Metal installations',
        epilog='''Examples:
  tt metal ls                            # List installed versions
  tt metal checkout --tag v0.66.0-rc7    # Install specific version
  tt metal use v0.66.0-rc7               # Set active version
  tt metal info v0.66.0-rc7              # Show installation details
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    metal_subparsers = metal_parser.add_subparsers(
        dest='metal_command',
        help='Metal commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt metal checkout
    checkout_parser = metal_subparsers.add_parser(
        'checkout',
        help='Checkout and build a specific TT-Metal version',
    )
    checkout_parser.add_argument(
        '--tag',
        required=True,
        help='Git tag to checkout (e.g., v0.66.0-rc7)',
    )
    checkout_parser.add_argument(
        '--path',
        help='Installation path (default: ~/tt-metal-versions/<tag>)',
    )
    checkout_parser.add_argument(
        '--python',
        help='Python version to use (default: 3.12)',
    )
    checkout_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing installation',
    )
    checkout_parser.add_argument(
        '--skip-deps',
        action='store_true',
        help='Skip dependency installation',
    )
    checkout_parser.add_argument(
        '--skip-build',
        action='store_true',
        help='Skip build step',
    )
    checkout_parser.add_argument(
        '--skip-env',
        action='store_true',
        help='Skip python_env creation',
    )
    checkout_parser.add_argument(
        '--skip-vllm',
        action='store_true',
        help='Skip vLLM environment creation',
    )
    checkout_parser.add_argument(
        '--build-tt-train',
        action='store_true',
        default=True,
        help='Build with tt-train support (default: True)',
    )
    checkout_parser.add_argument(
        '--set-active',
        action='store_true',
        help='Set as active version after checkout',
    )
    checkout_parser.set_defaults(func=metal.checkout)

    # tt metal list (and alias: tt metal ls)
    metal_list_parser = metal_subparsers.add_parser(
        'list',
        help='List installed TT-Metal versions',
    )
    metal_list_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    metal_list_parser.set_defaults(func=metal.list_installations)

    # tt metal ls (alias for list)
    metal_ls_parser = metal_subparsers.add_parser(
        'ls',
        help='List installed TT-Metal versions (alias for list)',
    )
    metal_ls_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    metal_ls_parser.set_defaults(func=metal.list_installations)

    # tt metal use
    metal_use_parser = metal_subparsers.add_parser(
        'use',
        help='Set active TT-Metal version',
    )
    metal_use_parser.add_argument(
        'version',
        help='Version to set as active',
    )
    metal_use_parser.add_argument(
        '--force',
        action='store_true',
        help='Set as active even if installation has issues',
    )
    metal_use_parser.set_defaults(func=metal.use)

    # tt metal info
    metal_info_parser = metal_subparsers.add_parser(
        'info',
        help='Show installation details',
    )
    metal_info_parser.add_argument(
        'version',
        help='Version to show info for',
    )
    metal_info_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    metal_info_parser.set_defaults(func=metal.info)

    # tt metal remove (and alias: tt metal rm)
    metal_remove_parser = metal_subparsers.add_parser(
        'remove',
        help='Remove a TT-Metal installation',
    )
    metal_remove_parser.add_argument(
        'version',
        help='Version to remove',
    )
    metal_remove_parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt',
    )
    metal_remove_parser.set_defaults(func=metal.remove)

    # tt metal rm (alias for remove)
    metal_rm_parser = metal_subparsers.add_parser(
        'rm',
        help='Remove a TT-Metal installation (alias for remove)',
    )
    metal_rm_parser.add_argument(
        'version',
        help='Version to remove',
    )
    metal_rm_parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt',
    )
    metal_rm_parser.set_defaults(func=metal.remove)

    # tt metal build
    metal_build_parser = metal_subparsers.add_parser(
        'build',
        help='Build a TT-Metal installation',
    )
    metal_build_parser.add_argument(
        'version',
        help='Version to build',
    )
    metal_build_parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean build directory first',
    )
    metal_build_parser.add_argument(
        '--build-tt-train',
        action='store_true',
        default=True,
        help='Build with tt-train support (default: True)',
    )
    metal_build_parser.set_defaults(func=metal.build)

    # tt metal setup
    metal_setup_parser = metal_subparsers.add_parser(
        'setup',
        help='Setup environments for installation',
    )
    metal_setup_parser.add_argument(
        'version',
        help='Version to setup',
    )
    metal_setup_parser.add_argument(
        '--python',
        help='Python version to use (default: 3.12)',
    )
    metal_setup_parser.add_argument(
        '--vllm-only',
        action='store_true',
        help='Only setup vLLM environment',
    )
    metal_setup_parser.set_defaults(func=metal.setup)

    # ========================================================================
    # tt device - Device management
    # ========================================================================
    device_parser = subparsers.add_parser(
        'device',
        help='Manage Tenstorrent devices',
        epilog='''Examples:
  tt device info                         # Show device information
  tt device test                         # Test all devices
  tt device reset                        # Reset devices
  tt device clear                        # Clear device state
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    device_subparsers = device_parser.add_subparsers(
        dest='device_command',
        help='Device commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt device test
    test_parser = device_subparsers.add_parser(
        'test',
        help='Test all devices',
    )
    test_parser.set_defaults(func=device.test)

    # tt device info
    info_parser = device_subparsers.add_parser(
        'info',
        help='Show device information',
    )
    info_parser.set_defaults(func=device.info)

    # tt device reset
    reset_parser = device_subparsers.add_parser(
        'reset',
        help='Reset devices',
    )
    reset_parser.set_defaults(func=device.reset)

    # tt device clear
    clear_parser = device_subparsers.add_parser(
        'clear',
        help='Clear device state and shared memory',
    )
    clear_parser.set_defaults(func=device.clear)

    # ========================================================================
    # tt firmware - Firmware management
    # ========================================================================
    firmware_parser = subparsers.add_parser(
        'firmware',
        help='Manage device firmware',
        epilog='''Examples:
  tt fw current                          # Show current firmware
  tt fw ls                               # List available versions
  tt fw flash v19.4.2 --yes              # Flash firmware version
  tt fw latest --recommended             # Show recommended version
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    firmware_subparsers = firmware_parser.add_subparsers(
        dest='firmware_command',
        help='Firmware commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt firmware list (and alias: tt firmware ls)
    list_fw_parser = firmware_subparsers.add_parser(
        'list',
        help='List available firmware versions',
    )
    list_fw_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    list_fw_parser.add_argument(
        '--recommended',
        action='store_true',
        help='Show only recommended versions for detected hardware',
    )
    list_fw_parser.set_defaults(func=firmware.list_firmware)

    # tt firmware ls (alias for list)
    ls_fw_parser = firmware_subparsers.add_parser(
        'ls',
        help='List available firmware versions (alias for list)',
    )
    ls_fw_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    ls_fw_parser.add_argument(
        '--recommended',
        action='store_true',
        help='Show only recommended versions for detected hardware',
    )
    ls_fw_parser.set_defaults(func=firmware.list_firmware)

    # tt firmware current
    current_fw_parser = firmware_subparsers.add_parser(
        'current',
        help='Show current firmware version',
    )
    current_fw_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    current_fw_parser.set_defaults(func=firmware.current_firmware)

    # tt firmware download
    download_fw_parser = firmware_subparsers.add_parser(
        'download',
        help='Download firmware bundle',
    )
    download_fw_parser.add_argument(
        'version',
        help='Firmware version (e.g., 19.4.2 or v19.4.2)',
    )
    download_fw_parser.add_argument(
        '--output',
        help='Output path (default: ~/.tt/firmware/)',
    )
    download_fw_parser.set_defaults(func=firmware.download)

    # tt firmware flash
    flash_fw_parser = firmware_subparsers.add_parser(
        'flash',
        help='Flash firmware to devices',
    )
    flash_fw_parser.add_argument(
        'version_or_path',
        help='Firmware version or path to .fwbundle file',
    )
    flash_fw_parser.add_argument(
        '--force',
        action='store_true',
        help='Force update ROM',
    )
    flash_fw_parser.add_argument(
        '--no-reset',
        action='store_true',
        dest='no_reset',
        help='Do not reset devices after flash',
    )
    flash_fw_parser.add_argument(
        '--allow-downgrades',
        action='store_true',
        dest='allow_downgrades',
        help='Allow major version downgrades',
    )
    flash_fw_parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt',
    )
    flash_fw_parser.set_defaults(func=firmware.flash)

    # tt firmware verify
    verify_fw_parser = firmware_subparsers.add_parser(
        'verify',
        help='Verify firmware',
    )
    verify_fw_parser.add_argument(
        'version_or_path',
        nargs='?',
        help='Firmware version or path (optional)',
    )
    verify_fw_parser.set_defaults(func=firmware.verify)

    # tt firmware latest
    latest_fw_parser = firmware_subparsers.add_parser(
        'latest',
        help='Show latest firmware version',
    )
    latest_fw_parser.add_argument(
        '--download',
        action='store_true',
        help='Download latest firmware',
    )
    latest_fw_parser.add_argument(
        '--flash',
        action='store_true',
        help='Download and flash latest firmware',
    )
    latest_fw_parser.add_argument(
        '--recommended',
        action='store_true',
        help='Show latest recommended for detected hardware',
    )
    latest_fw_parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt',
    )
    latest_fw_parser.set_defaults(func=firmware.latest)

    # ========================================================================
    # tt fw - Firmware management (alias for firmware)
    # ========================================================================
    fw_parser = subparsers.add_parser(
        'fw',
        help='Manage device firmware (alias for firmware)',
        description='Manage device firmware',
        epilog='''Examples:
  tt fw current                          # Show current firmware
  tt fw ls                               # List available versions
  tt fw flash v19.4.2 --yes              # Flash firmware version
  tt fw latest --recommended             # Show recommended version
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    fw_subparsers = fw_parser.add_subparsers(
        dest='firmware_command',  # Use same dest as firmware
        help='Firmware commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # Add all firmware subcommands to fw as well
    # tt fw list / ls
    list_fw2_parser = fw_subparsers.add_parser('list', help='List available firmware versions')
    list_fw2_parser.add_argument('--json', action='store_true', help='Output as JSON')
    list_fw2_parser.add_argument('--recommended', action='store_true', help='Show only recommended versions')
    list_fw2_parser.set_defaults(func=firmware.list_firmware)

    ls_fw2_parser = fw_subparsers.add_parser('ls', help='List available firmware versions (alias for list)')
    ls_fw2_parser.add_argument('--json', action='store_true', help='Output as JSON')
    ls_fw2_parser.add_argument('--recommended', action='store_true', help='Show only recommended versions')
    ls_fw2_parser.set_defaults(func=firmware.list_firmware)

    # tt fw current
    current_fw2_parser = fw_subparsers.add_parser('current', help='Show current firmware version')
    current_fw2_parser.add_argument('--json', action='store_true', help='Output as JSON')
    current_fw2_parser.set_defaults(func=firmware.current_firmware)

    # tt fw flash
    flash_fw2_parser = fw_subparsers.add_parser('flash', help='Flash firmware to devices')
    flash_fw2_parser.add_argument('version_or_path', help='Firmware version or path to .fwbundle file')
    flash_fw2_parser.add_argument('--force', action='store_true', help='Force update ROM')
    flash_fw2_parser.add_argument('--no-reset', action='store_true', dest='no_reset', help='Do not reset devices after flash')
    flash_fw2_parser.add_argument('--allow-downgrades', action='store_true', dest='allow_downgrades', help='Allow major version downgrades')
    flash_fw2_parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    flash_fw2_parser.set_defaults(func=firmware.flash)

    # ========================================================================
    # tt model - Model management
    # ========================================================================
    model_parser = subparsers.add_parser(
        'model',
        help='Manage AI models',
        epilog='''Examples:
  tt model ls                            # List installed models
  tt model ls --device P150X4            # Show available for device
  tt model get meta-llama/Llama-3.1-8B   # Download from HuggingFace
  tt model info qwen3                    # Show model details
  tt model search llama                  # Search available models
  tt model cache ls qwen3                # List TT cache files
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    model_subparsers = model_parser.add_subparsers(
        dest='model_command',
        help='Model commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt model get / download
    get_parser = model_subparsers.add_parser(
        'get',
        help='Download model from HuggingFace',
    )
    get_parser.add_argument(
        'model',
        help='Model repository (e.g., Qwen/Qwen3-0.6B, meta-llama/Llama-3.1-8B)',
    )
    get_parser.add_argument(
        '--token',
        help='HuggingFace token for gated models',
    )
    get_parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download even if model exists',
    )
    get_parser.add_argument(
        '--validate',
        action='store_true',
        default=True,
        help='Validate model after download (default: True)',
    )
    get_parser.add_argument(
        '--models-dir',
        help='Models directory (default: ~/models)',
    )
    get_parser.set_defaults(func=model.get)

    # tt model download (alias for get)
    download_parser = model_subparsers.add_parser(
        'download',
        help='Download model from HuggingFace (alias for get)',
    )
    download_parser.add_argument(
        'model',
        help='Model repository (e.g., Qwen/Qwen3-0.6B, meta-llama/Llama-3.1-8B)',
    )
    download_parser.add_argument(
        '--token',
        help='HuggingFace token for gated models',
    )
    download_parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download even if model exists',
    )
    download_parser.add_argument(
        '--validate',
        action='store_true',
        default=True,
        help='Validate model after download (default: True)',
    )
    download_parser.add_argument(
        '--models-dir',
        help='Models directory (default: ~/models)',
    )
    download_parser.set_defaults(func=model.download)

    # tt model list (and alias: tt model ls)
    list_model_parser = model_subparsers.add_parser(
        'list',
        help='List installed models (and optionally show available models)',
    )
    list_model_parser.add_argument(
        '--device',
        help='Also show available models for device type (e.g., P150X4, N300)',
    )
    list_model_parser.set_defaults(func=model.list_models)

    # tt model ls (alias for list)
    ls_model_parser = model_subparsers.add_parser(
        'ls',
        help='List installed models (alias for list)',
    )
    ls_model_parser.add_argument(
        '--device',
        help='Also show available models for device type (e.g., P150X4, N300)',
    )
    ls_model_parser.set_defaults(func=model.list_models)

    # tt model info
    info_model_parser = model_subparsers.add_parser(
        'info',
        help='Show model information',
    )
    info_model_parser.add_argument(
        'name',
        help='Model name',
    )
    info_model_parser.set_defaults(func=model.info)

    # tt model check
    check_model_parser = model_subparsers.add_parser(
        'check',
        help='Validate model files',
    )
    check_model_parser.add_argument(
        'name',
        help='Model name',
    )
    check_model_parser.set_defaults(func=model.check)

    # tt model search (NEW - search tt-inference-server specs)
    search_model_parser = model_subparsers.add_parser(
        'search',
        help='Search for models in tt-inference-server specs',
    )
    search_model_parser.add_argument(
        'query',
        help='Search query (e.g., "llama", "qwen", "8b")',
    )
    search_model_parser.add_argument(
        '--device',
        help='Filter by device type (e.g., P150X4, N300)',
    )
    search_model_parser.set_defaults(func=model.search)

    # tt model spec-info (NEW - show detailed spec from tt-inference-server)
    spec_info_model_parser = model_subparsers.add_parser(
        'spec-info',
        help='Show detailed model spec from tt-inference-server',
    )
    spec_info_model_parser.add_argument(
        'model',
        help='Model name',
    )
    spec_info_model_parser.add_argument(
        '--device',
        help='Device type (e.g., P150X4, N300)',
    )
    spec_info_model_parser.set_defaults(func=model.spec_info)

    # tt model cache - Cache management
    cache_model_parser = model_subparsers.add_parser(
        'cache',
        help='Manage TT model caches',
        description='Build, clear, and list TT-optimized tensor caches',
        epilog='''Examples:
  tt model cache ls my-model            # List cache files
  tt model cache build my-model         # Build TT cache
  tt model cache clear my-model         # Clear cache
  tt model cache clear my-model --device P150X4  # Clear specific device cache
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cache_subparsers = cache_model_parser.add_subparsers(
        dest='cache_command',
        help='Cache commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt model cache ls
    cache_ls_parser = cache_subparsers.add_parser(
        'ls',
        help='List cache files',
    )
    cache_ls_parser.add_argument('model', help='Model name')
    cache_ls_parser.add_argument('--models-dir', help='Models directory')
    cache_ls_parser.set_defaults(func=model.cache_list)

    # tt model cache list (alias)
    cache_list_parser = cache_subparsers.add_parser(
        'list',
        help='List cache files (alias for ls)',
    )
    cache_list_parser.add_argument('model', help='Model name')
    cache_list_parser.add_argument('--models-dir', help='Models directory')
    cache_list_parser.set_defaults(func=model.cache_list)

    # tt model cache clear
    cache_clear_parser = cache_subparsers.add_parser(
        'clear',
        help='Clear TT cache',
    )
    cache_clear_parser.add_argument('model', help='Model name')
    cache_clear_parser.add_argument('--device', help='Clear specific device cache only')
    cache_clear_parser.add_argument('--models-dir', help='Models directory')
    cache_clear_parser.add_argument('--yes', action='store_true', help='Skip confirmation')
    cache_clear_parser.set_defaults(func=model.cache_clear)

    # tt model cache build
    cache_build_parser = cache_subparsers.add_parser(
        'build',
        help='Build TT cache',
    )
    cache_build_parser.add_argument('model', help='Model name')
    cache_build_parser.add_argument('--models-dir', help='Models directory')
    cache_build_parser.add_argument('--force', action='store_true', help='Rebuild if exists')
    cache_build_parser.set_defaults(func=model.cache_build)

    # ========================================================================
    # tt workflow - Workflow automation
    # ========================================================================
    workflow_parser = subparsers.add_parser(
        'workflow',
        help='Run automated workflows',
        epilog='''Examples:
  tt workflow ls                         # List available workflows
  tt workflow info validation            # Show workflow details
  tt workflow run validation --model m   # Run validation workflow
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    workflow_subparsers = workflow_parser.add_subparsers(
        dest='workflow_command',
        help='Workflow commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt workflow list
    workflow_list_parser = workflow_subparsers.add_parser(
        'list',
        help='List available workflows',
    )
    workflow_list_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    workflow_list_parser.set_defaults(func=workflow.list_workflows)

    # tt workflow info
    workflow_info_parser = workflow_subparsers.add_parser(
        'info',
        help='Show workflow details',
    )
    workflow_info_parser.add_argument(
        'name',
        help='Workflow name',
    )
    workflow_info_parser.set_defaults(func=workflow.info)

    # tt workflow run
    workflow_run_parser = workflow_subparsers.add_parser(
        'run',
        help='Run a workflow',
    )
    workflow_run_parser.add_argument(
        'name',
        help='Workflow name',
    )
    workflow_run_parser.add_argument(
        '--model',
        help='Model name (for model-related workflows)',
    )
    workflow_run_parser.add_argument(
        '--eval-suite',
        dest='eval_suite',
        help='Evaluation suite name (for eval workflow)',
    )
    workflow_run_parser.add_argument(
        '--dry-run',
        dest='dry_run',
        action='store_true',
        help='Show what would be done without executing',
    )
    workflow_run_parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode (validation only, no server start)',
    )
    workflow_run_parser.set_defaults(func=workflow.run)

    # ========================================================================
    # tt stack - Stack management (tt-jukebox style)
    # ========================================================================
    stack_parser = subparsers.add_parser(
        'stack',
        help='Manage deployment stacks',
        epilog='''Examples:
  tt stack ls                            # List available stacks
  tt stack use my-stack                  # Activate a stack
  tt stack info my-stack                 # Show stack details
  tt stack create new-stack              # Create new stack
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    stack_subparsers = stack_parser.add_subparsers(
        dest='stack_command',
        help='Stack commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt stack list (and alias: tt stack ls)
    stack_list_parser = stack_subparsers.add_parser(
        'list',
        help='List available stacks',
    )
    stack_list_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    stack_list_parser.set_defaults(func=stack.list_stacks)

    # tt stack ls (alias for list)
    stack_ls_parser = stack_subparsers.add_parser(
        'ls',
        help='List available stacks (alias for list)',
    )
    stack_ls_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    stack_ls_parser.set_defaults(func=stack.list_stacks)

    # tt stack use
    stack_use_parser = stack_subparsers.add_parser(
        'use',
        help='Activate a stack',
    )
    stack_use_parser.add_argument(
        'name',
        help='Stack name',
    )
    stack_use_parser.add_argument(
        '--force',
        action='store_true',
        help='Activate even with warnings',
    )
    stack_use_parser.set_defaults(func=stack.use)

    # tt stack info
    stack_info_parser = stack_subparsers.add_parser(
        'info',
        help='Show stack details',
    )
    stack_info_parser.add_argument(
        'name',
        help='Stack name',
    )
    stack_info_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    stack_info_parser.set_defaults(func=stack.info)

    # tt stack create
    stack_create_parser = stack_subparsers.add_parser(
        'create',
        help='Create a new stack',
    )
    stack_create_parser.add_argument(
        'name',
        help='Stack name',
    )
    stack_create_parser.add_argument(
        '--from-json',
        dest='from_json',
        help='Load configuration from JSON file',
    )
    stack_create_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing stack',
    )
    stack_create_parser.set_defaults(func=stack.create)

    # tt stack remove (and alias: tt stack rm)
    stack_remove_parser = stack_subparsers.add_parser(
        'remove',
        help='Remove a stack',
    )
    stack_remove_parser.add_argument(
        'name',
        help='Stack name',
    )
    stack_remove_parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation',
    )
    stack_remove_parser.set_defaults(func=stack.remove)

    # tt stack rm (alias for remove)
    stack_rm_parser = stack_subparsers.add_parser(
        'rm',
        help='Remove a stack (alias for remove)',
    )
    stack_rm_parser.add_argument(
        'name',
        help='Stack name',
    )
    stack_rm_parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation',
    )
    stack_rm_parser.set_defaults(func=stack.remove)

    # ========================================================================
    # tt config - Configuration management
    # ========================================================================
    config_parser = subparsers.add_parser(
        'config',
        help='Manage configuration',
        epilog='''Examples:
  tt config ls                           # List all configuration
  tt config get server.default_port      # Get specific value
  tt config set server.default_port 8001 # Set configuration value
  tt config reset                        # Reset to defaults
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    config_subparsers = config_parser.add_subparsers(
        dest='config_command',
        help='Configuration commands',
        required=True,
        parser_class=SmartArgumentParser,
    )

    # tt config get
    config_get_parser = config_subparsers.add_parser(
        'get',
        help='Get configuration value',
    )
    config_get_parser.add_argument(
        'key',
        help='Configuration key (dot notation, e.g., server.default_port)',
    )
    config_get_parser.add_argument(
        '--config-file',
        dest='config_file',
        help='Path to config file',
    )
    config_get_parser.set_defaults(func=config.get)

    # tt config set
    config_set_parser = config_subparsers.add_parser(
        'set',
        help='Set configuration value',
    )
    config_set_parser.add_argument(
        'key',
        help='Configuration key (dot notation)',
    )
    config_set_parser.add_argument(
        'value',
        help='Value to set',
    )
    config_set_parser.add_argument(
        '--config-file',
        dest='config_file',
        help='Path to config file',
    )
    config_set_parser.set_defaults(func=config.set)

    # tt config list (and alias: tt config ls)
    config_list_parser = config_subparsers.add_parser(
        'list',
        help='List all configuration',
    )
    config_list_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    config_list_parser.add_argument(
        '--config-file',
        dest='config_file',
        help='Path to config file',
    )
    config_list_parser.set_defaults(func=config.list_config)

    # tt config ls (alias for list)
    config_ls_parser = config_subparsers.add_parser(
        'ls',
        help='List all configuration (alias for list)',
    )
    config_ls_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    config_ls_parser.add_argument(
        '--config-file',
        dest='config_file',
        help='Path to config file',
    )
    config_ls_parser.set_defaults(func=config.list_config)

    # tt config reset
    config_reset_parser = config_subparsers.add_parser(
        'reset',
        help='Reset configuration to defaults',
    )
    config_reset_parser.add_argument(
        '--config-file',
        dest='config_file',
        help='Path to config file',
    )
    config_reset_parser.set_defaults(func=config.reset)

    # ========================================================================
    # tt status - Show status
    # ========================================================================
    status_parser = subparsers.add_parser(
        'status',
        help='Show system status',
    )
    status_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )
    status_parser.set_defaults(func=status.status)

    # ========================================================================
    # tt doctor - System diagnostics
    # ========================================================================
    doctor.add_doctor_parser(subparsers)

    return parser


def main():
    """Main entry point for tt CLI."""
    parser = create_parser()

    # If no arguments, show status
    if len(sys.argv) == 1:
        status.status(argparse.Namespace(json=False))
        return 0

    # Parse arguments
    args = parser.parse_args()

    # Enable debug mode if requested
    if hasattr(args, 'debug') and args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # Dispatch to command handler
    if hasattr(args, 'func'):
        try:
            result = args.func(args)
            return 0 if result is None else result
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            return 130
        except Exception as e:
            if hasattr(args, 'debug') and args.debug:
                raise
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
