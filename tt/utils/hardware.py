"""
Hardware detection and management utilities
Wraps tt-smi for device information
"""

import json
import subprocess
import shutil
from typing import Optional, Dict, List


def has_tt_smi() -> bool:
    """Check if tt-smi is available."""
    return shutil.which('tt-smi') is not None


def detect_hardware() -> Optional[Dict]:
    """
    Detect Tenstorrent hardware using tt-smi.

    Returns:
        Dict with device info, or None if no hardware detected
        Format: {
            'devices': [{'type': 'N150', 'index': 0, ...}, ...],
            'count': int,
            'primary_type': str,
        }
    """
    if not has_tt_smi():
        return None

    try:
        result = subprocess.run(
            ['tt-smi', '-s'],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        # Parse device information (tt-smi uses 'device_info' array)
        devices = []
        if 'device_info' in data:
            for idx, dev in enumerate(data['device_info']):
                board_info = dev.get('board_info', {})
                telemetry = dev.get('telemetry', {})
                firmwares = dev.get('firmwares', {})

                # Parse board type (e.g., "p300c" -> "P300C")
                board_type = board_info.get('board_type', 'unknown').upper()

                devices.append({
                    'type': board_type,
                    'index': idx,
                    'temperature': telemetry.get('ASIC_TEMPERATURE', 0),
                    'power': telemetry.get('INPUT_POWER', 0),
                    'pci_bus': board_info.get('bus_id', 'unknown'),
                    'firmware': firmwares.get('fw_bundle_version', 'unknown'),
                })

        # Determine primary device type
        primary_type = devices[0]['type'] if devices else None

        return {
            'devices': devices,
            'count': len(devices),
            'primary_type': primary_type,
        }

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


def get_mesh_device() -> Optional[str]:
    """
    Get MESH_DEVICE value for current hardware.

    Returns:
        String like "N150", "N300", "T3K", "P100", "P300", etc.
    """
    hw = detect_hardware()
    if not hw:
        return None

    # For multi-device systems, return appropriate mesh device
    device_type = hw['primary_type']
    count = hw['count']

    # Wormhole multi-chip configurations
    if device_type == 'N150' and count == 4:
        return 'N150X4'
    elif device_type == 'N150' and count == 2:
        return 'N300'
    elif device_type == 'N150' and count == 8:
        return 'T3K'

    # Blackhole configurations
    # P300C is a 2-chip board, appears as 2 devices in tt-smi
    if device_type == 'P300C' and count == 2:
        return 'P300'
    elif device_type == 'P300C' and count == 1:
        return 'P100'  # Single chip from P300 board

    # P150 multi-chip configurations
    if device_type in ['P150', 'P150C']:
        if count == 4:
            return 'P150X4'
        elif count == 2:
            return 'P300'  # 2x P150 = P300 equivalent
        else:
            return 'P150'

    # Single chip or unknown configuration
    # Strip the 'C' suffix from board names (P300C -> P300, P100C -> P100)
    if device_type.endswith('C'):
        return device_type[:-1]

    return device_type


def get_arch_name() -> Optional[str]:
    """
    Get TT_METAL_ARCH_NAME for current hardware.

    Returns:
        "blackhole" for P100/P150/P300C, None for others (auto-detected)
    """
    hw = detect_hardware()
    if not hw:
        return None

    device_type = hw['primary_type']

    # Blackhole chips need explicit arch name
    # P300C, P150C, P100C are all Blackhole variants
    if device_type in ['P100', 'P100C', 'P150', 'P150C', 'P300', 'P300C']:
        return 'blackhole'

    # Wormhole auto-detects
    return None


def is_blackhole() -> bool:
    """Check if hardware is Blackhole architecture."""
    hw = detect_hardware()
    if not hw:
        return False
    return hw['primary_type'] in ['P100', 'P100C', 'P150', 'P150C', 'P300', 'P300C']


def is_wormhole() -> bool:
    """Check if hardware is Wormhole architecture."""
    hw = detect_hardware()
    if not hw:
        return False
    return hw['primary_type'] in ['N150', 'N300', 'T3K']


def reset_devices():
    """Reset all Tenstorrent devices using tt-smi."""
    if not has_tt_smi():
        raise RuntimeError("tt-smi not found")

    subprocess.run(['tt-smi', '-r'], check=True)


def clear_device_state():
    """
    Clear device state by:
    1. Killing stale processes
    2. Clearing shared memory
    3. Resetting devices
    """
    import signal
    import os
    import glob

    # Kill stale processes
    try:
        subprocess.run(['pkill', '-9', '-f', 'tt-metal'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-9', '-f', 'vllm'], stderr=subprocess.DEVNULL)
    except:
        pass

    # Clear shared memory
    shm_patterns = [
        '/dev/shm/tenstorrent*',
        '/dev/shm/tt_*',
    ]

    for pattern in shm_patterns:
        for path in glob.glob(pattern):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except:
                pass  # May need sudo for some files

    # Reset devices
    if has_tt_smi():
        try:
            reset_devices()
        except:
            pass


def format_hardware_summary(hw: Optional[Dict]) -> str:
    """
    Format hardware info for display.

    Args:
        hw: Hardware dict from detect_hardware()

    Returns:
        Formatted string
    """
    if not hw:
        return "No hardware detected (tt-smi not available or no devices found)"

    devices = hw['devices']
    count = hw['count']
    primary = hw['primary_type']

    if count == 1:
        dev = devices[0]
        return f"{primary} (firmware {dev['firmware']})"
    else:
        # Multiple devices - show range of temps
        temps = [d['temperature'] for d in devices if d['temperature'] > 0]
        if temps:
            temp_range = f"{min(temps):.0f}-{max(temps):.0f}°C"
        else:
            temp_range = "N/A"

        return f"{count}x {primary} ({temp_range})"
