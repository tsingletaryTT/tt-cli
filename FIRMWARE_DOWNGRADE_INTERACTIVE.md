# Firmware Downgrade Interactive Prompts

## Overview

The `tt firmware flash` command now provides interactive prompts and safety checks when attempting firmware downgrades. This gives developers explicit control over downgrade operations while maintaining safety by default.

## What Changed

### 1. Fixed tt-flash Flag Mismatch
- **Before:** tt-cli used `--allow-downgrades` but tt-flash expects `--allow-major-downgrades`
- **After:** Correct flag is now passed to tt-flash
- **File:** `tt/utils/firmware.py:560`

### 2. Added Interactive Downgrade Prompt
When a downgrade is detected (target version < current version):
- Displays clear warning with version comparison
- Explains potential risks
- Prompts user for confirmation
- Only shown when `--allow-downgrades` flag is NOT used
- Skipped when `--yes` flag is used (non-interactive mode)

### 3. Enhanced Help Text
- CLI help now mentions interactive confirmation requirement
- Clearer description of what `--allow-downgrades` does

## Usage Examples

### Case 1: Interactive Downgrade (Default Behavior)
```bash
$ tt firmware flash 19.3.0

Hardware detected: P300C
Target firmware: 19.3.0

⚠ Warning: This is a downgrade from 19.4.2 to 19.3.0

Current firmware: 19.4.2
Target firmware:  19.3.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠  FIRMWARE DOWNGRADE DETECTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Current version: 19.4.2
  Target version:  19.3.0

Firmware downgrades may cause compatibility issues or unexpected behavior.
This operation will override tt-flash safety checks.

Options:
  [y] Yes, proceed with downgrade (adds --allow-major-downgrades)
  [n] No, cancel operation (default)

Proceed with downgrade? [y/N]: y

✓ Downgrade confirmed - proceeding with --allow-major-downgrades

This will flash firmware to all devices.
Continue? [y/N]: y

Flashing firmware: ~/.tt/firmware/fw_pack-80.130.30.0.fwbundle
Command: tt-flash flash ~/.tt/firmware/fw_pack-80.130.30.0.fwbundle --allow-major-downgrades
...
```

### Case 2: Bypass Interactive Prompt with Flag
```bash
# Skip interactive prompt by explicitly allowing downgrades
$ tt firmware flash 19.3.0 --allow-downgrades

Hardware detected: P300C
Target firmware: 19.3.0

⚠ Warning: This is a downgrade from 19.4.2 to 19.3.0

Current firmware: 19.4.2
Target firmware:  19.3.0

This will flash firmware to all devices.
Continue? [y/N]: y

Flashing firmware: ~/.tt/firmware/fw_pack-80.130.30.0.fwbundle
Command: tt-flash flash ~/.tt/firmware/fw_pack-80.130.30.0.fwbundle --allow-major-downgrades
...
```

### Case 3: Fully Non-Interactive
```bash
# Skip ALL prompts (useful for automation)
$ tt firmware flash 19.3.0 --allow-downgrades --yes

Hardware detected: P300C
Target firmware: 19.3.0

⚠ Warning: This is a downgrade from 19.4.2 to 19.3.0

Current firmware: 19.4.2
Target firmware:  19.3.0

Flashing firmware: ~/.tt/firmware/fw_pack-80.130.30.0.fwbundle
Command: tt-flash flash ~/.tt/firmware/fw_pack-80.130.30.0.fwbundle --allow-major-downgrades
...
```

### Case 4: User Cancels Downgrade
```bash
$ tt firmware flash 19.3.0

...
Proceed with downgrade? [y/N]: n

Cancelled - downgrade not performed

To flash this version, either:
  • Use a newer firmware version (try: tt firmware list --recommended)
  • Add --allow-downgrades flag to bypass this check
```

## Implementation Details

### Downgrade Detection Logic
```python
# In tt/commands/firmware.py:349-356
is_downgrade = False
if current_version != "unknown" and version != current_version:
    comparison = firmware.compare_versions(version, current_version)
    if comparison < 0:
        is_downgrade = True
        print(f"⚠ Warning: This is a downgrade from {current_version} to {version}")
```

### Interactive Prompt Logic
```python
# In tt/commands/firmware.py:378-410
if is_downgrade and not args.allow_downgrades and not args.yes:
    # Show warning UI
    response = input("Proceed with downgrade? [y/N]: ").strip().lower()

    if response not in ['y', 'yes']:
        print("Cancelled - downgrade not performed")
        return 0

    # User confirmed - enable flag
    args.allow_downgrades = True
```

### Correct tt-flash Flag
```python
# In tt/utils/firmware.py:559-561
if allow_downgrades:
    cmd.append('--allow-major-downgrades')  # ✓ Correct flag
```

## Files Modified

1. **`tt/utils/firmware.py`**
   - Line 560: Fixed `--allow-downgrades` → `--allow-major-downgrades`
   - Updated docstring

2. **`tt/commands/firmware.py`**
   - Lines 350-361: Added downgrade detection with `is_downgrade` flag
   - Lines 375-376: Set `is_downgrade = False` when hardware not detected
   - Lines 378-410: Added interactive downgrade prompt

3. **`tt/core/cli.py`**
   - Line 835: Added description to flash parser
   - Line 856: Enhanced help text for `--allow-downgrades` flag

## Safety Features

1. **Default Safe Behavior:** Downgrades require explicit confirmation
2. **Clear Warnings:** User sees version comparison before proceeding
3. **Risk Explanation:** Prompt explains potential issues
4. **Multiple Confirmation Points:**
   - Downgrade confirmation (if detected)
   - General flash confirmation (unless --yes)
5. **Easy Exit:** Default is "No" - pressing Enter cancels
6. **Helpful Guidance:** Shows alternatives when user cancels

## Testing

### Unit Test Scenarios
- ✅ Upgrade (newer version) - no extra prompt
- ✅ Downgrade without flags - shows interactive prompt
- ✅ Downgrade with `--allow-downgrades` - skips interactive prompt
- ✅ Downgrade with `--yes` - fully non-interactive
- ✅ User confirms downgrade - proceeds with flag enabled
- ✅ User cancels downgrade - exits with helpful message
- ✅ Unknown version (file path) - no downgrade detection

### Manual Testing Commands
```bash
# Get current firmware version
tt firmware current

# List available versions
tt firmware list

# Test interactive downgrade (to older version)
tt firmware flash 19.3.0

# Test bypass with flag
tt firmware flash 19.3.0 --allow-downgrades

# Test fully automated
tt firmware flash 19.3.0 --allow-downgrades --yes
```

## Benefits

1. **✅ Safety First:** Prevents accidental downgrades
2. **✅ Developer Control:** Easy to override when needed
3. **✅ Clear Communication:** User understands what's happening
4. **✅ Correct Implementation:** Uses proper tt-flash flags
5. **✅ Flexible:** Supports both interactive and automated workflows
6. **✅ Helpful:** Provides guidance when operations are cancelled

## Future Enhancements

Possible improvements for future versions:
- Add `--force-downgrade` alias for `--allow-downgrades`
- Log downgrade operations to audit file
- Add telemetry to understand downgrade patterns
- Show release notes diff between versions
- Add `--explain` flag to show why downgrade might be needed

## Related Commands

- `tt firmware list` - See available firmware versions
- `tt firmware list --recommended` - See hardware-compatible versions
- `tt firmware current` - Check current firmware version
- `tt firmware latest` - Get latest firmware version
- `tt doctor` - Check overall system health

## Documentation

For more information:
- tt-flash documentation: https://github.com/tenstorrent/tt-flash
- Firmware compatibility: See `tt/utils/firmware.py:FIRMWARE_RECOMMENDATIONS`
- Hardware detection: See `tt/utils/hardware.py`
