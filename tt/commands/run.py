"""
Simple 'tt run' command for tt-cli.

This is the primary ergonomic improvement inspired by tt-jukebox:
- Single command: "tt run <model>"
- Auto-detects hardware
- Fetches official model specs from tt-inference-server
- Shows exactly what it's doing (transparent)
- Validates environment compatibility
- Just works™

Philosophy: "I want to run a model" → done
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict

from tt.utils import hardware, model_specs, compatibility


def find_model_path(model_name: str, models_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Find model path in common locations.

    Searches:
    - ~/models/
    - Exact path if provided
    - HuggingFace cache

    Args:
        model_name: Model name or path
        models_dir: Override models directory

    Returns:
        Path to model directory, or None if not found
    """
    # If it's already a path, check if it exists
    model_path = Path(model_name)
    if model_path.exists() and model_path.is_dir():
        return model_path

    # Try models directory
    if models_dir is None:
        models_dir = Path.home() / "models"

    # Look for model in models directory
    # Try exact match first
    candidates = [
        models_dir / model_name,
        models_dir / model_name.lower(),
        models_dir / model_name.replace('/', '--'),  # HF format
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    # Try fuzzy match in models directory
    if models_dir.exists():
        model_lower = model_name.lower()
        for item in models_dir.iterdir():
            if item.is_dir():
                # Check if model name is in directory name
                if model_lower in item.name.lower() or item.name.lower() in model_lower:
                    return item

    return None


def run_command(args):
    """
    Execute 'tt run <model>' command.

    This is the main entry point for the simple workflow.

    Workflow:
    1. Detect hardware
    2. Fetch model spec from tt-inference-server (live or cached)
    3. Find model files
    4. Check environment compatibility
    5. Start server with official parameters

    Args:
        args: Parsed arguments from argparse
    """
    model_name = args.model
    force = args.force
    verbose = args.verbose

    print(f"🚀 Running model: {model_name}")
    print()

    # Step 1: Detect hardware
    print("🔍 Detecting hardware...")
    hw = hardware.detect_hardware()

    if not hw:
        print("❌ No Tenstorrent hardware detected")
        print("   Run 'tt-smi -s' to check device status")
        sys.exit(1)

    device_type = hw['primary_type']
    device_count = hw['count']

    # Get mesh device name
    mesh_device = hardware.get_mesh_device()

    print(f"✓ Hardware: {device_count}x {device_type}")
    if mesh_device:
        print(f"  MESH_DEVICE: {mesh_device}")
    print()

    # Step 2: Fetch model spec from tt-inference-server
    print("🌐 Fetching model specs from tt-inference-server...")

    try:
        spec = model_specs.get_model_spec(
            model_name,
            mesh_device or device_type,
            verbose=verbose
        )
    except RuntimeError as e:
        print(f"❌ Failed to fetch model specs: {e}")
        sys.exit(1)

    if not spec:
        print(f"❌ No compatible spec found for '{model_name}' on {mesh_device or device_type}")
        print()
        print("Try:")
        print(f"  tt model search {model_name}")
        print(f"  tt model list --device {mesh_device or device_type}")
        sys.exit(1)

    full_model_name = spec.get('model_name', model_name)
    spec_id = spec.get('spec_id', 'unknown')

    print(f"✓ Found spec: {full_model_name}")
    print(f"  Spec ID: {spec_id}")
    print(f"  Device: {spec.get('device_type', 'unknown')}")
    print()

    # Step 3: Find model files
    print("📁 Looking for model files...")

    # Try to find model locally
    model_path = find_model_path(model_name, args.models_dir)

    if model_path:
        print(f"✓ Found model: {model_path}")
        model_arg = str(model_path)
    else:
        # Use HuggingFace path from spec
        print(f"⚠️  Local model not found, will download from HuggingFace")
        model_arg = full_model_name

    print()

    # Step 4: Check environment compatibility
    print("🔧 Checking environment compatibility...")

    compat = compatibility.check_environment_compatibility(spec, verbose=False)

    if compat['all_match']:
        print("✓ Environment matches spec requirements")
    else:
        print("⚠️  Environment differs from spec:")
        print()

        if not compat['metal_match']:
            print(f"  tt-metal:")
            print(f"    Current:  {compat['metal_current']}")
            print(f"    Required: {compat['metal_required']}")

        if not compat['vllm_match']:
            print(f"  tt-vllm:")
            print(f"    Current:  {compat['vllm_current']}")
            print(f"    Required: {compat['vllm_required']}")

        print()

        if not force:
            print("⚠️  This may not work as expected.")
            print("   Use --force to run anyway, or update your environment.")
            print()
            print("Recommendations:")
            for rec in compat['recommendations']:
                print(f"  • {rec}")
            sys.exit(1)
        else:
            print("⚠️  Running anyway (--force enabled)")

    print()

    # Step 5: Start server with official parameters
    print("🚀 Starting vLLM server with official parameters...")
    print()

    # Extract vLLM arguments from spec
    device_model_spec = spec.get('device_model_spec', {})
    vllm_args = device_model_spec.get('vllm_args', {})
    env_vars = device_model_spec.get('env_vars', {})

    # Display what we're using
    print("Parameters from spec:")
    print(f"  max_model_len: {vllm_args.get('max_model_len', 'default')}")
    print(f"  max_num_seqs: {vllm_args.get('max_num_seqs', 'default')}")
    print(f"  block_size: {vllm_args.get('block_size', 'default')}")

    if env_vars.get('MESH_DEVICE'):
        print(f"  MESH_DEVICE: {env_vars['MESH_DEVICE']}")

    print()

    # Build vLLM command
    vllm_cmd = ['python', '-m', 'vllm.entrypoints.openai.api_server']

    # Model argument
    vllm_cmd.extend(['--model', model_arg])

    # Apply parameters from spec
    if 'max_model_len' in vllm_args:
        vllm_cmd.extend(['--max-model-len', str(vllm_args['max_model_len'])])

    if 'max_num_seqs' in vllm_args:
        vllm_cmd.extend(['--max-num-seqs', str(vllm_args['max_num_seqs'])])

    if 'block_size' in vllm_args:
        vllm_cmd.extend(['--block-size', str(vllm_args['block_size'])])

    # Port (use override or default)
    port = args.port or 8000
    vllm_cmd.extend(['--port', str(port)])

    # Apply overrides from command line
    if args.max_model_len:
        # Replace the value
        for i, arg in enumerate(vllm_cmd):
            if arg == '--max-model-len' and i + 1 < len(vllm_cmd):
                vllm_cmd[i + 1] = str(args.max_model_len)
                print(f"⚠️  Override: max_model_len = {args.max_model_len}")
                break

    if args.max_num_seqs:
        for i, arg in enumerate(vllm_cmd):
            if arg == '--max-num-seqs' and i + 1 < len(vllm_cmd):
                vllm_cmd[i + 1] = str(args.max_num_seqs)
                print(f"⚠️  Override: max_num_seqs = {args.max_num_seqs}")
                break

    # Prepare environment variables
    env = os.environ.copy()

    # Apply environment variables from spec
    for key, value in env_vars.items():
        env[key] = str(value)
        if verbose:
            print(f"  Setting {key}={value}")

    # Set ARCH_NAME if Blackhole
    if hardware.is_blackhole():
        arch_name = hardware.get_arch_name()
        if arch_name:
            env['TT_METAL_ARCH_NAME'] = arch_name
            if verbose:
                print(f"  Setting TT_METAL_ARCH_NAME={arch_name}")

    # Show the actual command (transparent like tt-jukebox)
    print()
    print("Command:")
    print(f"  {' '.join(vllm_cmd)}")
    print()

    # Run it
    try:
        subprocess.run(vllm_cmd, env=env)
    except KeyboardInterrupt:
        print()
        print("⚠️  Stopped by user")
        sys.exit(0)
    except Exception as e:
        print()
        print(f"❌ Error running vLLM: {e}")
        sys.exit(1)


def add_run_parser(subparsers):
    """
    Add 'tt run' command to parser.

    This is called from cli.py to register the command.

    Args:
        subparsers: argparse subparsers object
    """
    run_parser = subparsers.add_parser(
        'run',
        help='Run a model (simple workflow)',
        description='Run a model with automatic configuration from tt-inference-server specs',
    )

    run_parser.add_argument(
        'model',
        help='Model name (e.g., "llama-3.1-8b", "qwen3")',
    )

    run_parser.add_argument(
        '--force',
        action='store_true',
        help='Run even if environment doesn\'t match spec',
    )

    run_parser.add_argument(
        '--port',
        type=int,
        help='Server port (default: 8000)',
    )

    run_parser.add_argument(
        '--models-dir',
        type=Path,
        help='Models directory (default: ~/models)',
    )

    run_parser.add_argument(
        '--max-model-len',
        type=int,
        help='Override max_model_len from spec',
    )

    run_parser.add_argument(
        '--max-num-seqs',
        type=int,
        help='Override max_num_seqs from spec',
    )

    run_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed information',
    )

    run_parser.set_defaults(func=run_command)
