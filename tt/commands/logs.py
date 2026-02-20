"""
tt logs command - View model logs

This provides access to logs for running or recently run models.
Similar to `docker logs` and `kubectl logs`.

Examples:
    $ tt logs llama-3.1-8b           # Show all logs
    $ tt logs qwen3 --follow         # Live tail logs
    $ tt logs qwen3 -f               # Short form for follow
    $ tt logs qwen3 --tail 100       # Show last 100 lines
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Optional

# Default directories (matches serve.py and ps.py)
DEFAULT_PID_DIR = Path.home() / ".tt" / "pids"


def normalize_model_name(model_name: str) -> str:
    """
    Normalize model name for file paths.

    Args:
        model_name: Original model name

    Returns:
        Normalized name (e.g., "qwen3-0.6b", "llama-3.1-8b")
    """
    return model_name.lower().replace('_', '-')


def find_log_file(model_name: str, pid_dir: Path, device_id: Optional[int] = None) -> Optional[Path]:
    """
    Find log file for a model.

    Args:
        model_name: Model name
        pid_dir: PID directory
        device_id: Device ID (for single-device instances)

    Returns:
        Path to log file, or None if not found
    """
    log_dir = pid_dir / "logs"

    if not log_dir.exists():
        return None

    normalized_name = normalize_model_name(model_name)

    # Try with device ID first if specified
    if device_id is not None:
        log_file = log_dir / f"{normalized_name}-dev{device_id}.log"
        if log_file.exists():
            return log_file

    # Try without device ID
    log_file = log_dir / f"{normalized_name}.log"
    if log_file.exists():
        return log_file

    # Try to find any log file matching the model name
    pattern = f"{normalized_name}*.log"
    matches = list(log_dir.glob(pattern))
    if matches:
        # Return the most recently modified one
        return max(matches, key=lambda p: p.stat().st_mtime)

    return None


def logs(args: argparse.Namespace) -> int:
    """
    View logs for a model.

    Args:
        args: Command arguments with model name, follow flag, tail count, etc.

    Returns:
        Exit code (0 = success)
    """
    model_name = args.model
    pid_dir = Path(args.pid_dir) if (hasattr(args, 'pid_dir') and args.pid_dir) else DEFAULT_PID_DIR
    device_id = args.device_id if hasattr(args, 'device_id') and args.device_id is not None else None

    # Find log file
    log_file = find_log_file(model_name, pid_dir, device_id)

    if not log_file:
        dev_str = f" on device {device_id}" if device_id is not None else ""
        print(f"❌ No log file found for model: {model_name}{dev_str}")
        print()
        print("Possible reasons:")
        print(f"  • Model was never started")
        print(f"  • Model was started without --detach flag (logs went to terminal)")
        print(f"  • Logs were deleted")
        print()
        print("Check running models: tt ps")
        return 1

    # Display logs
    try:
        if args.follow:
            # Live tail mode
            print(f"Following logs for {model_name} (Ctrl+C to stop)...")
            print(f"Log file: {log_file}")
            print("-" * 80)
            print()

            # Use tail -f for live following
            try:
                subprocess.run(['tail', '-f', str(log_file)])
            except KeyboardInterrupt:
                print("\n")
                return 0

        else:
            # Static display mode
            if hasattr(args, 'tail') and args.tail:
                # Show last N lines
                subprocess.run(['tail', '-n', str(args.tail), str(log_file)])
            else:
                # Show all logs
                # Use cat for static output
                subprocess.run(['cat', str(log_file)])

        return 0

    except FileNotFoundError as e:
        print(f"❌ Error reading log file: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


def add_logs_parser(subparsers):
    """
    Add logs parser to main CLI.

    Args:
        subparsers: Subparsers from main argument parser
    """
    logs_parser = subparsers.add_parser(
        'logs',
        help='View model logs',
        description='View logs for running or recently run models (like docker logs)',
        epilog='''Examples:
  tt logs llama-3.1-8b              # Show all logs
  tt logs qwen3 --follow            # Live tail logs
  tt logs qwen3 -f                  # Short form for follow
  tt logs qwen3 --tail 100          # Show last 100 lines
  tt logs qwen3 --device-id 0       # Logs for specific device
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    logs_parser.add_argument(
        'model',
        help='Model name',
    )

    logs_parser.add_argument(
        '--follow',
        '-f',
        action='store_true',
        help='Follow log output (live tail)',
    )

    logs_parser.add_argument(
        '--tail',
        type=int,
        default=None,
        help='Show last N lines (default: all)',
    )

    logs_parser.add_argument(
        '--device-id',
        type=int,
        default=None,
        dest='device_id',
        help='Device ID (for single-device instances)',
    )

    logs_parser.add_argument(
        '--pid-dir',
        type=str,
        default=None,
        dest='pid_dir',
        help='PID file directory',
    )

    logs_parser.set_defaults(func=logs)
