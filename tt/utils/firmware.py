"""
Firmware management utilities for Tenstorrent devices.

Handles firmware version parsing, downloading, and flashing.
Integrates with GitHub API for firmware releases and tt-flash for device operations.
"""

import json
import subprocess
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from . import hardware


# GitHub repository for firmware releases
FIRMWARE_REPO = "tenstorrent/tt-firmware"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

# Default cache directory for firmware bundles
DEFAULT_CACHE_DIR = Path.home() / ".tt" / "firmware"

# Hardware architecture compatibility mappings
# Maps device types to minimum recommended firmware versions
FIRMWARE_RECOMMENDATIONS = {
    # Blackhole devices (P-series) - recommend 19.4.x+
    'P100': {'min_version': '19.4.0', 'arch': 'blackhole'},
    'P100C': {'min_version': '19.4.0', 'arch': 'blackhole'},
    'P150': {'min_version': '19.4.0', 'arch': 'blackhole'},
    'P150C': {'min_version': '19.4.0', 'arch': 'blackhole'},
    'P300': {'min_version': '19.4.0', 'arch': 'blackhole'},
    'P300C': {'min_version': '19.4.0', 'arch': 'blackhole'},

    # Wormhole devices (N-series) - recommend 19.x+
    'N150': {'min_version': '19.0.0', 'arch': 'wormhole'},
    'N300': {'min_version': '19.0.0', 'arch': 'wormhole'},
    'T3K': {'min_version': '19.0.0', 'arch': 'wormhole'},
}


def parse_firmware_version(hex_version: int) -> str:
    """
    Convert hex firmware version to semantic version string.

    Firmware version format (32-bit hex):
    - Byte 4 (bits 24-31): major version
    - Byte 3 (bits 16-23): minor version
    - Byte 2 (bits 8-15): patch version
    - Byte 1 (bits 0-7): build version

    Args:
        hex_version: Hex firmware version (e.g., 0x13040200)

    Returns:
        Semantic version string (e.g., "19.4.2.0")

    Examples:
        >>> parse_firmware_version(0x13040200)
        '19.4.2.0'
        >>> parse_firmware_version(0x13040100)
        '19.4.1.0'
    """
    # Extract version components from hex value
    major = (hex_version >> 24) & 0xFF
    minor = (hex_version >> 16) & 0xFF
    patch = (hex_version >> 8) & 0xFF
    build = hex_version & 0xFF

    return f"{major}.{minor}.{patch}.{build}"


def format_firmware_version(version_str: str) -> str:
    """
    Format firmware version for display (strip trailing .0).

    Args:
        version_str: Version string (e.g., "19.4.2.0")

    Returns:
        Formatted version (e.g., "19.4.2")

    Examples:
        >>> format_firmware_version("19.4.2.0")
        '19.4.2'
        >>> format_firmware_version("19.4.1.5")
        '19.4.1.5'
    """
    parts = version_str.split('.')

    # Strip trailing .0
    while len(parts) > 1 and parts[-1] == '0':
        parts.pop()

    return '.'.join(parts)


def get_current_firmware() -> Optional[Dict]:
    """
    Get current firmware versions from all detected devices.

    Returns:
        Dict with firmware info per device, or None if no hardware detected
        Format: {
            'devices': [
                {
                    'index': 0,
                    'type': 'P300C',
                    'firmware_hex': '0x13040200',
                    'firmware_version': '19.4.2.0',
                    'firmware_display': '19.4.2',
                },
                ...
            ],
            'primary_version': '19.4.2',  # Most common version
        }
    """
    hw = hardware.detect_hardware()
    if not hw:
        return None

    devices = []
    version_counts = {}

    for dev in hw['devices']:
        firmware_raw = dev['firmware']

        # Try to parse hex firmware version
        firmware_version = None
        firmware_hex = None

        if isinstance(firmware_raw, int):
            # Already an integer
            firmware_hex = f"0x{firmware_raw:08x}"
            firmware_version = parse_firmware_version(firmware_raw)
        elif isinstance(firmware_raw, str):
            # String - might be hex string or decimal
            try:
                if firmware_raw.startswith('0x'):
                    # Hex string
                    firmware_int = int(firmware_raw, 16)
                    firmware_hex = firmware_raw
                    firmware_version = parse_firmware_version(firmware_int)
                else:
                    # Decimal string or already formatted
                    try:
                        firmware_int = int(firmware_raw)
                        firmware_hex = f"0x{firmware_int:08x}"
                        firmware_version = parse_firmware_version(firmware_int)
                    except ValueError:
                        # Already formatted version string
                        firmware_version = firmware_raw
                        firmware_hex = "unknown"
            except (ValueError, TypeError):
                firmware_version = firmware_raw
                firmware_hex = "unknown"

        firmware_display = format_firmware_version(firmware_version) if firmware_version else "unknown"

        devices.append({
            'index': dev['index'],
            'type': dev['type'],
            'firmware_hex': firmware_hex,
            'firmware_version': firmware_version,
            'firmware_display': firmware_display,
        })

        # Count versions for determining primary
        version_counts[firmware_display] = version_counts.get(firmware_display, 0) + 1

    # Primary version is the most common one
    primary_version = max(version_counts.items(), key=lambda x: x[1])[0] if version_counts else "unknown"

    return {
        'devices': devices,
        'primary_version': primary_version,
    }


def list_available_firmware() -> List[Dict]:
    """
    Fetch available firmware releases from GitHub API.

    Returns:
        List of firmware releases, sorted by version (newest first)
        Format: [
            {
                'tag': 'v19.4.2',
                'version': '19.4.2',
                'date': '2026-01-05',
                'url': 'https://github.com/tenstorrent/tt-firmware/releases/download/...',
                'name': 'fw_pack-80.140.41.0.fwbundle',
            },
            ...
        ]

    Raises:
        urllib.error.URLError: If network request fails
        json.JSONDecodeError: If API response is invalid
    """
    api_url = f"{GITHUB_API_BASE}/repos/{FIRMWARE_REPO}/releases"

    try:
        with urllib.request.urlopen(api_url, timeout=10) as response:
            releases = json.loads(response.read())
    except urllib.error.URLError as e:
        raise urllib.error.URLError(f"Failed to fetch firmware releases from GitHub: {e.reason}")

    firmware_list = []

    for release in releases:
        tag = release.get('tag_name', '')

        # Skip if no tag or not a version tag
        if not tag or not tag.startswith('v'):
            continue

        # Extract version (strip 'v' prefix)
        version = tag[1:]

        # Get release date (format: 2026-01-05T12:34:56Z -> 2026-01-05)
        date = release.get('published_at', '')[:10]

        # Find firmware bundle asset
        bundle_name = None
        bundle_url = None

        for asset in release.get('assets', []):
            asset_name = asset.get('name', '')
            if asset_name.endswith('.fwbundle'):
                bundle_name = asset_name
                bundle_url = asset.get('browser_download_url')
                break

        # Skip if no firmware bundle found
        if not bundle_url:
            continue

        firmware_list.append({
            'tag': tag,
            'version': version,
            'date': date,
            'url': bundle_url,
            'name': bundle_name,
        })

    # Sort by version (newest first) - simple string comparison works for semantic versions
    firmware_list.sort(key=lambda x: [int(p) for p in x['version'].split('.')], reverse=True)

    return firmware_list


def get_latest_firmware() -> Optional[Dict]:
    """
    Get latest firmware release from GitHub API.

    Returns:
        Latest firmware release dict, or None if not found
        Format: {'tag': 'v19.4.2', 'version': '19.4.2', 'date': '2026-01-05', 'url': '...', 'name': '...'}

    Raises:
        urllib.error.URLError: If network request fails
    """
    firmware_list = list_available_firmware()
    return firmware_list[0] if firmware_list else None


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semantic version strings.

    Args:
        v1: First version string (e.g., "19.4.2")
        v2: Second version string (e.g., "19.4.1")

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2

    Examples:
        >>> compare_versions("19.4.2", "19.4.1")
        1
        >>> compare_versions("19.4.1", "19.4.2")
        -1
        >>> compare_versions("19.4.2", "19.4.2")
        0
    """
    # Normalize versions (strip 'v' prefix if present)
    v1 = v1.lstrip('v')
    v2 = v2.lstrip('v')

    # Split into parts and convert to integers
    parts1 = [int(p) for p in v1.split('.')]
    parts2 = [int(p) for p in v2.split('.')]

    # Pad shorter version with zeros
    max_len = max(len(parts1), len(parts2))
    parts1.extend([0] * (max_len - len(parts1)))
    parts2.extend([0] * (max_len - len(parts2)))

    # Compare part by part
    for p1, p2 in zip(parts1, parts2):
        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1

    return 0


def get_firmware_compatibility(version: str, hardware_type: str) -> Dict:
    """
    Determine firmware compatibility for specific hardware type.

    This is advisory only - provides recommendations but never blocks operations.

    Args:
        version: Firmware version (e.g., "19.4.2")
        hardware_type: Hardware type (e.g., "P300C", "N150")

    Returns:
        Dict with compatibility info:
        {
            'compatible': bool,           # Is this version recommended?
            'recommendation': str,         # Recommended version range
            'warning': str | None,        # Warning message if not recommended
            'arch': str,                  # Architecture name
        }

    Examples:
        >>> get_firmware_compatibility("19.4.2", "P300C")
        {'compatible': True, 'recommendation': '19.4.0+', 'warning': None, 'arch': 'blackhole'}
        >>> get_firmware_compatibility("19.2.0", "P300C")
        {'compatible': False, 'recommendation': '19.4.0+', 'warning': '...', 'arch': 'blackhole'}
    """
    # Get recommendation for this hardware type
    rec = FIRMWARE_RECOMMENDATIONS.get(hardware_type)

    if not rec:
        # Unknown hardware type - assume compatible
        return {
            'compatible': True,
            'recommendation': 'Any',
            'warning': None,
            'arch': 'unknown',
        }

    min_version = rec['min_version']
    arch = rec['arch']

    # Compare versions
    is_compatible = compare_versions(version, min_version) >= 0

    warning = None
    if not is_compatible:
        warning = (
            f"Firmware {version} may not be optimal for {hardware_type} ({arch.capitalize()}) hardware. "
            f"Consider using {min_version} or newer for best compatibility."
        )

    return {
        'compatible': is_compatible,
        'recommendation': f"{min_version}+",
        'warning': warning,
        'arch': arch,
    }


def get_recommended_firmware(hardware_type: str) -> List[Dict]:
    """
    Get firmware versions recommended for specific hardware.

    Filters available firmware by compatibility heuristics.

    Args:
        hardware_type: Hardware type (e.g., "P300C", "N150")

    Returns:
        List of recommended firmware releases (sorted newest first)

    Raises:
        urllib.error.URLError: If network request fails
    """
    all_firmware = list_available_firmware()

    # Filter by compatibility
    recommended = []
    for fw in all_firmware:
        compat = get_firmware_compatibility(fw['version'], hardware_type)
        if compat['compatible']:
            # Add compatibility info to firmware dict
            fw_with_compat = fw.copy()
            fw_with_compat['arch'] = compat['arch']
            fw_with_compat['recommendation'] = compat['recommendation']
            recommended.append(fw_with_compat)

    return recommended


def download_firmware(version: str, cache_dir: Optional[Path] = None, show_progress: bool = True) -> Path:
    """
    Download firmware bundle for specific version.

    Args:
        version: Firmware version (e.g., "19.4.2" or "v19.4.2")
        cache_dir: Directory to save firmware (default: ~/.tt/firmware/)
        show_progress: Whether to show download progress (default: True)

    Returns:
        Path to downloaded firmware bundle

    Raises:
        ValueError: If firmware version not found
        urllib.error.URLError: If download fails
        OSError: If file system operations fail

    Examples:
        >>> path = download_firmware("19.4.2")
        Downloading firmware 19.4.2...
        Download complete: ~/.tt/firmware/fw_pack-80.140.41.0.fwbundle
    """
    # Normalize version (strip 'v' prefix if present)
    version = version.lstrip('v')

    # Set default cache directory
    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR

    # Create cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Find firmware release
    firmware_list = list_available_firmware()
    firmware = None

    for fw in firmware_list:
        if fw['version'] == version:
            firmware = fw
            break

    if not firmware:
        raise ValueError(f"Firmware version {version} not found in available releases")

    # Check if already downloaded
    target_path = cache_dir / firmware['name']

    if target_path.exists():
        if show_progress:
            print(f"✓ Firmware {version} already downloaded: {target_path}")
        return target_path

    # Download firmware
    if show_progress:
        print(f"Downloading firmware {version}...")
        print(f"  URL: {firmware['url']}")
        print(f"  File: {firmware['name']}")

    try:
        # Download with progress indicator
        def show_download_progress(block_num, block_size, total_size):
            if not show_progress or total_size <= 0:
                return

            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100)

            # Show progress bar
            bar_length = 40
            filled = int(bar_length * downloaded / total_size)
            bar = '=' * filled + '-' * (bar_length - filled)

            # Format sizes
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)

            print(f"\r  Progress: [{bar}] {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)", end='', flush=True)

        # Download to temporary file first
        temp_path = target_path.with_suffix('.tmp')

        urllib.request.urlretrieve(
            firmware['url'],
            temp_path,
            reporthook=show_download_progress if show_progress else None,
        )

        if show_progress:
            print()  # New line after progress bar

        # Move to final location
        temp_path.rename(target_path)

        if show_progress:
            print(f"✓ Download complete: {target_path}")

        return target_path

    except Exception as e:
        # Clean up temporary file if it exists
        temp_path = target_path.with_suffix('.tmp')
        if temp_path.exists():
            temp_path.unlink()

        raise urllib.error.URLError(f"Failed to download firmware: {e}")


def has_tt_flash() -> bool:
    """
    Check if tt-flash tool is available in PATH.

    Returns:
        True if tt-flash is available, False otherwise
    """
    return shutil.which('tt-flash') is not None


def flash_firmware(
    bundle_path: Path,
    force: bool = False,
    no_reset: bool = False,
    allow_downgrades: bool = False,
) -> int:
    """
    Flash firmware to devices using tt-flash tool.

    Wrapper around `tt-flash flash` command.

    Args:
        bundle_path: Path to firmware bundle (.fwbundle file)
        force: Force update ROM (--force flag)
        no_reset: Do not reset devices after flash (--no-reset flag)
        allow_downgrades: Allow major version downgrades (--allow-major-downgrades flag)

    Returns:
        Exit code (0 = success, non-zero = error)

    Raises:
        FileNotFoundError: If tt-flash not found or bundle_path doesn't exist
    """
    if not has_tt_flash():
        raise FileNotFoundError(
            "tt-flash tool not found. "
            "Install with: pip install tt-flash"
        )

    if not bundle_path.exists():
        raise FileNotFoundError(f"Firmware bundle not found: {bundle_path}")

    # Build command
    cmd = ['tt-flash', 'flash', str(bundle_path)]

    if force:
        cmd.append('--force')

    if no_reset:
        cmd.append('--no-reset')

    if allow_downgrades:
        cmd.append('--allow-major-downgrades')

    # Execute command
    print(f"Flashing firmware: {bundle_path}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error flashing firmware: {e}")
        return 1


def verify_firmware(bundle_path: Optional[Path] = None) -> int:
    """
    Verify firmware on devices using tt-flash tool.

    Wrapper around `tt-flash verify` command.

    Args:
        bundle_path: Optional path to firmware bundle to verify against.
                    If not provided, verifies current firmware on device.

    Returns:
        Exit code (0 = success, non-zero = error)

    Raises:
        FileNotFoundError: If tt-flash not found or bundle_path doesn't exist
    """
    if not has_tt_flash():
        raise FileNotFoundError(
            "tt-flash tool not found. "
            "Install with: pip install tt-flash"
        )

    # Build command
    cmd = ['tt-flash', 'verify']

    if bundle_path:
        if not bundle_path.exists():
            raise FileNotFoundError(f"Firmware bundle not found: {bundle_path}")
        cmd.append(str(bundle_path))

    # Execute command
    print(f"Verifying firmware...")
    if bundle_path:
        print(f"Bundle: {bundle_path}")

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error verifying firmware: {e}")
        return 1
