"""
tt ps command - Show running models (docker-like interface)

This provides a clean, table-based view of running models similar to `docker ps`.
Shows: PID, MODEL, PORT, CHIPS, STATUS, UPTIME

Example:
    $ tt ps
    PID    MODEL            PORT  CHIPS    STATUS   UPTIME
    1234   llama-3.1-8b     8000  0,1,2,3  running  2h 15m
    5678   qwen3            8001  0,1      running  45m
"""

import os
import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Optional

# Default directories (matches serve.py)
DEFAULT_PID_DIR = Path.home() / ".tt" / "pids"


def format_uptime(start_time: float) -> str:
    """
    Format uptime in human-readable form.

    Args:
        start_time: Process start time (epoch seconds)

    Returns:
        Formatted uptime (e.g., "2h 15m", "45m", "30s")
    """
    uptime_seconds = time.time() - start_time

    if uptime_seconds < 60:
        return f"{int(uptime_seconds)}s"
    elif uptime_seconds < 3600:
        minutes = int(uptime_seconds / 60)
        return f"{minutes}m"
    else:
        hours = int(uptime_seconds / 3600)
        minutes = int((uptime_seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def get_running_servers(pid_dir: Path) -> List[Dict]:
    """
    Get list of running servers from PID files.

    Args:
        pid_dir: Directory containing PID files

    Returns:
        List of server info dicts with pid, model, port, chips, status, uptime
    """
    if not pid_dir.exists():
        return []

    pid_files = list(pid_dir.glob("*.pid"))

    if not pid_files:
        return []

    servers = []

    for pid_file in pid_files:
        try:
            pid_info = json.loads(pid_file.read_text())
            pid = pid_info['pid']

            # Check if process exists
            try:
                os.kill(pid, 0)
                running = True

                # Get process start time for uptime calculation
                start_time = pid_info.get('start_time', time.time())
                uptime = format_uptime(start_time)

            except (OSError, ProcessLookupError):
                # Process doesn't exist - clean up stale PID file
                pid_file.unlink()
                continue

            # Extract chip information from PID info or device_id
            chips = pid_info.get('chips', 'unknown')
            if chips == 'unknown' and 'device_id' in pid_info:
                # Single device
                chips = str(pid_info['device_id'])

            servers.append({
                'pid': pid,
                'model': pid_info.get('model', 'unknown'),
                'port': pid_info.get('port', 'unknown'),
                'chips': chips,
                'status': 'running' if running else 'exited',
                'uptime': uptime,
            })

        except (json.JSONDecodeError, KeyError):
            # Invalid PID file - skip
            continue

    return servers


def print_table(servers: List[Dict]):
    """
    Print servers in a clean table format.

    Args:
        servers: List of server info dicts
    """
    if not servers:
        print("No models running")
        return

    # Calculate column widths
    pid_width = max(len(str(s['pid'])) for s in servers)
    pid_width = max(pid_width, len("PID"))

    model_width = max(len(s['model']) for s in servers)
    model_width = max(model_width, len("MODEL"))

    port_width = max(len(str(s['port'])) for s in servers)
    port_width = max(port_width, len("PORT"))

    chips_width = max(len(str(s['chips'])) for s in servers)
    chips_width = max(chips_width, len("CHIPS"))

    status_width = max(len(s['status']) for s in servers)
    status_width = max(status_width, len("STATUS"))

    uptime_width = max(len(s['uptime']) for s in servers)
    uptime_width = max(uptime_width, len("UPTIME"))

    # Print header
    header = (
        f"{'PID':<{pid_width}}  "
        f"{'MODEL':<{model_width}}  "
        f"{'PORT':<{port_width}}  "
        f"{'CHIPS':<{chips_width}}  "
        f"{'STATUS':<{status_width}}  "
        f"{'UPTIME':<{uptime_width}}"
    )
    print(header)

    # Print rows
    for server in servers:
        row = (
            f"{server['pid']:<{pid_width}}  "
            f"{server['model']:<{model_width}}  "
            f"{server['port']:<{port_width}}  "
            f"{server['chips']:<{chips_width}}  "
            f"{server['status']:<{status_width}}  "
            f"{server['uptime']:<{uptime_width}}"
        )
        print(row)


def ps(args: argparse.Namespace) -> int:
    """
    Show running models in a docker-like table format.

    Args:
        args: Command arguments (supports --json for JSON output)

    Returns:
        Exit code (0 = success)
    """
    pid_dir = Path(args.pid_dir) if (hasattr(args, 'pid_dir') and args.pid_dir) else DEFAULT_PID_DIR

    servers = get_running_servers(pid_dir)

    if hasattr(args, 'json') and args.json:
        # JSON output
        print(json.dumps({'servers': servers}, indent=2))
    else:
        # Table output
        print_table(servers)

    return 0
