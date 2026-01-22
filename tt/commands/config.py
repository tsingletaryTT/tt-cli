"""
Configuration management commands for tt-cli.

Provides commands to get, set, and list configuration values.
"""

import json
import argparse
from typing import Dict, Any

from tt.utils import config as config_utils


def get(args: argparse.Namespace) -> int:
    """
    Get a configuration value.

    Args:
        args: Command arguments with key

    Returns:
        Exit code (0 = success)
    """
    cfg = config_utils.load_config(config_path=args.config_file)

    value = config_utils.get_value(cfg, args.key)

    if value is None:
        print(f"⚠️  Configuration key '{args.key}' not found")
        print()
        print("Available keys:")
        print_keys(cfg)
        return 1

    # Print value
    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2))
    else:
        print(value)

    return 0


def set(args: argparse.Namespace) -> int:
    """
    Set a configuration value.

    Args:
        args: Command arguments with key and value

    Returns:
        Exit code (0 = success)
    """
    # Determine config file path
    config_path = args.config_file or str(config_utils.get_config_path())

    # Load existing config
    cfg = config_utils.load_config(config_path=config_path)

    # Set value
    config_utils.set_value(cfg, args.key, args.value)

    # Save config
    success = config_utils.save_config(cfg, config_path=config_path)

    if success:
        print(f"✓ Set {args.key} = {args.value}")
        print(f"  Config file: {config_path}")
    else:
        print(f"❌ Failed to save configuration")
        return 1

    return 0


def list_config(args: argparse.Namespace) -> int:
    """
    List all configuration values.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 = success)
    """
    cfg = config_utils.load_config(config_path=args.config_file)

    if args.json:
        print(json.dumps(cfg, indent=2))
    else:
        config_path = args.config_file or config_utils.get_config_path()
        print(f"Configuration (from {config_path}):")
        print()
        print_config(cfg)

    return 0


def reset(args: argparse.Namespace) -> int:
    """
    Reset configuration to defaults.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 = success)
    """
    # Determine config file path
    config_path = args.config_file or str(config_utils.get_config_path())

    # Get defaults
    cfg = config_utils.DEFAULT_CONFIG.copy()

    # Save defaults
    success = config_utils.save_config(cfg, config_path=config_path)

    if success:
        print(f"✓ Reset configuration to defaults")
        print(f"  Config file: {config_path}")
    else:
        print(f"❌ Failed to save configuration")
        return 1

    return 0


def print_config(cfg: Dict[str, Any], indent: int = 0) -> None:
    """
    Print configuration in human-readable format.

    Args:
        cfg: Configuration dictionary
        indent: Indentation level
    """
    for key, value in cfg.items():
        if isinstance(value, dict):
            print("  " * indent + f"{key}:")
            print_config(value, indent + 1)
        elif isinstance(value, list):
            print("  " * indent + f"{key}: {json.dumps(value)}")
        else:
            print("  " * indent + f"{key}: {value}")


def print_keys(cfg: Dict[str, Any], prefix: str = "") -> None:
    """
    Print all configuration keys in dot notation.

    Args:
        cfg: Configuration dictionary
        prefix: Key prefix
    """
    for key, value in cfg.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            print_keys(value, full_key)
        else:
            print(f"  {full_key}")
