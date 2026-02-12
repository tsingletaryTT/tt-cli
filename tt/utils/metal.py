"""
TT-Metal installation management utilities.

Provides functions for managing multiple TT-Metal installations:
- Checkout specific versions from git
- Track installed versions in config
- Switch between versions
- Build and setup environments
"""

import json
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, List
from tt.utils import config as cfg


DEFAULT_METAL_REPO = "https://github.com/tenstorrent/tt-metal.git"
DEFAULT_INSTALL_BASE = Path.home() / "tt-metal-versions"


def has_git() -> bool:
    """Check if git is available."""
    return shutil.which('git') is not None


def has_cmake() -> bool:
    """Check if cmake is available."""
    return shutil.which('cmake') is not None


def has_uv() -> bool:
    """Check if uv is available for fast venv operations."""
    return shutil.which('uv') is not None


def get_metal_installations() -> Dict[str, Dict]:
    """
    Get all registered TT-Metal installations from config.

    Returns:
        Dict mapping version tags to installation info:
        {
            'v0.66.0-rc7': {
                'path': '/home/user/tt-metal-versions/v0.66.0-rc7',
                'tag': 'v0.66.0-rc7',
                'python_env': '/home/user/tt-metal-versions/v0.66.0-rc7/python_env',
                'vllm_env': '/home/user/tt-metal-versions/v0.66.0-rc7/build/python_env_vllm',
                'created': '2026-01-30T10:30:00Z',
            }
        }
    """
    conf = cfg.load_config()
    return conf.get('metal', {}).get('installations', {})


def get_active_metal() -> Optional[str]:
    """
    Get the currently active TT-Metal version.

    Returns:
        Version tag string (e.g., 'v0.66.0-rc7') or None if not set
    """
    conf = cfg.load_config()
    return conf.get('metal', {}).get('active')


def set_active_metal(version: str) -> None:
    """
    Set the active TT-Metal version in config.

    Args:
        version: Version tag to set as active
    """
    conf = cfg.load_config()

    if 'metal' not in conf:
        conf['metal'] = {}

    conf['metal']['active'] = version
    cfg.save_config(conf)


def register_metal_installation(
    version: str,
    path: Path,
    tag: str,
    python_env: Optional[Path] = None,
    vllm_env: Optional[Path] = None,
) -> None:
    """
    Register a TT-Metal installation in config.

    Args:
        version: Version identifier (e.g., 'v0.66.0-rc7')
        path: Path to installation directory
        tag: Git tag used for checkout
        python_env: Path to python_env directory (optional)
        vllm_env: Path to vllm environment directory (optional)
    """
    conf = cfg.load_config()

    if 'metal' not in conf:
        conf['metal'] = {}
    if 'installations' not in conf['metal']:
        conf['metal']['installations'] = {}

    from datetime import datetime

    conf['metal']['installations'][version] = {
        'path': str(path),
        'tag': tag,
        'python_env': str(python_env) if python_env else None,
        'vllm_env': str(vllm_env) if vllm_env else None,
        'created': datetime.utcnow().isoformat() + 'Z',
    }

    cfg.save_config(conf)


def unregister_metal_installation(version: str) -> None:
    """
    Remove a TT-Metal installation from config.

    Args:
        version: Version identifier to remove
    """
    conf = cfg.load_config()

    if 'metal' in conf and 'installations' in conf['metal']:
        if version in conf['metal']['installations']:
            del conf['metal']['installations'][version]

            # If this was the active version, clear it
            if conf['metal'].get('active') == version:
                conf['metal']['active'] = None

            cfg.save_config(conf)


def checkout_metal(
    tag: str,
    path: Path,
    force_update_submodules: bool = True,
) -> int:
    """
    Checkout TT-Metal at specific tag.

    Args:
        tag: Git tag to checkout (e.g., 'v0.66.0-rc7')
        path: Installation path
        force_update_submodules: Force update all submodules

    Returns:
        Exit code (0 = success)
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Clone repository
    print(f"Cloning TT-Metal from {DEFAULT_METAL_REPO}...")
    result = subprocess.run(
        ['git', 'clone', DEFAULT_METAL_REPO, str(path)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ Clone failed: {result.stderr}")
        return result.returncode

    # Checkout specific tag
    print(f"Checking out tag {tag}...")
    result = subprocess.run(
        ['git', 'checkout', tag],
        cwd=str(path),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ Checkout failed: {result.stderr}")
        return result.returncode

    # Update submodules
    print("Updating submodules...")
    if force_update_submodules:
        cmd = ['git', 'submodule', 'update', '--init', '--recursive', '--force']
    else:
        cmd = ['git', 'submodule', 'update', '--init', '--recursive']

    result = subprocess.run(
        cmd,
        cwd=str(path),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ Submodule update failed: {result.stderr}")
        return result.returncode

    print("✓ Checkout complete")
    return 0


def install_dependencies(metal_path: Path) -> int:
    """
    Install TT-Metal dependencies using install_dependencies.sh.

    Args:
        metal_path: Path to TT-Metal installation

    Returns:
        Exit code (0 = success)
    """
    install_script = metal_path / "install_dependencies.sh"

    if not install_script.exists():
        print(f"❌ install_dependencies.sh not found at {install_script}")
        return 1

    print("Installing dependencies (requires sudo)...")
    result = subprocess.run(
        ['sudo', 'bash', str(install_script)],
        cwd=str(metal_path),
    )

    return result.returncode


def build_metal(
    metal_path: Path,
    build_tt_train: bool = True,
    clean: bool = False,
) -> int:
    """
    Build TT-Metal using cmake.

    Args:
        metal_path: Path to TT-Metal installation
        build_tt_train: Include tt-train in build
        clean: Clean build directory first

    Returns:
        Exit code (0 = success)
    """
    build_dir = metal_path / "build"

    if clean and build_dir.exists():
        print("Cleaning build directory...")
        shutil.rmtree(build_dir)

    build_dir.mkdir(exist_ok=True)

    # Configure with cmake
    print("Configuring build with cmake...")
    cmake_args = [
        'cmake',
        '-G', 'Ninja',
        '..',
    ]

    if build_tt_train:
        cmake_args.append('-DTT_METAL_BUILD_TT_TRAIN=ON')

    result = subprocess.run(
        cmake_args,
        cwd=str(build_dir),
    )

    if result.returncode != 0:
        print("❌ CMake configuration failed")
        return result.returncode

    # Build
    print("Building TT-Metal (this may take several minutes)...")
    result = subprocess.run(
        ['cmake', '--build', '.', '--parallel'],
        cwd=str(build_dir),
    )

    if result.returncode != 0:
        print("❌ Build failed")
        return result.returncode

    print("✓ Build complete")
    return 0


def create_python_env(
    metal_path: Path,
    python_version: str = "3.12",
    use_uv: bool = True,
) -> int:
    """
    Create python_env for TT-Metal.

    Args:
        metal_path: Path to TT-Metal installation
        python_version: Python version to use
        use_uv: Use uv if available (much faster)

    Returns:
        Exit code (0 = success)
    """
    create_script = metal_path / "create_venv.sh"

    if not create_script.exists():
        print(f"❌ create_venv.sh not found at {create_script}")
        return 1

    print(f"Creating python_env with Python {python_version}...")

    env = os.environ.copy()
    env['PYTHON_VERSION'] = python_version

    result = subprocess.run(
        ['bash', str(create_script)],
        cwd=str(metal_path),
        env=env,
    )

    if result.returncode != 0:
        print("❌ Python environment creation failed")
        return result.returncode

    print("✓ Python environment created")
    return 0


def create_vllm_env(
    metal_path: Path,
    python_version: str = "3.12",
) -> int:
    """
    Create vLLM environment for TT-Metal.

    Args:
        metal_path: Path to TT-Metal installation
        python_version: Python version to use

    Returns:
        Exit code (0 = success)
    """
    vllm_script = metal_path / "vllm_create_venv.sh"

    if not vllm_script.exists():
        print(f"❌ vllm_create_venv.sh not found at {vllm_script}")
        return 1

    print(f"Creating vLLM environment with Python {python_version}...")

    env = os.environ.copy()
    env['PYTHON_VERSION'] = python_version

    result = subprocess.run(
        ['bash', str(vllm_script)],
        cwd=str(metal_path),
        env=env,
    )

    if result.returncode != 0:
        print("❌ vLLM environment creation failed")
        return result.returncode

    print("✓ vLLM environment created")
    return 0


def install_vllm_dependencies(metal_path: Path) -> int:
    """
    Install additional dependencies in vLLM environment.

    This includes the TT fork of llama-models and other required packages.

    Args:
        metal_path: Path to TT-Metal installation

    Returns:
        Exit code (0 = success)
    """
    vllm_env = metal_path / "build" / "python_env_vllm"
    pip_path = vllm_env / "bin" / "pip"

    if not pip_path.exists():
        print(f"❌ vLLM environment not found at {vllm_env}")
        return 1

    print("Installing TT fork of llama-models...")
    result = subprocess.run(
        [
            str(pip_path),
            'install',
            'git+https://github.com/tenstorrent/llama-models.git@tt_metal_tag',
        ],
    )

    if result.returncode != 0:
        print("❌ Failed to install llama-models")
        return result.returncode

    print("Installing additional dependencies (loguru, pytest)...")
    result = subprocess.run(
        [
            str(pip_path),
            'install',
            'loguru',
            'pytest',
        ],
    )

    if result.returncode != 0:
        print("❌ Failed to install dependencies")
        return result.returncode

    print("✓ vLLM dependencies installed")
    return 0


def get_metal_info(version: str) -> Optional[Dict]:
    """
    Get information about a specific TT-Metal installation.

    Args:
        version: Version identifier

    Returns:
        Installation info dict or None if not found
    """
    installations = get_metal_installations()
    return installations.get(version)


def validate_metal_installation(path: Path) -> Dict:
    """
    Validate a TT-Metal installation.

    Args:
        path: Path to TT-Metal installation

    Returns:
        Dict with validation results:
        {
            'valid': bool,
            'issues': [str],
            'python_env_exists': bool,
            'vllm_env_exists': bool,
            'build_exists': bool,
        }
    """
    issues = []

    # Check directory exists
    if not path.exists():
        return {
            'valid': False,
            'issues': [f"Installation directory not found: {path}"],
            'python_env_exists': False,
            'vllm_env_exists': False,
            'build_exists': False,
        }

    # Check python_env
    python_env = path / "python_env"
    python_env_exists = python_env.exists()
    if not python_env_exists:
        issues.append("python_env not found")

    # Check vllm environment
    vllm_env = path / "build" / "python_env_vllm"
    vllm_env_exists = vllm_env.exists()
    if not vllm_env_exists:
        issues.append("vLLM environment not found")

    # Check build directory
    build_dir = path / "build"
    build_exists = build_dir.exists()
    if not build_exists:
        issues.append("build directory not found")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'python_env_exists': python_env_exists,
        'vllm_env_exists': vllm_env_exists,
        'build_exists': build_exists,
    }


def parse_version_spec(spec: str) -> tuple[str, Optional[str]]:
    """
    Parse environment@version specification.

    Args:
        spec: Environment spec like "metal" or "metal@v0.66.0-rc7"

    Returns:
        Tuple of (env_name, version) where version is None if not specified

    Examples:
        >>> parse_version_spec("metal")
        ("metal", None)
        >>> parse_version_spec("metal@v0.66.0-rc7")
        ("metal", "v0.66.0-rc7")
    """
    if '@' in spec:
        parts = spec.split('@', 1)
        return parts[0], parts[1]
    else:
        return spec, None
