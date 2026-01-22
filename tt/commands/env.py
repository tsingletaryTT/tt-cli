"""
Environment management commands
"""

from pathlib import Path

from tt.utils import envmanager


def use(args):
    """Switch to specified environment."""
    env_name = args.name

    print(f"Switching to {env_name} environment...")
    print()

    try:
        env_vars = envmanager.activate_environment(env_name)

        # Show what was set/unset
        print("Environment configured:")
        for var, value in env_vars.items():
            if value is None:
                print(f"  ✓ Unset {var}")
            else:
                # Truncate long values
                display_value = value if len(value) < 60 else value[:57] + '...'
                print(f"  ✓ Set {var}={display_value}")

        print()
        print(f"✓ Activated {envmanager.ENVIRONMENTS[env_name]['name']} environment")
        print()
        print("Note: These changes affect the current shell only.")
        print("      For persistent changes, add to ~/.bashrc")

    except ValueError as e:
        print(f"✗ Error: {e}")
        return 1


def list_envs(args):
    """List available environments."""
    print()
    print("Available Environments")
    print("=" * 70)
    print()

    for name, config in envmanager.ENVIRONMENTS.items():
        venv_path = Path(config['venv_path']).expanduser()
        exists = venv_path.exists()

        status = "✓" if exists else "✗"
        status_text = "exists" if exists else "not created"

        print(f"{status} {name}")
        print(f"   Name: {config['name']}")
        print(f"   Path: {config['venv_path']} ({status_text})")
        print(f"   Description: {config['description']}")

        if exists:
            version = envmanager.get_venv_python_version(venv_path)
            if version:
                print(f"   Python: {version}")

        print()

    print("Use 'tt env use <name>' to switch environments")
    print("Use 'tt env setup <name>' to create missing environments")
    print()


def setup(args):
    """Create new environment."""
    env_name = args.name
    python_version = args.python

    # Check if this is a standard environment
    if env_name in envmanager.ENVIRONMENTS:
        config = envmanager.ENVIRONMENTS[env_name]
        venv_path = Path(config['venv_path']).expanduser()

        print(f"Setting up {config['name']} environment...")
        print(f"Path: {venv_path}")
        print()

        if venv_path.exists():
            print(f"⚠️  Environment already exists at {venv_path}")
            response = input("Recreate? [y/N]: ")
            if response.lower() != 'y':
                print("Cancelled")
                return 1

            import shutil
            shutil.rmtree(venv_path)
            print(f"✓ Removed existing environment")

        # Create venv
        print("Creating virtual environment...")
        tool = envmanager.create_venv(venv_path, python_version)
        print(f"✓ Created using {tool}")

        # TODO: Install packages based on environment type
        # For now, just create the venv
        print()
        print(f"✓ Environment created at {venv_path}")
        print()
        print(f"Next steps:")
        print(f"  1. Activate: tt env use {env_name}")
        print(f"  2. Install packages as needed")

    else:
        # Custom environment
        custom_path = Path.home() / '.tt' / 'envs' / env_name

        print(f"Creating custom environment: {env_name}")
        print(f"Path: {custom_path}")
        print()

        if custom_path.exists():
            print(f"⚠️  Environment already exists")
            return 1

        tool = envmanager.create_venv(custom_path, python_version)
        print(f"✓ Created using {tool}")
        print()
        print(f"Environment created at {custom_path}")
        print(f"Activate with: source {custom_path}/bin/activate")


def check(args):
    """Check current environment for issues."""
    print()
    print("Checking environment...")
    print()

    result = envmanager.check_environment()

    if result['status'] == 'ok':
        print("✓ Environment looks good!")
    else:
        print("✗ Issues found:")

    print()

    # Show issues
    if result['issues']:
        print("Issues:")
        for issue in result['issues']:
            print(f"  ✗ {issue}")
        print()

    # Show warnings
    if result['warnings']:
        print("Warnings:")
        for warning in result['warnings']:
            print(f"  ⚠️  {warning}")
        print()

    # Suggestions
    if result['issues'] or result['warnings']:
        print("Suggestions:")
        print("  • Run 'tt env fix' to auto-fix common issues")
        if result['forge_conflict']:
            print("  • Run 'tt env use forge' to properly configure TT-Forge")
        print()


def fix(args):
    """Auto-fix common environment issues."""
    # Check if --export mode (for eval)
    export_mode = getattr(args, 'export', False)

    if export_mode:
        # Export mode - output shell commands for eval
        fixes, env_vars = envmanager.fix_environment(apply_to_os_environ=False)

        # Print export statements
        for var, value in env_vars.items():
            # Escape value for shell safety
            safe_value = value.replace('"', '\\"')
            print(f'export {var}="{safe_value}"')

        return 0

    # Normal mode - human-readable output
    print()
    print("Fixing environment issues...")
    print()

    fixes, env_vars = envmanager.fix_environment(apply_to_os_environ=True)

    if not fixes:
        print("✓ No fixes needed - environment is already configured correctly")
    else:
        print("Applied fixes:")
        for fix in fixes:
            print(f"  ✓ {fix}")

        print()
        print("⚠️  Note: These changes only affect subprocesses started by this command.")
        print("   To apply to your current shell, use:")
        print()
        print('   eval "$(tt env fix --export)"')

    print()
    print("Run 'tt env check' to verify")
    print()


def install_uv(args):
    """Install uv package manager."""
    print()

    if envmanager.has_uv():
        print("✓ uv is already installed")
        import shutil
        uv_path = shutil.which('uv')
        print(f"   Location: {uv_path}")
        print()
        return 0

    print("Installing uv package manager...")
    print("This will make environment operations 10-100x faster!")
    print()

    success = envmanager.install_uv()

    if success:
        print()
        print("Benefits:")
        print("  • 10-100x faster package installs")
        print("  • Automatic Python version management")
        print("  • Better dependency resolution")
        print()
        print("Usage:")
        print("  tt env setup myenv --python 3.10")
        print()
        return 0
    else:
        return 1
