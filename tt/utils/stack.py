"""
Stack management utilities for tt-cli.

Stacks are pre-configured combinations of:
- TT-Metal version
- Model
- Hardware configuration
- Environment variables
- Server settings

This enables tt-jukebox-style workflows where you can switch
between complete deployment configurations with a single command.

Example:
    # Define a stack
    stacks:
      coding-dev:
        metal: v0.66.0-rc7
        model: meta-llama/Llama-3.1-8B-Instruct
        hardware: P150X4
        config:
          max_model_len: 128000
          max_num_seqs: 32
          tensor_parallel: 4

    # Use it
    tt stack use coding-dev
    tt serve start  # Automatically uses stack configuration
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from tt.utils import config as cfg, metal as metalutils, hardware


# Default stack templates
DEFAULT_STACKS = {
    'llama-3.1-8b-p150x4': {
        'description': 'Llama 3.1 8B Instruct on P150X4 (coding-optimized)',
        'metal': 'v0.66.0-rc7',
        'model': 'meta-llama/Llama-3.1-8B-Instruct',
        'hardware': 'P150X4',
        'config': {
            'max_model_len': 128000,
            'max_num_seqs': 128,  # 32 * 4 for data parallel
            'tensor_parallel': 1,
            'data_parallel': 4,
            'port': 8000,
        },
        'env_vars': {
            'VLLM_ALLOW_LONG_MAX_MODEL_LEN': '1',
        },
        'override_tt_config': {
            'data_parallel': 4,
            'sample_on_device_mode': 'decode_only',
            'trace_region_size': 33000000,
        },
    },
    'llama-3.3-70b-p150x4': {
        'description': 'Llama 3.3 70B Instruct on P150X4 (best reasoning)',
        'metal': 'v0.66.0-rc7',
        'model': 'meta-llama/Llama-3.3-70B-Instruct',
        'hardware': 'P150X4',
        'config': {
            'max_model_len': 128000,
            'max_num_seqs': 32,
            'tensor_parallel': 1,
            'port': 8000,
        },
        'env_vars': {
            'VLLM_ALLOW_LONG_MAX_MODEL_LEN': '1',
        },
        'override_tt_config': {
            'trace_region_size': 30000000,
        },
    },
}


def get_stacks() -> Dict[str, Dict]:
    """
    Get all stacks from config.

    Returns:
        Dict mapping stack names to stack configurations
    """
    conf = cfg.load_config()

    # Get user-defined stacks
    user_stacks = conf.get('stacks', {})

    # Merge with defaults (user stacks override defaults)
    stacks = DEFAULT_STACKS.copy()
    stacks.update(user_stacks)

    return stacks


def get_stack(name: str) -> Optional[Dict]:
    """
    Get a specific stack configuration.

    Args:
        name: Stack name

    Returns:
        Stack config dict or None if not found
    """
    stacks = get_stacks()
    return stacks.get(name)


def get_active_stack() -> Optional[str]:
    """
    Get the currently active stack.

    Returns:
        Stack name or None if not set
    """
    conf = cfg.load_config()
    return conf.get('active_stack')


def set_active_stack(name: str) -> None:
    """
    Set the active stack in config.

    Args:
        name: Stack name to set as active
    """
    conf = cfg.load_config()
    conf['active_stack'] = name
    cfg.save_config(conf)


def register_stack(name: str, stack_config: Dict) -> None:
    """
    Register a new stack or update existing one.

    Args:
        name: Stack name
        stack_config: Stack configuration dict
    """
    conf = cfg.load_config()

    if 'stacks' not in conf:
        conf['stacks'] = {}

    conf['stacks'][name] = stack_config
    cfg.save_config(conf)


def unregister_stack(name: str) -> None:
    """
    Remove a stack from config.

    Args:
        name: Stack name to remove
    """
    conf = cfg.load_config()

    if 'stacks' in conf and name in conf['stacks']:
        del conf['stacks'][name]

        # If this was the active stack, clear it
        if conf.get('active_stack') == name:
            conf['active_stack'] = None

        cfg.save_config(conf)


def validate_stack(stack_config: Dict) -> Dict[str, Any]:
    """
    Validate a stack configuration.

    Args:
        stack_config: Stack configuration to validate

    Returns:
        Dict with validation results:
        {
            'valid': bool,
            'issues': [str],
            'warnings': [str],
            'metal_exists': bool,
            'model_exists': bool,
            'hardware_matches': bool,
        }
    """
    issues = []
    warnings = []

    # Check required fields
    if 'metal' not in stack_config:
        issues.append("Missing 'metal' field (TT-Metal version)")

    if 'model' not in stack_config:
        issues.append("Missing 'model' field")

    if 'hardware' not in stack_config:
        warnings.append("Missing 'hardware' field (will use auto-detection)")

    # Check if metal version is installed
    metal_exists = False
    if 'metal' in stack_config:
        metal_version = stack_config['metal']
        installations = metalutils.get_metal_installations()
        metal_exists = metal_version in installations

        if not metal_exists:
            warnings.append(f"TT-Metal version '{metal_version}' not installed")

    # Check if model exists (basic check - look for model directory)
    model_exists = False
    if 'model' in stack_config:
        model_name = stack_config['model']
        # Check common model locations
        model_paths = [
            Path.home() / "models" / model_name.split('/')[-1],
            Path("/mnt/models") / model_name.split('/')[-1],
        ]

        model_exists = any(p.exists() for p in model_paths)

        if not model_exists:
            warnings.append(f"Model '{model_name}' not found locally (will download on first use)")

    # Check if hardware matches current system
    hardware_matches = False
    if 'hardware' in stack_config:
        expected_hw = stack_config['hardware']
        current_hw = hardware.detect_hardware()

        if current_hw:
            # Handle P300C → P150 aliasing
            current_type = current_hw.get('primary_type', '')
            if current_type == 'P300C':
                current_type = 'P150'

            hardware_matches = (current_type == expected_hw or
                              expected_hw.startswith(current_type))

            if not hardware_matches:
                warnings.append(
                    f"Hardware mismatch: stack expects {expected_hw}, "
                    f"but current hardware is {current_hw['primary_type']}"
                )

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'metal_exists': metal_exists,
        'model_exists': model_exists,
        'hardware_matches': hardware_matches,
    }


def activate_stack(name: str) -> Dict[str, str]:
    """
    Activate a stack by setting up its environment.

    This:
    1. Activates the specified TT-Metal version
    2. Sets environment variables
    3. Configures paths
    4. Sets stack as active

    Args:
        name: Stack name to activate

    Returns:
        Dict of environment variables set

    Raises:
        ValueError: If stack not found or invalid
    """
    stack_config = get_stack(name)

    if not stack_config:
        raise ValueError(f"Stack '{name}' not found")

    # Validate stack
    validation = validate_stack(stack_config)

    if not validation['valid']:
        raise ValueError(
            f"Invalid stack configuration: {', '.join(validation['issues'])}"
        )

    env_vars = {}

    # Activate TT-Metal version
    metal_version = stack_config['metal']
    installations = metalutils.get_metal_installations()

    if metal_version not in installations:
        raise ValueError(
            f"TT-Metal version '{metal_version}' not installed. "
            f"Install with: tt metal checkout --tag {metal_version}"
        )

    metal_path = Path(installations[metal_version]['path'])

    # Import envmanager here to avoid circular imports
    from tt.utils import envmanager
    metal_env_vars = envmanager.activate_metal_version(metal_path)
    env_vars.update(metal_env_vars)

    # Set stack-specific environment variables
    if 'env_vars' in stack_config:
        import os
        for var, value in stack_config['env_vars'].items():
            os.environ[var] = str(value)
            env_vars[var] = str(value)

    # Set as active stack
    set_active_stack(name)

    return env_vars


def get_stack_server_config(stack_name: Optional[str] = None) -> Dict:
    """
    Get server configuration from a stack.

    Args:
        stack_name: Stack name (uses active if None)

    Returns:
        Dict with server configuration suitable for tt serve

    Raises:
        ValueError: If no stack specified and no active stack
    """
    if not stack_name:
        stack_name = get_active_stack()

        if not stack_name:
            raise ValueError("No active stack and no stack name provided")

    stack_config = get_stack(stack_name)

    if not stack_config:
        raise ValueError(f"Stack '{stack_name}' not found")

    # Build server config
    server_config = {
        'model': stack_config['model'],
    }

    # Add config parameters
    if 'config' in stack_config:
        server_config.update(stack_config['config'])

    # Add override_tt_config if present
    if 'override_tt_config' in stack_config:
        server_config['override_tt_config'] = stack_config['override_tt_config']

    return server_config
