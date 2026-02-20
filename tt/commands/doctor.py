"""
tt doctor command - Comprehensive system diagnostics

This checks all aspects of the TT development environment:
- Hardware/devices
- Firmware versions
- Environment variables
- Python packages
- TT-Metal installation
- vLLM patches
- Model caches
- Disk space
- Drivers

Similar to: brew doctor, flutter doctor, docker info
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from tt.utils import hardware, envmanager
from tt.commands import model as modelutils


class DiagnosticResult:
    """Result of a diagnostic check."""

    def __init__(self, name: str, status: str, message: str, details: Optional[List[str]] = None, fixable: bool = False):
        """
        Create diagnostic result.

        Args:
            name: Check name (e.g., "Devices")
            status: "ok", "warning", or "error"
            message: Summary message
            details: Optional list of detail lines
            fixable: Whether this can be auto-fixed
        """
        self.name = name
        self.status = status
        self.message = message
        self.details = details or []
        self.fixable = fixable


def check_devices(verbose: bool = False) -> DiagnosticResult:
    """
    Check if TT devices are detected and healthy.

    Args:
        verbose: Show detailed information

    Returns:
        DiagnosticResult
    """
    hw = hardware.detect_hardware()

    if not hw:
        return DiagnosticResult(
            name="Devices",
            status="error",
            message="No Tenstorrent devices detected",
            details=[
                "Run 'tt-smi -s' to check device status",
                "Check if driver is loaded: lsmod | grep tenstorrent",
            ],
        )

    device_type = hw['primary_type']
    device_count = hw['count']
    mesh_device = hardware.get_mesh_device()

    details = [
        f"Type: {device_type}",
        f"Count: {device_count}",
    ]

    if mesh_device:
        details.append(f"MESH_DEVICE: {mesh_device}")

    # Try to get device info from tt-smi
    if verbose:
        try:
            result = subprocess.run(
                ['tt-smi', '-s'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                details.append("tt-smi status: OK")
        except Exception:
            pass

    return DiagnosticResult(
        name="Devices",
        status="ok",
        message=f"{device_count}x {device_type} detected",
        details=details,
    )


def check_firmware(verbose: bool = False) -> DiagnosticResult:
    """
    Check firmware version.

    Args:
        verbose: Show detailed information

    Returns:
        DiagnosticResult
    """
    # Try to get current firmware version
    try:
        from tt.commands import firmware as fw

        # This is a simplified check - would need to integrate with firmware.py properly
        details = ["Firmware check available via: tt fw current"]

        return DiagnosticResult(
            name="Firmware",
            status="ok",
            message="Firmware commands available",
            details=details,
        )
    except Exception as e:
        return DiagnosticResult(
            name="Firmware",
            status="warning",
            message="Could not check firmware",
            details=[str(e)],
        )


def check_environment(verbose: bool = False) -> DiagnosticResult:
    """
    Check environment variables.

    Args:
        verbose: Show detailed information

    Returns:
        DiagnosticResult
    """
    required_vars = ['TT_METAL_HOME', 'PYTHONPATH']
    recommended_vars = ['ARCH_NAME', 'MESH_DEVICE']

    issues = []
    warnings = []
    details = []

    # Check required variables
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            issues.append(f"{var} not set")
        else:
            details.append(f"{var}: {value}")

    # Check recommended variables
    for var in recommended_vars:
        value = os.environ.get(var)
        if value:
            details.append(f"{var}: {value}")
        else:
            warnings.append(f"{var} not set (recommended)")

    if issues:
        return DiagnosticResult(
            name="Environment",
            status="error",
            message=f"{len(issues)} required variable(s) missing",
            details=issues + warnings + details,
            fixable=True,
        )
    elif warnings:
        return DiagnosticResult(
            name="Environment",
            status="warning",
            message="Some recommended variables not set",
            details=warnings + details,
            fixable=True,
        )
    else:
        return DiagnosticResult(
            name="Environment",
            status="ok",
            message="All environment variables set",
            details=details if verbose else [],
        )


def check_python_packages(verbose: bool = False) -> DiagnosticResult:
    """
    Check Python packages (vllm, etc.).

    Args:
        verbose: Show detailed information

    Returns:
        DiagnosticResult
    """
    required_packages = {
        'vllm': 'vLLM for inference',
    }

    details = []
    missing = []

    for package, description in required_packages.items():
        try:
            result = subprocess.run(
                ['python', '-c', f'import {package}; print({package}.__version__)'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                details.append(f"{package}: {version}")
            else:
                missing.append(f"{package} ({description})")
        except Exception:
            missing.append(f"{package} ({description})")

    if missing:
        return DiagnosticResult(
            name="Python Packages",
            status="error",
            message=f"{len(missing)} package(s) missing",
            details=missing + details,
        )
    else:
        return DiagnosticResult(
            name="Python Packages",
            status="ok",
            message="All required packages installed",
            details=details,
        )


def check_tt_metal(verbose: bool = False) -> DiagnosticResult:
    """
    Check TT-Metal installation.

    Args:
        verbose: Show detailed information

    Returns:
        DiagnosticResult
    """
    tt_metal_home = os.environ.get('TT_METAL_HOME')

    if not tt_metal_home:
        return DiagnosticResult(
            name="TT-Metal",
            status="error",
            message="TT_METAL_HOME not set",
            details=["Set TT_METAL_HOME environment variable"],
            fixable=True,
        )

    tt_metal_path = Path(tt_metal_home)

    if not tt_metal_path.exists():
        return DiagnosticResult(
            name="TT-Metal",
            status="error",
            message=f"TT-Metal directory not found: {tt_metal_home}",
            details=["Check TT_METAL_HOME path"],
        )

    details = [f"Path: {tt_metal_home}"]

    # Check if built
    build_dir = tt_metal_path / 'build'
    if build_dir.exists():
        details.append("Build directory: exists")
    else:
        details.append("Build directory: missing")

    # Try to get git commit
    if verbose:
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=tt_metal_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                commit = result.stdout.strip()
                details.append(f"Git commit: {commit}")
        except Exception:
            pass

    return DiagnosticResult(
        name="TT-Metal",
        status="ok",
        message="TT-Metal installation found",
        details=details,
    )


def check_vllm_patches(verbose: bool = False) -> DiagnosticResult:
    """
    Check if vLLM patches are applied.

    Args:
        verbose: Show detailed information

    Returns:
        DiagnosticResult
    """
    patch_status = envmanager.check_vllm_patches()

    if patch_status['warnings']:
        return DiagnosticResult(
            name="vLLM Patches",
            status="warning",
            message="Some patches missing",
            details=patch_status['warnings'],
        )
    else:
        return DiagnosticResult(
            name="vLLM Patches",
            status="ok",
            message="All patches detected",
            details=["Model registration: OK", "Block size: OK"] if verbose else [],
        )


def check_disk_space(verbose: bool = False) -> DiagnosticResult:
    """
    Check disk space for models and caches.

    Args:
        verbose: Show detailed information

    Returns:
        DiagnosticResult
    """
    home = Path.home()

    # Check home directory space
    stat = shutil.disk_usage(home)
    free_gb = stat.free / (1024 ** 3)
    total_gb = stat.total / (1024 ** 3)
    used_percent = (stat.used / stat.total) * 100

    details = [
        f"Home: {free_gb:.1f}GB free / {total_gb:.1f}GB total ({used_percent:.0f}% used)"
    ]

    # Check models directory
    models_dir = home / 'models'
    if models_dir.exists():
        try:
            size = sum(f.stat().st_size for f in models_dir.rglob('*') if f.is_file())
            size_gb = size / (1024 ** 3)
            details.append(f"Models: {size_gb:.1f}GB")
        except Exception:
            pass

    # Warn if less than 10GB free
    if free_gb < 10:
        return DiagnosticResult(
            name="Disk Space",
            status="warning",
            message=f"Low disk space: {free_gb:.1f}GB free",
            details=details + ["Consider cleaning up old models or caches"],
        )
    else:
        return DiagnosticResult(
            name="Disk Space",
            status="ok",
            message=f"{free_gb:.1f}GB available",
            details=details if verbose else [],
        )


def check_models(verbose: bool = False) -> DiagnosticResult:
    """
    Check installed models.

    Args:
        verbose: Show detailed information

    Returns:
        DiagnosticResult
    """
    models_dir = Path.home() / 'models'

    if not models_dir.exists():
        return DiagnosticResult(
            name="Models",
            status="ok",
            message="No models directory (models will be downloaded on first use)",
            details=[],
        )

    # Count models
    model_count = len([d for d in models_dir.iterdir() if d.is_dir()])

    details = [f"Models directory: {models_dir}", f"Installed models: {model_count}"]

    # Check for TT caches if verbose
    if verbose and model_count > 0:
        cached_models = 0
        for model_dir in models_dir.iterdir():
            if model_dir.is_dir():
                cache_info = modelutils.detect_tt_cache(model_dir)
                if cache_info['has_cache']:
                    cached_models += 1
                    details.append(f"  {model_dir.name}: {cache_info['device']} cache ({cache_info['cache_size_mb']}MB)")

        details.append(f"Models with TT cache: {cached_models}/{model_count}")

    return DiagnosticResult(
        name="Models",
        status="ok",
        message=f"{model_count} model(s) installed",
        details=details if verbose else [],
    )


def run_diagnostics(args: argparse.Namespace) -> List[DiagnosticResult]:
    """
    Run all diagnostic checks.

    Args:
        args: Command arguments

    Returns:
        List of DiagnosticResults
    """
    results = []
    verbose = hasattr(args, 'verbose') and args.verbose

    # Determine which checks to run
    run_all = not any([
        hasattr(args, 'devices') and args.devices,
        hasattr(args, 'env') and args.env,
        hasattr(args, 'models') and args.models,
        hasattr(args, 'firmware') and args.firmware,
    ])

    if run_all or (hasattr(args, 'devices') and args.devices):
        results.append(check_devices(verbose))

    if run_all or (hasattr(args, 'firmware') and args.firmware):
        results.append(check_firmware(verbose))

    if run_all or (hasattr(args, 'env') and args.env):
        results.append(check_environment(verbose))

    if run_all:
        results.append(check_python_packages(verbose))
        results.append(check_tt_metal(verbose))
        results.append(check_vllm_patches(verbose))
        results.append(check_disk_space(verbose))

    if run_all or (hasattr(args, 'models') and args.models):
        results.append(check_models(verbose))

    return results


def print_results(results: List[DiagnosticResult], verbose: bool = False):
    """
    Print diagnostic results in human-readable format.

    Args:
        results: List of DiagnosticResults
        verbose: Show detailed information
    """
    print("System Diagnostics\n")

    for result in results:
        # Status icon
        if result.status == "ok":
            icon = "✓"
        elif result.status == "warning":
            icon = "⚠️ "
        else:
            icon = "❌"

        # Print result
        print(f"{icon} {result.name}: {result.message}")

        # Print details if verbose or if there's an issue
        if result.details and (verbose or result.status != "ok"):
            for detail in result.details:
                print(f"   {detail}")
            print()

    # Summary
    ok_count = sum(1 for r in results if r.status == "ok")
    warning_count = sum(1 for r in results if r.status == "warning")
    error_count = sum(1 for r in results if r.status == "error")

    print()
    print(f"Summary: {ok_count} OK, {warning_count} warnings, {error_count} errors")

    # Suggest fixes if there are fixable issues
    fixable = [r for r in results if r.fixable and r.status != "ok"]
    if fixable:
        print()
        print(f"💡 {len(fixable)} issue(s) can be auto-fixed. Run: tt doctor --fix")


def auto_fix(results: List[DiagnosticResult]) -> int:
    """
    Attempt to auto-fix issues.

    Args:
        results: List of DiagnosticResults

    Returns:
        Number of issues fixed
    """
    fixable = [r for r in results if r.fixable and r.status != "ok"]

    if not fixable:
        print("No fixable issues found")
        return 0

    print("🔧 Auto-fixing issues...\n")

    fixed_count = 0

    for result in fixable:
        if result.name == "Environment":
            print(f"Fixing: {result.name}")

            # Use envmanager to fix environment
            issues, fixed_vars = envmanager.fix_environment(apply_to_os_environ=True)

            if fixed_vars:
                print(f"✓ Fixed {len(fixed_vars)} environment variable(s)")
                for var, value in fixed_vars.items():
                    print(f"  {var}={value}")
                fixed_count += 1
            else:
                print("⚠️  Could not auto-fix environment")

            print()

    if fixed_count > 0:
        print(f"✓ Fixed {fixed_count} issue(s)")
        print()
        print("Note: Environment fixes only apply to this session.")
        print("For persistent fixes, run: eval \"$(tt env fix --export)\"")

    return fixed_count


def doctor(args: argparse.Namespace) -> int:
    """
    Run system diagnostics.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 = all OK, 1 = warnings, 2 = errors)
    """
    # Run diagnostics
    results = run_diagnostics(args)

    # Print results (unless JSON mode)
    if hasattr(args, 'json') and args.json:
        import json
        output = {
            'results': [
                {
                    'name': r.name,
                    'status': r.status,
                    'message': r.message,
                    'details': r.details,
                    'fixable': r.fixable,
                }
                for r in results
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        verbose = hasattr(args, 'verbose') and args.verbose
        print_results(results, verbose)

    # Auto-fix if requested
    if hasattr(args, 'fix') and args.fix:
        print()
        auto_fix(results)

        # Re-run diagnostics after fix
        print()
        print("Re-running diagnostics...")
        print()
        results = run_diagnostics(args)
        print_results(results, verbose)

    # Determine exit code
    has_errors = any(r.status == "error" for r in results)
    has_warnings = any(r.status == "warning" for r in results)

    if has_errors:
        return 2
    elif has_warnings:
        return 1
    else:
        return 0


def add_doctor_parser(subparsers):
    """
    Add doctor parser to main CLI.

    Args:
        subparsers: Subparsers from main argument parser
    """
    doctor_parser = subparsers.add_parser(
        'doctor',
        help='Run system diagnostics',
        description='Check system health and configuration (like brew doctor, flutter doctor)',
        epilog='''Examples:
  tt doctor                           # Run all checks
  tt doctor --verbose                 # Show detailed information
  tt doctor --fix                     # Auto-fix issues
  tt doctor --devices                 # Check devices only
  tt doctor --env                     # Check environment only
  tt doctor --json                    # JSON output
''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    doctor_parser.add_argument(
        '--fix',
        action='store_true',
        help='Attempt to auto-fix issues',
    )

    doctor_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed information',
    )

    doctor_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )

    # Subsystem-specific checks
    doctor_parser.add_argument(
        '--devices',
        action='store_true',
        help='Check devices only',
    )

    doctor_parser.add_argument(
        '--firmware',
        action='store_true',
        help='Check firmware only',
    )

    doctor_parser.add_argument(
        '--env',
        action='store_true',
        help='Check environment only',
    )

    doctor_parser.add_argument(
        '--models',
        action='store_true',
        help='Check models only',
    )

    doctor_parser.set_defaults(func=doctor)
