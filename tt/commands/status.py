"""
Status command - Show comprehensive system status
"""

import json
import os
from pathlib import Path

from tt.utils import hardware, envmanager


def status(args):
    """
    Show comprehensive system status.

    Args:
        args: Argparse namespace with json flag
    """
    # Gather status information
    status_data = {}

    # Hardware status
    hw = hardware.detect_hardware()
    if hw:
        status_data['hardware'] = {
            'detected': True,
            'type': hw['primary_type'],
            'count': hw['count'],
            'summary': hardware.format_hardware_summary(hw),
            'devices': hw['devices'],
        }
    else:
        status_data['hardware'] = {
            'detected': False,
            'message': 'No hardware detected (tt-smi not available)',
        }

    # Environment status
    env_check = envmanager.check_environment()
    status_data['environment'] = {
        'status': env_check['status'],
        'TT_METAL_HOME': os.environ.get('TT_METAL_HOME', 'not set'),
        'PYTHONPATH': os.environ.get('PYTHONPATH', 'not set'),
        'LD_LIBRARY_PATH': os.environ.get('LD_LIBRARY_PATH', 'not set')[:100] + '...'
            if os.environ.get('LD_LIBRARY_PATH') else 'not set',
        'has_uv': envmanager.has_uv(),
        'python_version': envmanager.get_current_python_version(),
        'issues': env_check['issues'],
        'warnings': env_check['warnings'],
    }

    # Model status (basic - just check if models directory exists)
    models_dir = Path.home() / 'models'
    if models_dir.exists():
        models = [d.name for d in models_dir.iterdir() if d.is_dir()]
        status_data['models'] = {
            'directory': str(models_dir),
            'count': len(models),
            'models': models[:5],  # Show first 5
        }
    else:
        status_data['models'] = {
            'directory': str(models_dir),
            'exists': False,
        }

    # Output format
    if args.json:
        print(json.dumps(status_data, indent=2))
    else:
        _print_status_human(status_data)


def _print_status_human(status_data: dict):
    """Print status in human-readable format."""
    # Header
    print()
    print("=" * 70)
    print("  Tenstorrent System Status")
    print("=" * 70)
    print()

    # Hardware
    print("🖥️  Hardware")
    hw = status_data['hardware']
    if hw['detected']:
        print(f"   ✓ {hw['summary']}")
        print(f"   ✓ {hw['count']} device(s) detected")
    else:
        print(f"   ⚠️  {hw['message']}")
    print()

    # Environment
    print("🔧 Environment")
    env = status_data['environment']

    # Status indicator
    if env['status'] == 'ok':
        print(f"   ✓ Status: OK")
    else:
        print(f"   ✗ Status: Issues found")

    # Key variables
    print(f"   • TT_METAL_HOME: {env['TT_METAL_HOME']}")
    print(f"   • Python: {env['python_version']}")
    print(f"   • uv available: {'Yes' if env['has_uv'] else 'No'}")

    # Issues and warnings
    if env['issues']:
        print()
        print("   Issues:")
        for issue in env['issues']:
            print(f"     ✗ {issue}")

    if env['warnings']:
        print()
        print("   Warnings:")
        for warning in env['warnings']:
            print(f"     ⚠️  {warning}")

    if env['issues'] or env['warnings']:
        print()
        print("   Run 'tt env fix' to auto-fix common issues")
        print("   Run 'tt env check' for detailed environment validation")

    print()

    # Models
    print("📦 Models")
    models = status_data['models']
    if 'exists' in models and not models['exists']:
        print(f"   ⚠️  Models directory not found: {models['directory']}")
        print(f"   Create it with: mkdir -p ~/models")
    elif models['count'] == 0:
        print(f"   ⚠️  No models installed")
        print(f"   Download models with: tt model get <name>")
    else:
        print(f"   ✓ {models['count']} model(s) installed")
        if models['models']:
            print(f"   • {', '.join(models['models'])}")
            if models['count'] > 5:
                print(f"   • ... and {models['count'] - 5} more")
    print()

    # Quick commands
    print("📌 Quick Commands")
    print("   tt serve <model>     # Start vLLM server")
    print("   tt env use <name>    # Switch environment")
    print("   tt device test       # Test devices")
    print("   tt model list        # List models")
    print()
    print("=" * 70)
    print()
