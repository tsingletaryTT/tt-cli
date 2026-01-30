"""
Server management commands for tt-cli.

Provides commands to start, stop, and manage vLLM servers.
"""

import os
import sys
import signal
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Optional, List

from tt.utils import hardware, envmanager


# Default models directory
DEFAULT_MODELS_DIR = Path.home() / "models"

# Default PID directory
DEFAULT_PID_DIR = Path.home() / ".tt" / "servers"


def get_optimal_params(hw_info: Dict, model_name: str) -> Dict[str, any]:
    """
    Determine optimal vLLM parameters based on hardware.

    Args:
        hw_info: Hardware information from detect_hardware()
        model_name: Name of the model being served

    Returns:
        Dictionary of optimal parameters
    """
    device_count = hw_info.get('count', 1)
    device_type = hw_info.get('primary_type', 'N150')

    # Base parameters
    params = {
        'max_model_len': 2048,
        'max_num_seqs': 16,
        'block_size': 64,
        'tensor_parallel_size': device_count if device_count > 1 else 1,
    }

    # Adjust based on device type
    if device_type in ['P100', 'P150', 'P300']:
        # Blackhole has more memory
        params['max_model_len'] = 4096
        params['max_num_seqs'] = 32

    # Adjust based on model size (heuristic from name)
    model_lower = model_name.lower()
    if '70b' in model_lower or '65b' in model_lower:
        # Large models - conservative settings
        # Note: TT hardware uses MESH_DEVICE, not tensor-parallel-size
        params['tensor_parallel_size'] = None  # Don't set for TT hardware
        params['max_model_len'] = 32768  # Reasonable for 70B models
        params['max_num_seqs'] = 8
    elif '8b' in model_lower or '7b' in model_lower:
        # Medium models
        params['tensor_parallel_size'] = None  # Don't set for TT hardware
        params['max_model_len'] = 4096
    elif '0.6b' in model_lower or '1b' in model_lower or '2b' in model_lower:
        # Small models can use less parallelism
        params['tensor_parallel_size'] = 1
        params['max_num_seqs'] = 32  # Can handle more sequences

    return params


def normalize_model_name(model_name: str) -> str:
    """
    Normalize model name for use in filenames.

    Args:
        model_name: Model name (e.g., "Qwen3-0.6B", "Llama-3.1-8B")

    Returns:
        Normalized name (e.g., "qwen3-0.6b", "llama-3.1-8b")
    """
    return model_name.lower().replace('_', '-')


def get_pid_file(model_name: str, pid_dir: Optional[Path] = None) -> Path:
    """
    Get PID file path for a model.

    Args:
        model_name: Model name
        pid_dir: Directory for PID files (default: ~/.tt/servers)

    Returns:
        Path to PID file
    """
    if pid_dir is None:
        pid_dir = DEFAULT_PID_DIR

    pid_dir = Path(pid_dir)
    pid_dir.mkdir(parents=True, exist_ok=True)

    normalized_name = normalize_model_name(model_name)
    return pid_dir / f"{normalized_name}.pid"


def write_pid_file(model_name: str, pid: int, port: int, pid_dir: Optional[Path] = None) -> None:
    """
    Write PID file for running server.

    Args:
        model_name: Model name
        pid: Process ID
        port: Server port
        pid_dir: Directory for PID files
    """
    pid_file = get_pid_file(model_name, pid_dir)

    data = {
        'pid': pid,
        'port': port,
        'model': model_name,
    }

    pid_file.write_text(json.dumps(data, indent=2))


def read_pid_file(model_name: str, pid_dir: Optional[Path] = None) -> Optional[Dict]:
    """
    Read PID file for a model.

    Args:
        model_name: Model name
        pid_dir: Directory for PID files

    Returns:
        Dictionary with pid, port, model or None if not found
    """
    pid_file = get_pid_file(model_name, pid_dir)

    if not pid_file.exists():
        return None

    try:
        return json.loads(pid_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def delete_pid_file(model_name: str, pid_dir: Optional[Path] = None) -> None:
    """
    Delete PID file for a model.

    Args:
        model_name: Model name
        pid_dir: Directory for PID files
    """
    pid_file = get_pid_file(model_name, pid_dir)
    if pid_file.exists():
        pid_file.unlink()


def start(args: argparse.Namespace) -> int:
    """
    Start a vLLM server.

    Args:
        args: Command arguments with model, port, etc.

    Returns:
        Exit code (0 = success)
    """
    # Get hardware info
    hw = hardware.detect_hardware()
    if not hw:
        print("❌ No hardware detected. Cannot start server.")
        print("   Run 'tt device info' to check hardware.")
        return 1

    device_type = hw.get('primary_type', 'Unknown')
    device_count = hw.get('count', 1)

    print(f"Hardware: {device_count}x {device_type}")

    # Check if model exists
    models_dir = Path(args.models_dir) if (hasattr(args, 'models_dir') and args.models_dir) else DEFAULT_MODELS_DIR
    models_dir = Path(models_dir)
    model_path = models_dir / args.model

    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        print(f"   Available models: tt model list")
        return 1

    # Check if already running
    pid_dir = Path(args.pid_dir) if (hasattr(args, 'pid_dir') and args.pid_dir) else DEFAULT_PID_DIR
    existing = read_pid_file(args.model, pid_dir)
    if existing:
        pid = existing['pid']
        try:
            # Check if process actually exists
            os.kill(pid, 0)
            print(f"⚠️  Server already running (PID: {pid}, Port: {existing['port']})")
            print(f"   Stop it first: tt stop {args.model}")
            return 1
        except (OSError, ProcessLookupError):
            # Process doesn't exist, clean up stale PID file
            delete_pid_file(args.model, pid_dir)

    # Get optimal parameters
    optimal = get_optimal_params(hw, args.model)

    # Override with user-provided values
    max_model_len = args.max_model_len if args.max_model_len else optimal['max_model_len']
    tensor_parallel = args.tensor_parallel if args.tensor_parallel else optimal['tensor_parallel_size']
    port = args.port

    # Determine which Python to use (check for vllm availability)
    python_cmd = 'python'

    # Try vllm environment first
    vllm_python = Path.home() / 'tt-metal' / 'build' / 'python_env_vllm' / 'bin' / 'python'
    if vllm_python.exists():
        python_cmd = str(vllm_python)
        print(f"  Using vLLM environment: {vllm_python}")

    # Build vLLM command
    cmd = [
        python_cmd, '-m', 'vllm.entrypoints.openai.api_server',
        '--model', str(model_path),
        '--port', str(port),
        '--max-model-len', str(max_model_len),
        '--max-num-seqs', str(optimal['max_num_seqs']),
        '--block-size', str(optimal['block_size']),
    ]

    # Only add tensor-parallel-size if explicitly set (TT hardware uses MESH_DEVICE instead)
    if tensor_parallel is not None:
        cmd.extend(['--tensor-parallel-size', str(tensor_parallel)])

    # Set environment variables
    # First, auto-fix environment to ensure TT_METAL_HOME and PYTHONPATH are set correctly
    _, fixed_env_vars = envmanager.fix_environment(apply_to_os_environ=False)

    # Start with current environment and apply fixes
    env = os.environ.copy()
    env.update(fixed_env_vars)

    mesh_device = hardware.get_mesh_device()
    if mesh_device:
        env['MESH_DEVICE'] = mesh_device

    arch_name = hardware.get_arch_name()
    if arch_name:
        env['TT_METAL_ARCH_NAME'] = arch_name

    # Set HF_MODEL for TT vLLM backend (required for model initialization)
    # Construct from model directory name using common patterns
    if 'HF_MODEL' not in env:
        model_name = args.model

        # Try common organization names based on model name
        if 'deepseek' in model_name.lower():
            hf_model = f"deepseek-ai/{model_name}"
        elif 'llama' in model_name.lower() and 'meta' not in model_name.lower():
            hf_model = f"meta-llama/{model_name}"
        elif 'qwen' in model_name.lower():
            hf_model = f"Qwen/{model_name}"
        elif 'mistral' in model_name.lower():
            hf_model = f"mistralai/{model_name}"
        else:
            # If already in org/name format, use as-is
            if '/' in model_name:
                hf_model = model_name
            else:
                # Generic fallback - just use the model name
                hf_model = model_name

        env['HF_MODEL'] = hf_model

    # Print what we're doing
    print(f"\nStarting vLLM server:")
    print(f"  Model: {args.model}")
    print(f"  Port: {port}")
    print(f"  max-model-len: {max_model_len}")
    if tensor_parallel is not None:
        print(f"  tensor-parallel-size: {tensor_parallel}")
    else:
        print(f"  tensor-parallel-size: (not set - using MESH_DEVICE)")
    print(f"  max-num-seqs: {optimal['max_num_seqs']}")
    print(f"  MESH_DEVICE: {mesh_device}")
    if arch_name:
        print(f"  TT_METAL_ARCH_NAME: {arch_name}")
    print(f"  HF_MODEL: {env.get('HF_MODEL', 'not set')}")
    print(f"  TT_METAL_HOME: {env.get('TT_METAL_HOME', 'not set')}")
    print(f"  PYTHONPATH: {env.get('PYTHONPATH', 'not set')}")

    # Start server
    try:
        if args.detach:
            # Detached mode - run in background
            print("\n🚀 Starting server in background...")

            # Redirect stdout/stderr to log file
            log_dir = pid_dir / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{normalize_model_name(args.model)}.log"

            with open(log_file, 'w') as f:
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,  # Detach from terminal
                )

            # Write PID file
            write_pid_file(args.model, process.pid, port, pid_dir)

            print(f"✓ Server started successfully")
            print(f"  PID: {process.pid}")
            print(f"  Log: {log_file}")
            print(f"\nCheck status: tt serve status")
            print(f"Stop server: tt stop {args.model}")

        else:
            # Foreground mode - run directly
            print("\n🚀 Starting server (foreground)...")
            print("   Press Ctrl+C to stop\n")

            process = subprocess.Popen(cmd, env=env)

            # Write PID file
            write_pid_file(args.model, process.pid, port, pid_dir)

            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n\nStopping server...")
                process.terminate()
                process.wait(timeout=10)
                delete_pid_file(args.model, pid_dir)
                print("✓ Server stopped")

        return 0

    except FileNotFoundError:
        print("❌ vLLM not found. Is it installed?")
        print("   Install: pip install vllm")
        return 1
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1


def stop(args: argparse.Namespace) -> int:
    """
    Stop a running vLLM server.

    Args:
        args: Command arguments with model name

    Returns:
        Exit code (0 = success)
    """
    pid_dir = Path(args.pid_dir) if (hasattr(args, 'pid_dir') and args.pid_dir) else DEFAULT_PID_DIR
    pid_info = read_pid_file(args.model, pid_dir)

    if not pid_info:
        print(f"⚠️  Server {args.model} is not running")
        return 1

    pid = pid_info['pid']
    port = pid_info.get('port', 'unknown')

    try:
        # Check if process exists
        os.kill(pid, 0)

        # Send SIGTERM
        print(f"Stopping server {args.model} (PID: {pid}, Port: {port})...")
        os.kill(pid, signal.SIGTERM)

        # Wait a bit for graceful shutdown
        import time
        for i in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except (OSError, ProcessLookupError):
                break

        # Check if still running
        try:
            os.kill(pid, 0)
            # Still running, force kill
            print("  Server not responding, force killing...")
            os.kill(pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass

        # Clean up PID file
        delete_pid_file(args.model, pid_dir)

        print(f"✓ Stopped server {args.model}")
        return 0

    except (OSError, ProcessLookupError):
        # Process doesn't exist
        print(f"⚠️  Server process not found (cleaned up stale PID file)")
        delete_pid_file(args.model, pid_dir)
        return 0


def status(args: argparse.Namespace) -> int:
    """
    Show status of running servers.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 = success)
    """
    pid_dir = Path(args.pid_dir) if (hasattr(args, 'pid_dir') and args.pid_dir) else DEFAULT_PID_DIR

    if not pid_dir.exists():
        if args.json:
            print(json.dumps({'servers': []}, indent=2))
        else:
            print("No servers running")
        return 0

    # Find all PID files
    pid_files = list(pid_dir.glob("*.pid"))

    if not pid_files:
        if args.json:
            print(json.dumps({'servers': []}, indent=2))
        else:
            print("No servers running")
        return 0

    # Check each server
    servers = []
    for pid_file in pid_files:
        try:
            pid_info = json.loads(pid_file.read_text())
            pid = pid_info['pid']

            # Check if process exists
            try:
                os.kill(pid, 0)
                running = True

                # Try to get CPU/memory info if psutil available
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    cpu = proc.cpu_percent(interval=0.1)
                    mem = proc.memory_info().rss / (1024 * 1024)  # MB
                except ImportError:
                    cpu = None
                    mem = None
            except (OSError, ProcessLookupError):
                running = False
                cpu = None
                mem = None
                # Clean up stale PID file
                pid_file.unlink()
                continue

            servers.append({
                'model': pid_info.get('model', 'unknown'),
                'pid': pid,
                'port': pid_info.get('port', 'unknown'),
                'running': running,
                'cpu_percent': cpu,
                'memory_mb': mem,
            })

        except (json.JSONDecodeError, KeyError):
            continue

    # Output
    if args.json:
        print(json.dumps({'servers': servers}, indent=2))
    else:
        if not servers:
            print("No servers running")
        else:
            print("Running Servers:\n")
            for server in servers:
                print(f"  {server['model']}")
                print(f"    PID: {server['pid']}")
                print(f"    Port: {server['port']}")
                if server['cpu_percent'] is not None:
                    print(f"    CPU: {server['cpu_percent']:.1f}%")
                    print(f"    Memory: {server['memory_mb']:.0f} MB")
                print()

    return 0


# Legacy aliases for compatibility
def serve(args):
    """Legacy alias for start()."""
    return start(args)


def restart(args):
    """Restart a server (stop then start)."""
    # Stop first
    stop_result = stop(args)

    # Start again
    return start(args)
