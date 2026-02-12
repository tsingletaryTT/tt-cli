#!/usr/bin/env python3
"""
Main CLI entry point for tt-cli
Handles argument parsing and command dispatch
"""

import sys
import argparse
from pathlib import Path

# Import command handlers
from tt.commands import serve, env, device, firmware, status, model, workflow, config, metal, stack


def create_parser():
    """Create argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog='tt',
        description='Unified CLI for Tenstorrent hardware development',
        epilog='Run "tt <command> --help" for more information on a command.',
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
    # tt serve - Server management
    # ========================================================================
    serve_parser = subparsers.add_parser(
        'serve',
        help='Manage vLLM servers',
        description='Start and manage vLLM servers',
    )
    serve_subparsers = serve_parser.add_subparsers(
        dest='serve_command',
        help='Server management commands',
        required=True,
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
    )
    env_subparsers = env_parser.add_subparsers(
        dest='env_command',
        help='Environment commands',
        required=True,
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

    # tt env list
    list_parser = env_subparsers.add_parser(
        'list',
        help='List available environments',
    )
    list_parser.set_defaults(func=env.list_envs)

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
    )
    metal_subparsers = metal_parser.add_subparsers(
        dest='metal_command',
        help='Metal commands',
        required=True,
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

    # tt metal list
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

    # tt metal remove
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
    )
    device_subparsers = device_parser.add_subparsers(
        dest='device_command',
        help='Device commands',
        required=True,
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
    )
    firmware_subparsers = firmware_parser.add_subparsers(
        dest='firmware_command',
        help='Firmware commands',
        required=True,
    )

    # tt firmware list
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
    # tt model - Model management
    # ========================================================================
    model_parser = subparsers.add_parser(
        'model',
        help='Manage AI models',
    )
    model_subparsers = model_parser.add_subparsers(
        dest='model_command',
        help='Model commands',
        required=True,
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

    # tt model list
    list_model_parser = model_subparsers.add_parser(
        'list',
        help='List installed models',
    )
    list_model_parser.set_defaults(func=model.list_models)

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

    # ========================================================================
    # tt workflow - Workflow automation
    # ========================================================================
    workflow_parser = subparsers.add_parser(
        'workflow',
        help='Run automated workflows',
    )
    workflow_subparsers = workflow_parser.add_subparsers(
        dest='workflow_command',
        help='Workflow commands',
        required=True,
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
    )
    stack_subparsers = stack_parser.add_subparsers(
        dest='stack_command',
        help='Stack commands',
        required=True,
    )

    # tt stack list
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

    # tt stack remove
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

    # ========================================================================
    # tt config - Configuration management
    # ========================================================================
    config_parser = subparsers.add_parser(
        'config',
        help='Manage configuration',
    )
    config_subparsers = config_parser.add_subparsers(
        dest='config_command',
        help='Configuration commands',
        required=True,
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

    # tt config list
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
