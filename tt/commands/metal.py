"""
TT-Metal installation management commands.

Provides commands for managing multiple TT-Metal installations:
- checkout: Clone and build specific TT-Metal versions
- list: Show all installed versions
- use: Switch active version
- info: Show installation details
- remove: Remove an installation
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from tt.utils import metal, config as cfg


def checkout(args):
    """
    Checkout and build a specific TT-Metal version.

    This command:
    1. Clones TT-Metal at specified tag
    2. Updates submodules
    3. Installs dependencies (requires sudo)
    4. Builds with cmake
    5. Creates python environments
    6. Registers installation in config

    Example:
        tt metal checkout --tag v0.66.0-rc7
        tt metal checkout --tag v0.66.0-rc7 --path ~/custom/path
    """
    print()

    # Check prerequisites
    if not metal.has_git():
        print("❌ git not found")
        print("   Install with: sudo apt install git")
        print()
        return 1

    if not metal.has_cmake():
        print("❌ cmake not found")
        print("   Install with: sudo apt install cmake ninja-build")
        print()
        return 1

    tag = args.tag
    version = tag  # Use tag as version identifier

    # Determine installation path
    if args.path:
        install_path = Path(args.path).expanduser().resolve()
    else:
        # Default: ~/tt-metal-versions/<tag>
        install_path = metal.DEFAULT_INSTALL_BASE / tag
        install_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if already exists
    if install_path.exists() and not args.force:
        print(f"❌ Installation already exists at {install_path}")
        print("   Use --force to overwrite")
        print()
        return 1

    if install_path.exists() and args.force:
        print(f"⚠ Removing existing installation at {install_path}")
        import shutil
        shutil.rmtree(install_path)

    # Checkout
    print(f"Checking out TT-Metal {tag}...")
    print(f"Installation path: {install_path}")
    print()

    exit_code = metal.checkout_metal(
        tag=tag,
        path=install_path,
        force_update_submodules=True,
    )

    if exit_code != 0:
        print()
        print("❌ Checkout failed")
        print()
        return exit_code

    print()

    # Install dependencies
    if not args.skip_deps:
        print("Installing system dependencies...")
        exit_code = metal.install_dependencies(install_path)

        if exit_code != 0:
            print()
            print("❌ Dependency installation failed")
            print("   You can retry with: tt metal setup " + version)
            print()
            return exit_code

        print("✓ Dependencies installed")
        print()

    # Build
    if not args.skip_build:
        print("Building TT-Metal...")
        exit_code = metal.build_metal(
            metal_path=install_path,
            build_tt_train=args.build_tt_train,
            clean=False,
        )

        if exit_code != 0:
            print()
            print("❌ Build failed")
            print("   You can retry with: tt metal build " + version)
            print()
            return exit_code

        print()

    # Create python_env
    if not args.skip_env:
        python_version = args.python or "3.12"
        print(f"Creating python_env (Python {python_version})...")
        exit_code = metal.create_python_env(
            metal_path=install_path,
            python_version=python_version,
            use_uv=metal.has_uv(),
        )

        if exit_code != 0:
            print()
            print("❌ Python environment creation failed")
            print("   You can retry with: tt metal setup " + version)
            print()
            return exit_code

        print()

    # Create vLLM environment
    if not args.skip_vllm:
        python_version = args.python or "3.12"
        print(f"Creating vLLM environment (Python {python_version})...")
        exit_code = metal.create_vllm_env(
            metal_path=install_path,
            python_version=python_version,
        )

        if exit_code != 0:
            print()
            print("❌ vLLM environment creation failed")
            print("   You can retry with: tt metal setup " + version + " --vllm-only")
            print()
            return exit_code

        print()

        # Install vLLM dependencies
        print("Installing vLLM dependencies (TT llama-models, loguru, pytest)...")
        exit_code = metal.install_vllm_dependencies(install_path)

        if exit_code != 0:
            print()
            print("❌ vLLM dependency installation failed")
            print("   You can retry with: tt metal setup " + version + " --vllm-only")
            print()
            return exit_code

        print()

    # Register installation
    python_env = install_path / "python_env" if (install_path / "python_env").exists() else None
    vllm_env = install_path / "build" / "python_env_vllm" if (install_path / "build" / "python_env_vllm").exists() else None

    metal.register_metal_installation(
        version=version,
        path=install_path,
        tag=tag,
        python_env=python_env,
        vllm_env=vllm_env,
    )

    # Set as active if requested
    if args.set_active:
        metal.set_active_metal(version)
        print(f"✓ Set {version} as active version")
        print()

    print("✓ TT-Metal installation complete")
    print()
    print(f"To use this version:")
    print(f"  tt metal use {version}")
    print(f"  tt env use metal@{version}")
    print()

    return 0


def list_installations(args):
    """
    List all installed TT-Metal versions.

    Shows version, path, and active status.
    """
    print()

    installations = metal.get_metal_installations()

    if not installations:
        print("No TT-Metal installations found")
        print()
        print("To install a version:")
        print("  tt metal checkout --tag v0.66.0-rc7")
        print()
        return 0

    active_version = metal.get_active_metal()

    # JSON output
    if args.json:
        output = {
            'installations': installations,
            'active': active_version,
        }
        print(json.dumps(output, indent=2))
        print()
        return 0

    # Human-readable output
    print("Installed TT-Metal Versions:")
    print()

    for version, info in installations.items():
        # Check if active
        is_active = version == active_version
        prefix = "✓" if is_active else "•"
        active_indicator = " (active)" if is_active else ""

        print(f"{prefix} {version}{active_indicator}")
        print(f"  Path: {info['path']}")

        # Validate installation
        validation = metal.validate_metal_installation(Path(info['path']))
        if validation['valid']:
            print("  Status: ✓ Valid")
        else:
            print(f"  Status: ⚠ Issues found")
            for issue in validation['issues']:
                print(f"    - {issue}")

        print()

    print(f"Total: {len(installations)} installation(s)")
    print()

    if not active_version:
        print("No active version set. Use 'tt metal use <version>' to set one.")
        print()

    return 0


def use(args):
    """
    Switch active TT-Metal version.

    This sets the default version for 'tt env use metal' commands.
    """
    print()

    version = args.version
    installations = metal.get_metal_installations()

    if version not in installations:
        print(f"❌ Version {version} not found")
        print()
        print("Available versions:")
        for v in installations.keys():
            print(f"  • {v}")
        print()
        print("To install a version:")
        print("  tt metal checkout --tag <version>")
        print()
        return 1

    # Validate installation
    info = installations[version]
    validation = metal.validate_metal_installation(Path(info['path']))

    if not validation['valid']:
        print(f"⚠ Warning: Installation has issues:")
        for issue in validation['issues']:
            print(f"  • {issue}")
        print()

        if not args.force:
            print("Use --force to set as active anyway")
            print()
            return 1

    # Set as active
    metal.set_active_metal(version)

    print(f"✓ Active TT-Metal version set to: {version}")
    print()
    print("To activate this environment:")
    print(f"  tt env use metal")
    print(f"  # or")
    print(f"  tt env use metal@{version}")
    print()

    return 0


def info(args):
    """
    Show detailed information about a TT-Metal installation.
    """
    print()

    version = args.version
    installations = metal.get_metal_installations()

    if version not in installations:
        print(f"❌ Version {version} not found")
        print()
        return 1

    info_dict = installations[version]
    install_path = Path(info_dict['path'])

    # JSON output
    if args.json:
        validation = metal.validate_metal_installation(install_path)
        output = {
            **info_dict,
            'validation': validation,
            'active': version == metal.get_active_metal(),
        }
        print(json.dumps(output, indent=2))
        print()
        return 0

    # Human-readable output
    is_active = version == metal.get_active_metal()
    active_indicator = " (active)" if is_active else ""

    print(f"TT-Metal Installation: {version}{active_indicator}")
    print()

    print(f"Git Tag: {info_dict['tag']}")
    print(f"Path: {info_dict['path']}")
    print(f"Created: {info_dict['created']}")
    print()

    print("Environments:")
    if info_dict.get('python_env'):
        print(f"  Python: {info_dict['python_env']}")
    else:
        print("  Python: Not configured")

    if info_dict.get('vllm_env'):
        print(f"  vLLM: {info_dict['vllm_env']}")
    else:
        print("  vLLM: Not configured")

    print()

    # Validation
    validation = metal.validate_metal_installation(install_path)
    if validation['valid']:
        print("Status: ✓ Valid installation")
    else:
        print("Status: ⚠ Issues found")
        for issue in validation['issues']:
            print(f"  • {issue}")

    print()

    return 0


def remove(args):
    """
    Remove a TT-Metal installation.

    This removes the installation directory and unregisters from config.
    """
    print()

    version = args.version
    installations = metal.get_metal_installations()

    if version not in installations:
        print(f"❌ Version {version} not found")
        print()
        return 1

    info = installations[version]
    install_path = Path(info['path'])

    # Show what will be removed
    print(f"This will remove TT-Metal {version}:")
    print(f"  Path: {install_path}")
    print()

    # Confirmation
    if not args.yes:
        response = input("Continue? [y/N]: ")
        print()

        if response.lower() not in ['y', 'yes']:
            print("Cancelled")
            print()
            return 0

    # Remove directory
    if install_path.exists():
        print(f"Removing installation directory...")
        import shutil
        shutil.rmtree(install_path)
        print("✓ Directory removed")
    else:
        print("⚠ Installation directory not found (already removed?)")

    # Unregister from config
    metal.unregister_metal_installation(version)
    print("✓ Unregistered from config")
    print()

    return 0


def build(args):
    """
    Build a TT-Metal installation.

    Useful for rebuilding after code changes or if initial build failed.
    """
    print()

    version = args.version
    installations = metal.get_metal_installations()

    if version not in installations:
        print(f"❌ Version {version} not found")
        print()
        return 1

    info = installations[version]
    install_path = Path(info['path'])

    if not install_path.exists():
        print(f"❌ Installation directory not found: {install_path}")
        print()
        return 1

    print(f"Building TT-Metal {version}...")
    print()

    exit_code = metal.build_metal(
        metal_path=install_path,
        build_tt_train=args.build_tt_train,
        clean=args.clean,
    )

    if exit_code != 0:
        print()
        print("❌ Build failed")
        print()
        return exit_code

    print()
    print("✓ Build complete")
    print()

    return 0


def setup(args):
    """
    Setup environments for a TT-Metal installation.

    Creates python_env and/or vLLM environment.
    Useful for fixing incomplete installations.
    """
    print()

    version = args.version
    installations = metal.get_metal_installations()

    if version not in installations:
        print(f"❌ Version {version} not found")
        print()
        return 1

    info = installations[version]
    install_path = Path(info['path'])

    if not install_path.exists():
        print(f"❌ Installation directory not found: {install_path}")
        print()
        return 1

    python_version = args.python or "3.12"

    # Create python_env (unless --vllm-only)
    if not args.vllm_only:
        print(f"Creating python_env (Python {python_version})...")
        exit_code = metal.create_python_env(
            metal_path=install_path,
            python_version=python_version,
            use_uv=metal.has_uv(),
        )

        if exit_code != 0:
            print()
            print("❌ Python environment creation failed")
            print()
            return exit_code

        print("✓ Python environment created")
        print()

    # Create vLLM environment
    print(f"Creating vLLM environment (Python {python_version})...")
    exit_code = metal.create_vllm_env(
        metal_path=install_path,
        python_version=python_version,
    )

    if exit_code != 0:
        print()
        print("❌ vLLM environment creation failed")
        print()
        return exit_code

    print()

    # Install vLLM dependencies
    print("Installing vLLM dependencies...")
    exit_code = metal.install_vllm_dependencies(install_path)

    if exit_code != 0:
        print()
        print("❌ vLLM dependency installation failed")
        print()
        return exit_code

    print()
    print("✓ Setup complete")
    print()

    # Update config
    python_env = install_path / "python_env"
    vllm_env = install_path / "build" / "python_env_vllm"

    metal.register_metal_installation(
        version=version,
        path=install_path,
        tag=info['tag'],
        python_env=python_env if python_env.exists() else None,
        vllm_env=vllm_env if vllm_env.exists() else None,
    )

    return 0
