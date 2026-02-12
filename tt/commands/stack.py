"""
Stack management commands for tt-cli.

Stacks are pre-configured deployment setups combining:
- TT-Metal version
- Model
- Hardware configuration
- Server settings

This enables tt-jukebox-style workflows.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from tt.utils import stack as stackutils


def list_stacks(args):
    """
    List all available stacks.

    Shows both default stacks and user-defined stacks.
    """
    print()

    stacks = stackutils.get_stacks()

    if not stacks:
        print("No stacks found")
        print()
        print("Create a stack with:")
        print("  tt stack create <name>")
        print()
        return 0

    active_stack = stackutils.get_active_stack()

    # JSON output
    if args.json:
        output = {
            'stacks': stacks,
            'active': active_stack,
        }
        print(json.dumps(output, indent=2))
        print()
        return 0

    # Human-readable output
    print("Available Stacks:")
    print()

    # Separate default and user stacks
    default_stacks = {k: v for k, v in stacks.items() if k in stackutils.DEFAULT_STACKS}
    user_stacks = {k: v for k, v in stacks.items() if k not in stackutils.DEFAULT_STACKS}

    # Show default stacks
    if default_stacks:
        print("Default Stacks:")
        for name, stack_config in default_stacks.items():
            is_active = name == active_stack
            prefix = "✓" if is_active else "•"
            active_indicator = " (active)" if is_active else ""

            print(f"{prefix} {name}{active_indicator}")
            if 'description' in stack_config:
                print(f"  Description: {stack_config['description']}")
            print(f"  Metal: {stack_config.get('metal', 'not specified')}")
            print(f"  Model: {stack_config.get('model', 'not specified')}")
            print(f"  Hardware: {stack_config.get('hardware', 'auto-detect')}")

            # Validate stack
            validation = stackutils.validate_stack(stack_config)
            if validation['valid'] and not validation['warnings']:
                print("  Status: ✓ Ready")
            elif validation['valid']:
                print(f"  Status: ⚠ {len(validation['warnings'])} warning(s)")
            else:
                print(f"  Status: ❌ {len(validation['issues'])} issue(s)")

            print()

    # Show user stacks
    if user_stacks:
        print("User-Defined Stacks:")
        for name, stack_config in user_stacks.items():
            is_active = name == active_stack
            prefix = "✓" if is_active else "•"
            active_indicator = " (active)" if is_active else ""

            print(f"{prefix} {name}{active_indicator}")
            if 'description' in stack_config:
                print(f"  Description: {stack_config['description']}")
            print(f"  Metal: {stack_config.get('metal', 'not specified')}")
            print(f"  Model: {stack_config.get('model', 'not specified')}")
            print(f"  Hardware: {stack_config.get('hardware', 'auto-detect')}")

            # Validate stack
            validation = stackutils.validate_stack(stack_config)
            if validation['valid'] and not validation['warnings']:
                print("  Status: ✓ Ready")
            elif validation['valid']:
                print(f"  Status: ⚠ {len(validation['warnings'])} warning(s)")
            else:
                print(f"  Status: ❌ {len(validation['issues'])} issue(s)")

            print()

    if not active_stack:
        print("No active stack. Use 'tt stack use <name>' to activate one.")
        print()

    return 0


def use(args):
    """
    Activate a stack.

    This sets up the environment for the stack:
    - Activates TT-Metal version
    - Sets environment variables
    - Marks stack as active
    """
    print()

    stack_name = args.name
    stacks = stackutils.get_stacks()

    if stack_name not in stacks:
        print(f"❌ Stack '{stack_name}' not found")
        print()
        print("Available stacks:")
        for name in stacks.keys():
            print(f"  • {name}")
        print()
        return 1

    stack_config = stacks[stack_name]

    # Validate stack
    print(f"Validating stack '{stack_name}'...")
    validation = stackutils.validate_stack(stack_config)

    if not validation['valid']:
        print()
        print("❌ Stack validation failed:")
        for issue in validation['issues']:
            print(f"  • {issue}")
        print()
        return 1

    # Show warnings
    if validation['warnings']:
        print()
        print("⚠ Warnings:")
        for warning in validation['warnings']:
            print(f"  • {warning}")
        print()

        if not args.force:
            response = input("Continue anyway? [y/N]: ")
            print()

            if response.lower() not in ['y', 'yes']:
                print("Cancelled")
                print()
                return 0

    # Activate stack
    print(f"Activating stack '{stack_name}'...")
    print()

    try:
        env_vars = stackutils.activate_stack(stack_name)

        # Show what was configured
        print("Environment configured:")
        for var, value in sorted(env_vars.items()):
            if value is None:
                print(f"  ✓ Unset {var}")
            else:
                display_value = value if len(str(value)) < 60 else str(value)[:57] + '...'
                print(f"  ✓ Set {var}={display_value}")

        print()
        print(f"✓ Activated stack '{stack_name}'")
        print()
        print("Stack configuration:")
        print(f"  Metal: {stack_config['metal']}")
        print(f"  Model: {stack_config['model']}")
        print(f"  Hardware: {stack_config.get('hardware', 'auto-detect')}")
        print()
        print("To start a server with this stack:")
        print(f"  tt serve start")
        print()

        return 0

    except Exception as e:
        print(f"❌ Error activating stack: {e}")
        print()
        return 1


def info(args):
    """
    Show detailed information about a stack.
    """
    print()

    stack_name = args.name
    stack_config = stackutils.get_stack(stack_name)

    if not stack_config:
        print(f"❌ Stack '{stack_name}' not found")
        print()
        return 1

    # JSON output
    if args.json:
        validation = stackutils.validate_stack(stack_config)
        output = {
            'name': stack_name,
            'config': stack_config,
            'validation': validation,
            'active': stack_name == stackutils.get_active_stack(),
        }
        print(json.dumps(output, indent=2))
        print()
        return 0

    # Human-readable output
    is_active = stack_name == stackutils.get_active_stack()
    active_indicator = " (active)" if is_active else ""

    print(f"Stack: {stack_name}{active_indicator}")
    print()

    if 'description' in stack_config:
        print(f"Description: {stack_config['description']}")
        print()

    print("Configuration:")
    print(f"  Metal Version: {stack_config.get('metal', 'not specified')}")
    print(f"  Model: {stack_config.get('model', 'not specified')}")
    print(f"  Hardware: {stack_config.get('hardware', 'auto-detect')}")
    print()

    # Server config
    if 'config' in stack_config and stack_config['config']:
        print("Server Settings:")
        for key, value in stack_config['config'].items():
            print(f"  {key}: {value}")
        print()

    # Environment variables
    if 'env_vars' in stack_config and stack_config['env_vars']:
        print("Environment Variables:")
        for var, value in stack_config['env_vars'].items():
            print(f"  {var}={value}")
        print()

    # Override TT config
    if 'override_tt_config' in stack_config and stack_config['override_tt_config']:
        print("TT-Metal Override Config:")
        for key, value in stack_config['override_tt_config'].items():
            print(f"  {key}: {value}")
        print()

    # Validation
    validation = stackutils.validate_stack(stack_config)

    print("Validation:")
    if validation['valid'] and not validation['warnings']:
        print("  ✓ Stack is ready to use")
    elif validation['valid']:
        print(f"  ⚠ {len(validation['warnings'])} warning(s)")
    else:
        print(f"  ❌ {len(validation['issues'])} issue(s)")

    if validation['issues']:
        print()
        print("Issues:")
        for issue in validation['issues']:
            print(f"  • {issue}")

    if validation['warnings']:
        print()
        print("Warnings:")
        for warning in validation['warnings']:
            print(f"  • {warning}")

    print()

    return 0


def create(args):
    """
    Create a new stack interactively or from JSON.
    """
    print()

    stack_name = args.name

    # Check if stack already exists
    existing_stacks = stackutils.get_stacks()

    if stack_name in existing_stacks and not args.force:
        print(f"❌ Stack '{stack_name}' already exists")
        print("   Use --force to overwrite")
        print()
        return 1

    # Load from JSON file if provided
    if args.from_json:
        json_path = Path(args.from_json)

        if not json_path.exists():
            print(f"❌ JSON file not found: {json_path}")
            print()
            return 1

        try:
            with open(json_path, 'r') as f:
                stack_config = json.load(f)

            print(f"Loaded stack configuration from {json_path}")
            print()

        except Exception as e:
            print(f"❌ Failed to load JSON: {e}")
            print()
            return 1

    else:
        # Interactive creation
        print(f"Creating stack '{stack_name}'")
        print()

        stack_config = {}

        # Description
        description = input("Description (optional): ").strip()
        if description:
            stack_config['description'] = description

        # Metal version
        from tt.utils import metal
        installations = metal.get_metal_installations()

        if installations:
            print()
            print("Installed TT-Metal versions:")
            for version in installations.keys():
                is_active = version == metal.get_active_metal()
                marker = " (active)" if is_active else ""
                print(f"  • {version}{marker}")
            print()

            metal_version = input("TT-Metal version: ").strip()
        else:
            print("⚠ No TT-Metal installations found")
            metal_version = input("TT-Metal version (e.g., v0.66.0-rc7): ").strip()

        if not metal_version:
            print("❌ Metal version is required")
            print()
            return 1

        stack_config['metal'] = metal_version

        # Model
        print()
        model = input("Model (e.g., meta-llama/Llama-3.1-8B-Instruct): ").strip()

        if not model:
            print("❌ Model is required")
            print()
            return 1

        stack_config['model'] = model

        # Hardware
        print()
        from tt.utils import hardware
        hw = hardware.detect_hardware()

        if hw:
            print(f"Current hardware: {hw['primary_type']}")
            hardware_type = input(f"Hardware [{hw['primary_type']}]: ").strip() or hw['primary_type']
        else:
            hardware_type = input("Hardware (e.g., P150X4): ").strip()

        if hardware_type:
            stack_config['hardware'] = hardware_type

        # Config (simplified)
        print()
        print("Server configuration (press Enter to skip):")

        max_model_len = input("  max_model_len [128000]: ").strip()
        if max_model_len:
            if 'config' not in stack_config:
                stack_config['config'] = {}
            stack_config['config']['max_model_len'] = int(max_model_len)

        max_num_seqs = input("  max_num_seqs [32]: ").strip()
        if max_num_seqs:
            if 'config' not in stack_config:
                stack_config['config'] = {}
            stack_config['config']['max_num_seqs'] = int(max_num_seqs)

        port = input("  port [8000]: ").strip()
        if port:
            if 'config' not in stack_config:
                stack_config['config'] = {}
            stack_config['config']['port'] = int(port)

    # Validate stack
    validation = stackutils.validate_stack(stack_config)

    if not validation['valid']:
        print()
        print("❌ Stack validation failed:")
        for issue in validation['issues']:
            print(f"  • {issue}")
        print()
        return 1

    if validation['warnings']:
        print()
        print("⚠ Warnings:")
        for warning in validation['warnings']:
            print(f"  • {warning}")
        print()

    # Save stack
    stackutils.register_stack(stack_name, stack_config)

    print()
    print(f"✓ Stack '{stack_name}' created successfully")
    print()
    print("To use this stack:")
    print(f"  tt stack use {stack_name}")
    print()

    return 0


def remove(args):
    """
    Remove a stack.
    """
    print()

    stack_name = args.name
    stacks = stackutils.get_stacks()

    if stack_name not in stacks:
        print(f"❌ Stack '{stack_name}' not found")
        print()
        return 1

    # Check if it's a default stack
    if stack_name in stackutils.DEFAULT_STACKS:
        print(f"❌ Cannot remove default stack '{stack_name}'")
        print()
        return 1

    # Confirmation
    if not args.yes:
        print(f"Remove stack '{stack_name}'?")
        response = input("Continue? [y/N]: ")
        print()

        if response.lower() not in ['y', 'yes']:
            print("Cancelled")
            print()
            return 0

    # Remove stack
    stackutils.unregister_stack(stack_name)

    print(f"✓ Stack '{stack_name}' removed")
    print()

    return 0
