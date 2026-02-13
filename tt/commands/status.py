"""
Status command - Show comprehensive system status
"""

import json
import os
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

from tt.utils import hardware, envmanager, stack as stackutils
from tt.commands import serve


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

    # Stack status
    active_stack = stackutils.get_active_stack()
    if active_stack:
        stack_config = stackutils.get_stack(active_stack)
        status_data['stack'] = {
            'active': active_stack,
            'model': stack_config.get('model', 'unknown'),
            'hardware': stack_config.get('hardware', 'auto'),
            'metal': stack_config.get('metal', 'unknown'),
        }
    else:
        status_data['stack'] = {
            'active': None,
        }

    # Server status
    pid_dir = Path.home() / '.tt' / 'servers'
    servers = []
    if pid_dir.exists():
        for pid_file in pid_dir.glob('*.pid'):
            try:
                pid_data = json.loads(pid_file.read_text())
                pid = pid_data['pid']
                port = pid_data.get('port', 'unknown')
                device_id = pid_data.get('device_id')

                # Check if process is alive
                try:
                    os.kill(pid, 0)
                    running = True
                except (OSError, ProcessLookupError):
                    running = False
                    continue

                # Check API health
                ready = False
                if running and port != 'unknown':
                    try:
                        req = urllib.request.Request(
                            f'http://localhost:{port}/health',
                            headers={'User-Agent': 'tt-cli'}
                        )
                        with urllib.request.urlopen(req, timeout=2) as response:
                            ready = response.status == 200
                    except (urllib.error.URLError, TimeoutError, OSError):
                        ready = False

                servers.append({
                    'pid': pid,
                    'port': port,
                    'device_id': device_id,
                    'model': pid_data.get('model', 'unknown'),
                    'running': running,
                    'ready': ready,
                })
            except (json.JSONDecodeError, KeyError):
                continue

    status_data['servers'] = {
        'count': len(servers),
        'servers': servers,
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

    # Stack
    print("📚 Active Stack")
    stack = status_data.get('stack', {})
    if stack.get('active'):
        print(f"   ✓ {stack['active']}")
        print(f"   • Model: {stack['model']}")
        print(f"   • Hardware: {stack['hardware']}")
        print(f"   • Metal: {stack['metal']}")
    else:
        print(f"   • No active stack")
        print(f"   • Activate with: tt stack use <name>")
    print()

    # Servers
    print("🚀 Running Servers")
    servers_data = status_data.get('servers', {})
    servers = servers_data.get('servers', [])

    if not servers:
        print("   • No servers running")
        print("   • Start with: tt serve start <model>")
    else:
        # Count ready vs initializing
        ready_count = sum(1 for s in servers if s['ready'])
        init_count = len(servers) - ready_count

        print(f"   Total: {len(servers)} server(s)")
        print(f"   Ready: {ready_count} | Initializing: {init_count}")
        print()

        # Show each server
        for server in sorted(servers, key=lambda s: s.get('port', 0)):
            port = server['port']
            device_id = server.get('device_id')
            device_str = f"device {device_id}" if device_id is not None else "all devices"

            if server['ready']:
                status_icon = "✓"
                status_text = "READY"
            else:
                status_icon = "⏳"
                status_text = "INITIALIZING"

            print(f"   {status_icon} Port {port} ({device_str}): {status_text}")

    print()

    # Quick commands
    print("📌 Quick Commands")
    print("   tt serve start <model>     # Start vLLM server")
    print("   tt stack use <name>        # Switch stack")
    print("   tt serve status            # Detailed server info")
    print("   tt env use <name>          # Switch environment")
    print("   tt device test             # Test devices")
    print()
    print("=" * 70)
    print()
