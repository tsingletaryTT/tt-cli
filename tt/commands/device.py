"""
Device management commands
"""

import sys

from tt.utils import hardware


def test(args):
    """Test all Tenstorrent devices."""
    print()
    print("Testing Tenstorrent devices...")
    print()

    # Detect hardware
    hw = hardware.detect_hardware()
    if not hw:
        print("✗ No hardware detected")
        print()
        print("Possible issues:")
        print("  • tt-smi not installed")
        print("  • No Tenstorrent devices present")
        print("  • Device drivers not loaded")
        print()
        return 1

    print(f"Detected: {hardware.format_hardware_summary(hw)}")
    print()

    # Test each device
    try:
        import ttnn

        num_devices = ttnn.GetNumAvailableDevices()
        print(f"Found {num_devices} device(s) available to TTNN")
        print()

        if num_devices == 0:
            print("✗ No devices available (may need device reset)")
            print("  Try: tt device reset")
            return 1

        # Create and test devices
        print("Creating devices...")
        devices = ttnn.CreateDevices(list(range(num_devices)))

        try:
            for i, device in enumerate(devices):
                print(f"  Testing device {i}... ", end='', flush=True)

                # Basic test: allocate a tensor
                tensor = ttnn.zeros((1024, 1024), device=device)

                print("✓ OK")

        finally:
            print()
            print("Closing devices...")
            ttnn.CloseDevices(devices)

        print()
        print(f"✓ All {num_devices} device(s) tested successfully")
        print()
        return 0

    except ImportError:
        print("✗ TTNN not available")
        print()
        print("To use device testing:")
        print("  1. Install tt-metal")
        print("  2. Build tt-metal: cd ~/tt-metal && ./build_metal.sh")
        print("  3. Set environment: tt env use metal")
        print()
        return 1

    except Exception as e:
        print(f"\n✗ Device test failed: {e}")
        print()
        print("Troubleshooting:")
        print("  • Try: tt device reset")
        print("  • Try: tt device clear")
        print("  • Check: tt-smi")
        print()
        return 1


def info(args):
    """Show detailed device information."""
    print()

    # Check if tt-smi is available
    if not hardware.has_tt_smi():
        print("✗ tt-smi not found")
        print()
        print("Install tt-smi to get device information:")
        print("  https://github.com/tenstorrent/tt-smi")
        print()
        return 1

    # Get device information
    hw = hardware.detect_hardware()
    if not hw:
        print("✗ No devices detected")
        print()
        return 1

    # Display information
    print(f"Tenstorrent Hardware Information")
    print("=" * 70)
    print()

    print(f"Device Count: {hw['count']}")
    print(f"Primary Type: {hw['primary_type']}")
    print()

    print("Devices:")
    for dev in hw['devices']:
        print(f"  Device {dev['index']}:")
        print(f"    Type: {dev['type']}")
        print(f"    PCI Bus: {dev['pci_bus']}")
        print(f"    Firmware: {dev['firmware']}")

        if dev['temperature'] > 0:
            print(f"    Temperature: {dev['temperature']:.1f}°C")
        if dev['power'] > 0:
            print(f"    Power: {dev['power']:.1f}W")
        print()

    # Mesh device info
    mesh = hardware.get_mesh_device()
    if mesh:
        print(f"MESH_DEVICE: {mesh}")

    # Architecture info
    arch = hardware.get_arch_name()
    if arch:
        print(f"TT_METAL_ARCH_NAME: {arch}")

    print()


def reset(args):
    """Reset all devices."""
    print()
    print("Resetting Tenstorrent devices...")

    if not hardware.has_tt_smi():
        print("✗ tt-smi not found")
        print()
        return 1

    try:
        hardware.reset_devices()
        print("✓ Devices reset successfully")
        print()
        return 0
    except Exception as e:
        print(f"✗ Failed to reset devices: {e}")
        print()
        return 1


def clear(args):
    """Clear device state and shared memory."""
    print()
    print("Clearing device state...")
    print("This will:")
    print("  1. Kill stale tt-metal and vLLM processes")
    print("  2. Clear shared memory (/dev/shm)")
    print("  3. Reset devices")
    print()

    response = input("Continue? [y/N]: ")
    if response.lower() != 'y':
        print("Cancelled")
        return 0

    print()
    print("Clearing...")

    try:
        hardware.clear_device_state()
        print("✓ Device state cleared")
        print()
        print("Note: Some files may require sudo to remove")
        print("      If issues persist, try: sudo tt device clear")
        print()
        return 0
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
        return 1
