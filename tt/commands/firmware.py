"""
Firmware management commands for Tenstorrent devices.

Provides commands for listing, downloading, and flashing firmware.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from tt.utils import hardware, firmware


def list_firmware(args):
    """
    List available firmware versions from GitHub.

    Supports filtering by hardware compatibility and JSON output.
    """
    print()

    # Check network connectivity by fetching firmware list
    try:
        firmware_list = firmware.list_available_firmware()
    except Exception as e:
        print(f"❌ Failed to fetch firmware list: {e}")
        print()
        print("Possible issues:")
        print("  • No network connection")
        print("  • GitHub API unavailable")
        print("  • API rate limit exceeded")
        print()
        return 1

    if not firmware_list:
        print("No firmware versions found")
        print()
        return 1

    # Get current firmware if possible
    current_fw = firmware.get_current_firmware()
    current_version = current_fw['primary_version'] if current_fw else None

    # Detect hardware for compatibility checks
    hw = hardware.detect_hardware()
    hardware_type = hw['primary_type'] if hw else None

    # Filter by compatibility if requested
    if args.recommended and hardware_type:
        firmware_list = [
            fw for fw in firmware_list
            if firmware.get_firmware_compatibility(fw['version'], hardware_type)['compatible']
        ]

    # JSON output
    if args.json:
        output = {
            'firmware_versions': firmware_list,
            'current_version': current_version,
            'hardware_type': hardware_type,
            'filter': 'recommended' if args.recommended else 'all',
        }
        print(json.dumps(output, indent=2))
        print()
        return 0

    # Human-readable output
    if hardware_type:
        print(f"Available Firmware Versions (for {hardware_type}):")
    else:
        print("Available Firmware Versions:")
    print()

    for fw in firmware_list:
        version = fw['version']
        date = fw['date']

        # Build status indicators
        indicators = []

        # Check if current version
        if current_version and version == current_version:
            indicators.append('current')

        # Check if recommended
        if hardware_type:
            compat = firmware.get_firmware_compatibility(version, hardware_type)
            if compat['compatible']:
                indicators.append('recommended')

        # Format indicator string
        if indicators:
            indicator = f"({', '.join(indicators)})"
        else:
            indicator = ""

        # Choose prefix symbol
        if 'current' in indicators and 'recommended' in indicators:
            prefix = "✓"  # Current and recommended
        elif 'recommended' in indicators:
            prefix = "⭐"  # Recommended
        elif 'current' in indicators:
            prefix = "✓"  # Current but not recommended
        else:
            prefix = "•"  # Available

        # Format output
        version_str = f"{prefix} {version:15s}"
        if indicator:
            version_str += f" {indicator:30s}"

        print(f"{version_str} - Released {date}")

    print()

    # Show filter hint
    if args.recommended:
        print("Showing only recommended versions for your hardware.")
        print("Use 'tt firmware list' to see all versions.")
    else:
        if hardware_type:
            print("Showing all versions. Use --recommended to show only compatible versions.")

    print()
    return 0


def current_firmware(args):
    """
    Show current firmware version on all devices.

    Supports JSON output.
    """
    print()

    # Get current firmware
    current_fw = firmware.get_current_firmware()

    if not current_fw:
        print("❌ No hardware detected")
        print()
        print("Possible issues:")
        print("  • tt-smi not installed")
        print("  • No Tenstorrent devices present")
        print("  • Device drivers not loaded")
        print()
        return 1

    # JSON output
    if args.json:
        print(json.dumps(current_fw, indent=2))
        print()
        return 0

    # Human-readable output
    print("Current Firmware:")
    print()

    for dev in current_fw['devices']:
        device_str = f"Device {dev['index']}"
        version_str = f"{dev['firmware_display']}"
        hex_str = f"({dev['firmware_hex']})"

        print(f"{device_str:12s}: {version_str:15s} {hex_str}")

    print()

    # Check if firmware is recommended for hardware
    hw = hardware.detect_hardware()
    if hw and hw['primary_type']:
        hardware_type = hw['primary_type']
        primary_version = current_fw['primary_version']

        compat = firmware.get_firmware_compatibility(primary_version, hardware_type)

        if compat['compatible']:
            print(f"✓ Firmware is recommended for {hardware_type} hardware")
        else:
            print(f"⚠ Warning: {compat['warning']}")
            print(f"  Recommended: {compat['recommendation']}")

        print()

    return 0


def download(args):
    """
    Download firmware bundle for specific version.

    Downloads to cache directory (default: ~/.tt/firmware/).
    """
    print()

    version = args.version
    output_path = Path(args.output) if args.output else None

    # Determine cache directory
    if output_path:
        # User specified output path
        if output_path.is_dir():
            cache_dir = output_path
        else:
            # Treat as file path - use parent directory
            cache_dir = output_path.parent
            # We'll rename after download
    else:
        cache_dir = firmware.DEFAULT_CACHE_DIR

    try:
        # Download firmware
        downloaded_path = firmware.download_firmware(
            version,
            cache_dir=cache_dir,
            show_progress=True,
        )

        # If user specified a file path (not directory), rename
        if output_path and not output_path.is_dir():
            downloaded_path.rename(output_path)
            downloaded_path = output_path

        print()
        print(f"✓ Firmware downloaded: {downloaded_path}")
        print()
        return 0

    except ValueError as e:
        print(f"❌ {e}")
        print()
        print("To see available versions:")
        print("  tt firmware list")
        print()
        return 1

    except Exception as e:
        print(f"❌ Download failed: {e}")
        print()
        print("Possible issues:")
        print("  • No network connection")
        print("  • GitHub unavailable")
        print("  • Insufficient disk space")
        print()
        return 1


def flash(args):
    """
    Flash firmware to devices.

    Supports both version strings and file paths.
    Shows compatibility warnings but never blocks operations.
    """
    print()

    version_or_path = args.version_or_path

    # Determine if this is a version or a path
    bundle_path = None

    # Check if it's a file path
    path_obj = Path(version_or_path)
    if path_obj.exists() and path_obj.is_file():
        bundle_path = path_obj
        version = None
    else:
        # Treat as version string - need to download
        version = version_or_path.lstrip('v')
        bundle_path = None

    # If version specified, check if cached or download
    if version:
        cache_dir = firmware.DEFAULT_CACHE_DIR

        # Try to find in cache
        try:
            firmware_list = firmware.list_available_firmware()
            fw_info = None

            for fw in firmware_list:
                if fw['version'] == version:
                    fw_info = fw
                    break

            if not fw_info:
                print(f"❌ Firmware version {version} not found")
                print()
                print("To see available versions:")
                print("  tt firmware list")
                print()
                return 1

            # Check if already downloaded
            cached_path = cache_dir / fw_info['name']

            if cached_path.exists():
                print(f"Using cached firmware: {cached_path}")
                bundle_path = cached_path
            else:
                # Download firmware
                print(f"Firmware {version} not cached, downloading...")
                bundle_path = firmware.download_firmware(
                    version,
                    cache_dir=cache_dir,
                    show_progress=True,
                )

        except Exception as e:
            print(f"❌ Failed to prepare firmware: {e}")
            print()
            return 1

    # At this point, bundle_path should be set
    if not bundle_path or not bundle_path.exists():
        print(f"❌ Firmware bundle not found: {bundle_path}")
        print()
        return 1

    print()

    # Detect hardware and check compatibility
    hw = hardware.detect_hardware()
    if hw and hw['primary_type']:
        hardware_type = hw['primary_type']
        print(f"Hardware detected: {hardware_type}")

        # Get current firmware
        current_fw = firmware.get_current_firmware()
        current_version = current_fw['primary_version'] if current_fw else "unknown"

        # Determine target version (if we have it)
        target_version = version if version else "unknown"

        # Check compatibility if we know the version
        if version:
            compat = firmware.get_firmware_compatibility(version, hardware_type)

            if not compat['compatible']:
                print(f"Target firmware: {version}")
                print()
                print(f"⚠ Warning: {compat['warning']}")
                print(f"💡 Recommendation: Consider using {compat['recommendation']} for optimal support.")
                print()
            else:
                print(f"Target firmware: {version}")
                print()

            # Check for downgrade
            if current_version != "unknown" and version != current_version:
                comparison = firmware.compare_versions(version, current_version)
                if comparison < 0:
                    print(f"⚠ Warning: This is a downgrade from {current_version} to {version}")
                    print()

        else:
            print(f"Target firmware: {bundle_path.name}")
            print()

        # Show current vs target
        if current_version != "unknown":
            print(f"Current firmware: {current_version}")
            if version:
                print(f"Target firmware:  {version}")
                if current_version == version:
                    print()
                    print("ℹ Firmware version is already installed (will re-flash)")
            print()

    else:
        print("⚠ Warning: Could not detect hardware")
        print()

    # Confirmation prompt (unless --yes flag)
    if not args.yes:
        print("This will flash firmware to all devices.")
        response = input("Continue? [y/N]: ")
        print()

        if response.lower() not in ['y', 'yes']:
            print("Cancelled")
            print()
            return 0

    # Check if tt-flash is available
    if not firmware.has_tt_flash():
        print("❌ tt-flash tool not found")
        print()
        print("Install with:")
        print("  pip install tt-flash")
        print()
        return 1

    # Flash firmware
    try:
        exit_code = firmware.flash_firmware(
            bundle_path,
            force=args.force,
            no_reset=args.no_reset,
            allow_downgrades=args.allow_downgrades,
        )

        print()

        if exit_code == 0:
            print("✓ Firmware flashed successfully")
            print()

            # Show new firmware version
            if not args.no_reset:
                print("Verifying firmware...")
                current_fw = firmware.get_current_firmware()
                if current_fw:
                    new_version = current_fw['primary_version']
                    print(f"✓ Current firmware: {new_version}")
                print()

            return 0
        else:
            print("❌ Firmware flash failed")
            print()
            print("Troubleshooting:")
            print("  • Check device connections")
            print("  • Try with --force flag")
            print("  • Check tt-flash documentation")
            print()
            return exit_code

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        return 1


def verify(args):
    """
    Verify firmware on devices.

    Optionally verify against specific bundle.
    """
    print()

    bundle_path = None

    # If version or path specified, resolve it
    if args.version_or_path:
        version_or_path = args.version_or_path

        # Check if it's a file path
        path_obj = Path(version_or_path)
        if path_obj.exists() and path_obj.is_file():
            bundle_path = path_obj
        else:
            # Treat as version - find in cache
            version = version_or_path.lstrip('v')
            cache_dir = firmware.DEFAULT_CACHE_DIR

            try:
                firmware_list = firmware.list_available_firmware()
                fw_info = None

                for fw in firmware_list:
                    if fw['version'] == version:
                        fw_info = fw
                        break

                if not fw_info:
                    print(f"❌ Firmware version {version} not found")
                    print()
                    return 1

                # Check if cached
                cached_path = cache_dir / fw_info['name']

                if not cached_path.exists():
                    print(f"❌ Firmware {version} not cached")
                    print()
                    print("Download first:")
                    print(f"  tt firmware download {version}")
                    print()
                    return 1

                bundle_path = cached_path

            except Exception as e:
                print(f"❌ Failed to locate firmware: {e}")
                print()
                return 1

    # Check if tt-flash is available
    if not firmware.has_tt_flash():
        print("❌ tt-flash tool not found")
        print()
        print("Install with:")
        print("  pip install tt-flash")
        print()
        return 1

    # Verify firmware
    try:
        exit_code = firmware.verify_firmware(bundle_path)

        print()

        if exit_code == 0:
            print("✓ Firmware verification passed")
            print()
            return 0
        else:
            print("❌ Firmware verification failed")
            print()
            return exit_code

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        return 1


def latest(args):
    """
    Show latest firmware version.

    Optionally download or flash latest firmware.
    """
    print()

    # Get latest firmware
    try:
        if args.recommended:
            # Get latest recommended for detected hardware
            hw = hardware.detect_hardware()
            if not hw or not hw['primary_type']:
                print("❌ Could not detect hardware")
                print()
                print("Use 'tt firmware latest' without --recommended to see absolute latest.")
                print()
                return 1

            hardware_type = hw['primary_type']
            recommended = firmware.get_recommended_firmware(hardware_type)

            if not recommended:
                print(f"❌ No recommended firmware found for {hardware_type}")
                print()
                return 1

            latest_fw = recommended[0]  # First is newest
            print(f"Hardware: {hardware_type}")
            print()
            print(f"Latest Recommended Firmware: {latest_fw['version']} (released {latest_fw['date']})")
        else:
            # Get absolute latest
            latest_fw = firmware.get_latest_firmware()

            if not latest_fw:
                print("❌ No firmware versions found")
                print()
                return 1

            print(f"Latest Firmware: {latest_fw['version']} (released {latest_fw['date']})")

    except Exception as e:
        print(f"❌ Failed to fetch firmware info: {e}")
        print()
        return 1

    # Get current firmware
    current_fw = firmware.get_current_firmware()
    current_version = current_fw['primary_version'] if current_fw else None

    if current_version:
        print(f"Current Firmware: {current_version}")
        print()

        # Compare versions
        comparison = firmware.compare_versions(latest_fw['version'], current_version)

        if comparison > 0:
            print(f"⬆ Update available: {current_version} → {latest_fw['version']}")
        elif comparison == 0:
            print("✓ Firmware is up to date")
        else:
            print(f"ℹ Current version ({current_version}) is newer than latest release")

        # Check if recommended for hardware
        hw = hardware.detect_hardware()
        if hw and hw['primary_type']:
            compat = firmware.get_firmware_compatibility(current_version, hw['primary_type'])
            if compat['compatible']:
                print("✓ Current firmware is recommended for your hardware")
            else:
                print(f"⚠ Current firmware may not be optimal for {hw['primary_type']}")

        print()

    # Download if requested
    if args.download or args.flash:
        print(f"Downloading firmware {latest_fw['version']}...")
        try:
            downloaded_path = firmware.download_firmware(
                latest_fw['version'],
                show_progress=True,
            )
            print()
            print(f"✓ Downloaded: {downloaded_path}")
            print()

            # Flash if requested
            if args.flash:
                # Prepare args for flash command
                import argparse
                flash_args = argparse.Namespace(
                    version_or_path=str(downloaded_path),
                    force=False,
                    no_reset=False,
                    allow_downgrades=False,
                    yes=args.yes,
                )

                return flash(flash_args)

        except Exception as e:
            print(f"❌ Failed to download: {e}")
            print()
            return 1

    return 0
