"""
Configuration management utilities for tt-cli.

Supports loading and saving configuration from ~/.ttconfig (YAML format).
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


# Default configuration values
DEFAULT_CONFIG = {
    'models_dir': '~/models',
    'server': {
        'default_port': 8000,
        'default_max_model_len': 2048,
        'default_max_num_seqs': 16,
        'default_tensor_parallel': None,  # Auto-detect from hardware
    },
    'environments': {
        'default': 'metal',
        'metal': {
            'path': '~/tt-metal',
            'python_version': None,  # Auto-detect
        },
        'vllm': {
            'path': '~/tt-vllm',
            'python_version': None,
        },
        'forge': {
            'path': '~/tt-forge',
            'python_version': None,
        },
        'xla': {
            'path': '~/tt-xla',
            'python_version': None,
        },
    },
    'workflow': {
        'default_timeout': 300,  # seconds
        'auto_cleanup': True,  # Stop servers after workflows
    },
}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file or return defaults.

    Args:
        config_path: Path to config file. If None, searches standard locations.

    Returns:
        Configuration dictionary
    """
    # Determine config file path
    if config_path is None:
        # Search standard locations
        search_paths = [
            Path.home() / '.ttconfig',
            Path.home() / '.tt' / 'config.yaml',
            Path.cwd() / '.ttconfig',
        ]

        config_file = None
        for path in search_paths:
            if path.exists():
                config_file = path
                break
    else:
        config_file = Path(config_path)

    # Load config if file exists
    if config_file and config_file.exists():
        try:
            content = config_file.read_text()

            # Try YAML first (requires PyYAML, optional)
            try:
                import yaml
                cfg = yaml.safe_load(content)
            except ImportError:
                # Fallback to JSON if YAML not available
                cfg = json.loads(content)

            # Merge with defaults
            return merge_config(DEFAULT_CONFIG, cfg)

        except Exception as e:
            # On error, return defaults
            print(f"⚠️  Error loading config: {e}")
            print(f"   Using default configuration")
            return DEFAULT_CONFIG.copy()

    # Return defaults if no config file found
    return DEFAULT_CONFIG.copy()


def merge_config(defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge configuration dictionaries, with overrides taking precedence.

    Args:
        defaults: Default configuration
        overrides: Override configuration

    Returns:
        Merged configuration
    """
    result = defaults.copy()

    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = merge_config(result[key], value)
        else:
            # Override value
            result[key] = value

    return result


def get_value(cfg: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Get a value from configuration using dot notation.

    Args:
        cfg: Configuration dictionary
        key: Key in dot notation (e.g., 'server.default_port')
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    keys = key.split('.')
    value = cfg

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def set_value(cfg: Dict[str, Any], key: str, value: Any) -> None:
    """
    Set a value in configuration using dot notation.

    Args:
        cfg: Configuration dictionary (modified in place)
        key: Key in dot notation (e.g., 'server.default_port')
        value: Value to set
    """
    keys = key.split('.')
    current = cfg

    # Navigate to parent of target key
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    # Set the value
    current[keys[-1]] = value


def save_config(cfg: Dict[str, Any], config_path: Optional[str] = None) -> bool:
    """
    Save configuration to file.

    Args:
        cfg: Configuration dictionary
        config_path: Path to config file. If None, uses ~/.ttconfig

    Returns:
        True if successful, False otherwise
    """
    if config_path is None:
        config_path = str(Path.home() / '.ttconfig')

    config_file = Path(config_path)

    try:
        # Ensure parent directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Try to save as YAML if available
        try:
            import yaml
            content = yaml.dump(cfg, default_flow_style=False, sort_keys=False)
        except ImportError:
            # Fallback to JSON
            content = json.dumps(cfg, indent=2)

        config_file.write_text(content)
        return True

    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False


def get_config_path() -> Path:
    """
    Get the path to the configuration file.

    Returns:
        Path to config file (may not exist)
    """
    # Check standard locations
    search_paths = [
        Path.home() / '.ttconfig',
        Path.home() / '.tt' / 'config.yaml',
    ]

    for path in search_paths:
        if path.exists():
            return path

    # Return default location if none exist
    return Path.home() / '.ttconfig'
