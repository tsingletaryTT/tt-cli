"""
tt chat command - Start interactive chat with running model

This launches aider (or similar tools) configured to talk to a running vLLM model.
Automatically detects running models and configures the OpenAI-compatible API.

Examples:
    $ tt chat                        # Auto-select if 1 model, prompt if multiple
    $ tt chat llama-3.1-8b           # Chat with specific model
    $ tt chat --tool aider           # Use specific chat tool (default: aider)
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# Import ps module to get running servers
from tt.commands import ps as ps_module

# Default directories
DEFAULT_PID_DIR = Path.home() / ".tt" / "pids"


def select_model(servers: List[Dict]) -> Optional[Dict]:
    """
    Let user select a model from multiple running servers.

    Args:
        servers: List of running server dicts

    Returns:
        Selected server dict, or None if user cancels
    """
    print("Multiple models running. Select one:\n")

    # Show servers in a table
    print(f"{'#':<3}  {'MODEL':<20}  {'PORT':<6}  {'CHIPS':<8}  {'UPTIME':<10}")
    print("-" * 55)

    for idx, server in enumerate(servers, start=1):
        print(f"{idx:<3}  {server['model']:<20}  {server['port']:<6}  {server['chips']:<8}  {server['uptime']:<10}")

    print()

    # Get user selection
    while True:
        try:
            choice = input("Select model (1-{}, or 'q' to quit): ".format(len(servers)))

            if choice.lower() == 'q':
                return None

            idx = int(choice)
            if 1 <= idx <= len(servers):
                return servers[idx - 1]
            else:
                print(f"Invalid choice. Please enter 1-{len(servers)}")

        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n")
            return None


def check_tool_installed(tool: str) -> bool:
    """
    Check if a chat tool is installed.

    Args:
        tool: Tool name (e.g., 'aider')

    Returns:
        True if installed, False otherwise
    """
    try:
        result = subprocess.run(['which', tool], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def launch_aider(model: str, port: int, api_key: str = "dummy") -> int:
    """
    Launch aider configured for a local vLLM model.

    Args:
        model: Model name
        port: Server port
        api_key: API key (dummy for local)

    Returns:
        Exit code from aider
    """
    # Configure environment for aider
    env = os.environ.copy()

    # Set OpenAI API base to local vLLM server
    api_base = f"http://localhost:{port}/v1"
    env['OPENAI_API_BASE'] = api_base
    env['OPENAI_API_KEY'] = api_key

    # Build aider command
    cmd = [
        'aider',
        '--model', model,
        '--openai-api-base', api_base,
        '--openai-api-key', api_key,
    ]

    print(f"🚀 Starting aider...")
    print(f"   Model: {model}")
    print(f"   API: {api_base}")
    print(f"   Press Ctrl+C to exit\n")

    try:
        result = subprocess.run(cmd, env=env)
        return result.returncode
    except KeyboardInterrupt:
        print("\n")
        return 0


def chat(args: argparse.Namespace) -> int:
    """
    Start interactive chat with a running model.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 = success)
    """
    tool = args.tool if hasattr(args, 'tool') else 'aider'

    # Check if tool is installed
    if not check_tool_installed(tool):
        print(f"❌ {tool} is not installed")
        print()
        print(f"Install {tool}:")
        if tool == 'aider':
            print(f"  pip install aider-chat")
            print(f"  # or: pipx install aider-chat")
        print()
        return 1

    # Get running servers
    pid_dir = Path(args.pid_dir) if (hasattr(args, 'pid_dir') and args.pid_dir) else DEFAULT_PID_DIR
    servers = ps_module.get_running_servers(pid_dir)

    if not servers:
        print("❌ No models running")
        print()
        print("Start a model first:")
        print("  tt run <model>")
        print()
        print("Check status:")
        print("  tt ps")
        return 1

    # Determine which model to use
    selected_model = None

    if hasattr(args, 'model') and args.model:
        # User specified a model - find it
        model_name = args.model
        for server in servers:
            if server['model'] == model_name:
                selected_model = server
                break

        if not selected_model:
            print(f"❌ Model not running: {model_name}")
            print()
            print("Running models:")
            ps_module.print_table(servers)
            return 1

    elif len(servers) == 1:
        # Only one model running - use it automatically
        selected_model = servers[0]
        print(f"✓ Using running model: {selected_model['model']}")
        print()

    else:
        # Multiple models - ask user to choose
        selected_model = select_model(servers)
        if not selected_model:
            print("Cancelled")
            return 0
        print()

    # Launch chat tool
    if tool == 'aider':
        return launch_aider(selected_model['model'], selected_model['port'])
    else:
        print(f"❌ Unsupported tool: {tool}")
        print("   Supported tools: aider")
        return 1


def add_chat_parser(subparsers):
    """
    Add chat parser to main CLI.

    Args:
        subparsers: Subparsers from main argument parser
    """
    chat_parser = subparsers.add_parser(
        'chat',
        help='Start interactive chat with running model',
        description='Launch aider or other chat tools configured for a running vLLM model',
        epilog='''Examples:
  tt chat                           # Auto-select if 1 model running
  tt chat llama-3.1-8b              # Chat with specific model
  tt chat --tool aider              # Use specific tool (default: aider)
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    chat_parser.add_argument(
        'model',
        nargs='?',
        help='Model name (optional - will prompt if multiple running)',
    )

    chat_parser.add_argument(
        '--tool',
        default='aider',
        choices=['aider'],
        help='Chat tool to use (default: aider)',
    )

    chat_parser.add_argument(
        '--pid-dir',
        type=str,
        default=None,
        dest='pid_dir',
        help='PID file directory',
    )

    chat_parser.set_defaults(func=chat)
