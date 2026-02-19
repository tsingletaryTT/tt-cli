"""
Environment management utilities
Hybrid approach: uses uv when available, falls back to venv
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, List


# Standard environment configurations
ENVIRONMENTS = {
    'metal': {
        'name': 'TT-Metal',
        'venv_path': '~/tt-metal/python_env',
        'vars': {
            'TT_METAL_HOME': '~/tt-metal',
            'PYTHONPATH': '~/tt-metal',
            'LD_LIBRARY_PATH': '/opt/openmpi-v5.0.7-ulfm/lib',
        },
        'unset': [],
        'description': 'tt-metal development environment',
    },
    'vllm': {
        'name': 'vLLM',
        'venv_path': '~/tt-metal/build/python_env_vllm',
        'vars': {
            'TT_METAL_HOME': '~/tt-metal',
            'PYTHONPATH': '~/tt-metal',
            'LD_LIBRARY_PATH': '/opt/openmpi-v5.0.7-ulfm/lib',
        },
        'unset': [],
        'description': 'vLLM server environment',
    },
    'forge': {
        'name': 'TT-Forge',
        'venv_path': '~/tt-forge-venv',
        'vars': {
            'PYTHONPATH': '~/tt-forge',
        },
        'unset': ['TT_METAL_HOME', 'TT_METAL_VERSION'],  # Critical for Forge!
        'description': 'TT-Forge compiler environment',
    },
    'xla': {
        'name': 'TT-XLA',
        'venv_path': '~/tt-xla-venv',
        'vars': {
            'PJRT_PLUGIN_LIBRARY_PATH': '~/tt-xla/build/lib/libpjrt_tt.so',
            'LD_LIBRARY_PATH': '/opt/openmpi-v5.0.7-ulfm/lib',
        },
        'unset': [],
        'description': 'TT-XLA/JAX environment',
    },
}


def has_uv() -> bool:
    """Check if uv is available."""
    return shutil.which('uv') is not None


def get_current_python_version() -> str:
    """Get current Python version as string (e.g., '3.10')."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def create_venv(path: Path, python_version: Optional[str] = None) -> str:
    """
    Create virtual environment using best available tool.

    Args:
        path: Path to create venv
        python_version: Desired Python version (e.g., "3.10"), requires uv

    Returns:
        Tool used: 'uv' or 'venv'
    """
    path = Path(path).expanduser()

    # Try uv first (if available)
    if has_uv():
        if python_version:
            # uv can install specific Python versions
            cmd = f"uv venv --python={python_version} {path}"
        else:
            cmd = f"uv venv {path}"

        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            return 'uv'
        except subprocess.CalledProcessError:
            # Fall through to venv fallback
            pass

    # Fallback to standard venv
    if python_version and python_version != get_current_python_version():
        print(f"⚠️  Warning: Requested Python {python_version} but uv not available")
        print(f"   Install uv for multi-version support: pip install uv")
        print(f"   Using system Python {get_current_python_version()} instead")

    cmd = f"{sys.executable} -m venv {path}"
    subprocess.run(cmd, shell=True, check=True)
    return 'venv'


def install_packages(venv_path: Path, packages: List[str]):
    """
    Install packages into venv using best available tool.

    Args:
        venv_path: Path to virtual environment
        packages: List of package specifiers
    """
    venv_path = Path(venv_path).expanduser()

    if has_uv():
        # Use uv pip (10-100x faster)
        cmd = f"uv pip install --python {venv_path}/bin/python {' '.join(packages)}"
    else:
        # Use regular pip
        cmd = f"{venv_path}/bin/pip install {' '.join(packages)}"

    subprocess.run(cmd, shell=True, check=True)


def activate_environment(env_name: str) -> Dict[str, str]:
    """
    Activate environment by returning environment variables to set.

    Args:
        env_name: Environment name (metal, vllm, forge, xla)

    Returns:
        Dict of environment variables to set

    Raises:
        ValueError: If environment not found
    """
    if env_name not in ENVIRONMENTS:
        raise ValueError(
            f"Unknown environment: {env_name}. "
            f"Available: {', '.join(ENVIRONMENTS.keys())}"
        )

    env = ENVIRONMENTS[env_name]
    env_vars = {}

    # Unset conflicting variables
    for var in env['unset']:
        if var in os.environ:
            del os.environ[var]
            env_vars[var] = None  # Signal to caller

    # Set new variables (expand paths)
    for var, value in env['vars'].items():
        expanded = os.path.expanduser(value)

        # Handle PATH-like variables (append, don't replace)
        if var in ['LD_LIBRARY_PATH', 'PYTHONPATH']:
            existing = os.environ.get(var, '')
            if existing and expanded not in existing:
                expanded = f"{expanded}:{existing}"

        os.environ[var] = expanded
        env_vars[var] = expanded

    return env_vars


def activate_metal_version(metal_path: Path) -> Dict[str, str]:
    """
    Activate a specific TT-Metal installation by path.

    This is used for version-specific activation like:
    - tt env use metal@v0.66.0-rc7

    Args:
        metal_path: Path to TT-Metal installation directory

    Returns:
        Dict of environment variables set

    Raises:
        ValueError: If installation is invalid
    """
    metal_path = Path(metal_path).expanduser().resolve()

    if not metal_path.exists():
        raise ValueError(f"TT-Metal installation not found: {metal_path}")

    python_env = metal_path / "python_env"
    if not python_env.exists():
        raise ValueError(f"Python environment not found: {python_env}")

    env_vars = {}

    # Set TT_METAL_HOME
    tt_metal_home = str(metal_path)
    os.environ['TT_METAL_HOME'] = tt_metal_home
    env_vars['TT_METAL_HOME'] = tt_metal_home

    # Set PYTHONPATH
    pythonpath = os.environ.get('PYTHONPATH', '')
    if pythonpath and tt_metal_home not in pythonpath:
        pythonpath = f"{tt_metal_home}:{pythonpath}"
    else:
        pythonpath = tt_metal_home

    os.environ['PYTHONPATH'] = pythonpath
    env_vars['PYTHONPATH'] = pythonpath

    # Set LD_LIBRARY_PATH for OpenMPI
    ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    openmpi_path = '/opt/openmpi-v5.0.7-ulfm/lib'

    if openmpi_path not in ld_path:
        if ld_path:
            ld_path = f"{openmpi_path}:{ld_path}"
        else:
            ld_path = openmpi_path

    os.environ['LD_LIBRARY_PATH'] = ld_path
    env_vars['LD_LIBRARY_PATH'] = ld_path

    # Set VIRTUAL_ENV to point to python_env
    os.environ['VIRTUAL_ENV'] = str(python_env)
    env_vars['VIRTUAL_ENV'] = str(python_env)

    # Update PATH to include python_env/bin
    path = os.environ.get('PATH', '')
    python_bin = str(python_env / "bin")

    if python_bin not in path:
        path = f"{python_bin}:{path}"
        os.environ['PATH'] = path
        env_vars['PATH'] = path

    return env_vars


def check_environment() -> Dict:
    """
    Check current environment for common issues.

    Returns:
        Dict with status and issues found
    """
    issues = []
    warnings = []

    # Check TT_METAL_HOME
    tt_metal_home = os.environ.get('TT_METAL_HOME')
    if not tt_metal_home:
        warnings.append("TT_METAL_HOME not set")
    elif not Path(tt_metal_home).exists():
        issues.append(f"TT_METAL_HOME points to non-existent directory: {tt_metal_home}")

    # Check PYTHONPATH
    pythonpath = os.environ.get('PYTHONPATH')
    if not pythonpath:
        warnings.append("PYTHONPATH not set")

    # Check LD_LIBRARY_PATH for OpenMPI
    ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    if '/opt/openmpi' not in ld_path and '/usr/lib/x86_64-linux-gnu/openmpi' not in ld_path:
        issues.append("LD_LIBRARY_PATH missing OpenMPI path (will cause import errors)")

    # Check for Forge conflicts
    forge_conflict = False
    if os.environ.get('TT_METAL_HOME') and os.environ.get('PYTHONPATH'):
        if 'forge' in os.environ.get('PYTHONPATH', '').lower():
            forge_conflict = True
            issues.append(
                "Potential TT-Forge conflict: TT_METAL_HOME set with Forge in PYTHONPATH. "
                "Run 'tt env use forge' to fix."
            )

    return {
        'status': 'ok' if not issues else 'error',
        'issues': issues,
        'warnings': warnings,
        'forge_conflict': forge_conflict,
    }


def fix_environment(apply_to_os_environ=True):
    """
    Auto-fix common environment issues.

    Args:
        apply_to_os_environ: If True, apply fixes to os.environ (default).
                             If False, only return the env vars to set.

    Returns:
        Tuple of (fixes_list, env_vars_dict)
        - fixes_list: List of human-readable descriptions of fixes
        - env_vars_dict: Dictionary of env vars to set {var_name: value}
    """
    fixes = []
    env_vars = {}

    # Fix LD_LIBRARY_PATH for OpenMPI
    ld_path = os.environ.get('LD_LIBRARY_PATH', '')

    openmpi_paths = [
        '/opt/openmpi-v5.0.7-ulfm/lib',
        '/usr/lib/x86_64-linux-gnu/openmpi/lib',
    ]

    for path in openmpi_paths:
        if Path(path).exists() and path not in ld_path:
            if ld_path:
                new_ld_path = f"{path}:{ld_path}"
            else:
                new_ld_path = path

            env_vars['LD_LIBRARY_PATH'] = new_ld_path
            if apply_to_os_environ:
                os.environ['LD_LIBRARY_PATH'] = new_ld_path
            fixes.append(f"Added {path} to LD_LIBRARY_PATH")
            break

    # Fix TT_METAL_HOME if tt-metal exists in standard location
    if not os.environ.get('TT_METAL_HOME'):
        tt_metal_home = Path.home() / 'tt-metal'
        if tt_metal_home.exists():
            env_vars['TT_METAL_HOME'] = str(tt_metal_home)
            if apply_to_os_environ:
                os.environ['TT_METAL_HOME'] = str(tt_metal_home)
            fixes.append(f"Set TT_METAL_HOME to {tt_metal_home}")

    # Fix PYTHONPATH
    tt_metal_home = env_vars.get('TT_METAL_HOME') or os.environ.get('TT_METAL_HOME')
    if tt_metal_home:
        pythonpath = os.environ.get('PYTHONPATH', '')
        if tt_metal_home not in pythonpath:
            if pythonpath:
                new_pythonpath = f"{tt_metal_home}:{pythonpath}"
            else:
                new_pythonpath = tt_metal_home

            env_vars['PYTHONPATH'] = new_pythonpath
            if apply_to_os_environ:
                os.environ['PYTHONPATH'] = new_pythonpath
            fixes.append(f"Added {tt_metal_home} to PYTHONPATH")

    return (fixes, env_vars)


def install_uv():
    """Install uv package manager."""
    print("Installing uv...")
    print("This will make environment operations 10-100x faster!")
    print()

    # Install uv using pip
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'uv'],
            check=True,
        )
        print("✓ uv installed successfully")
        print()
        print("You can now use 'tt env setup' with --python flag to create")
        print("environments with specific Python versions.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install uv: {e}")
        return False


def get_venv_python_version(venv_path: Path) -> Optional[str]:
    """
    Get Python version of a virtual environment.

    Args:
        venv_path: Path to venv

    Returns:
        Version string like "3.10.12" or None if can't determine
    """
    venv_path = Path(venv_path).expanduser()
    python_bin = venv_path / 'bin' / 'python'

    if not python_bin.exists():
        return None

    try:
        result = subprocess.run(
            [str(python_bin), '--version'],
            capture_output=True,
            text=True,
            timeout=2,
        )
        # Output format: "Python 3.10.12"
        version = result.stdout.strip().split()[1]
        return version
    except:
        return None


def check_vllm_patches() -> dict:
    """
    Check if required vLLM patches are applied for custom model support.

    These patches improve compatibility with custom TT models:
    1. Model registration patch - Ensures TT models are registered in worker subprocesses
    2. Block size default patch - Sets sensible block_size=64 default

    Returns:
        Dict with patch status:
        {
            'model_registration': bool,  # _ensure_tt_models_registered patch
            'block_size_default': bool,  # block_size=64 default patch
            'vllm_path': Path,           # Path to tt-vllm installation
            'warnings': list,            # List of warnings
        }
    """
    result = {
        'model_registration': False,
        'block_size_default': False,
        'vllm_path': None,
        'warnings': [],
    }

    # Find tt-vllm installation
    # Check both source directory and installed site-packages
    vllm_paths = [
        Path.home() / 'tt-vllm',
        Path.home() / 'tt-metal' / 'build' / 'python_env_vllm' / 'lib' / 'python3.12' / 'site-packages' / 'vllm',
    ]

    for vllm_path in vllm_paths:
        if vllm_path.exists():
            result['vllm_path'] = vllm_path
            break

    if not result['vllm_path']:
        result['warnings'].append("vLLM installation not found")
        return result

    # Check for model registration patch in tt.py platform file
    # Handle both source directory structure and installed package structure
    possible_tt_files = [
        result['vllm_path'] / 'vllm' / 'platforms' / 'tt.py',  # Source directory
        result['vllm_path'] / 'platforms' / 'tt.py',           # Installed package
    ]

    tt_platform_file = None
    for possible_file in possible_tt_files:
        if possible_file.exists():
            tt_platform_file = possible_file
            break

    if tt_platform_file and tt_platform_file.exists():
        content = tt_platform_file.read_text()

        # Check for model registration patch
        if '_ensure_tt_models_registered' in content:
            result['model_registration'] = True
        else:
            result['warnings'].append(
                "Model registration patch missing in vllm/platforms/tt.py. "
                "Custom models may fail with 'model not registered' error. "
                "See ASCII_MODEL_SOLUTION.md for patch details."
            )

        # Check for block size default patch
        if 'block_size = 64' in content or 'block_size=64' in content:
            result['block_size_default'] = True
        else:
            result['warnings'].append(
                "Block size default patch missing in vllm/platforms/tt.py. "
                "May cause 'NoneType multiplication' errors. "
                "See ASCII_MODEL_SOLUTION.md for patch details."
            )
    else:
        result['warnings'].append("vllm/platforms/tt.py not found")

    return result
