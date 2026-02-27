# Firmware Downgrade Quick Start

## Quick Reference

### Check Current Firmware
```bash
tt firmware current
```

### List Available Versions
```bash
tt firmware list                # All versions
tt firmware list --recommended  # Hardware-compatible only
```

### Flash Firmware (Interactive Mode)
```bash
# Upgrade - no extra prompts
tt firmware flash 19.5.0

# Downgrade - shows interactive prompt
tt firmware flash 19.3.0
# → Prompts: "Proceed with downgrade? [y/N]:"
# → If yes: adds --allow-major-downgrades automatically
```

### Flash Firmware (Non-Interactive)
```bash
# Skip downgrade prompt (still asks general confirmation)
tt firmware flash 19.3.0 --allow-downgrades

# Fully automated (no prompts at all)
tt firmware flash 19.3.0 --allow-downgrades --yes
```

## What Changed?

### Before This Update
```bash
$ tt firmware flash 19.3.0
# Would fail silently or with confusing error
# Had flag mismatch: CLI used --allow-downgrades but tt-flash expected --allow-major-downgrades
```

### After This Update
```bash
$ tt firmware flash 19.3.0
# Shows clear warning:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠  FIRMWARE DOWNGRADE DETECTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Current version: 19.4.2
  Target version:  19.3.0

Firmware downgrades may cause compatibility issues...

Proceed with downgrade? [y/N]: _
```

## Common Scenarios

### Scenario 1: Testing Older Firmware
```bash
# Interactive - good for manual testing
tt firmware flash 19.3.0
# Answer prompts as they appear

# Automated - good for scripts
tt firmware flash 19.3.0 --allow-downgrades --yes
```

### Scenario 2: Rollback After Issue
```bash
# Check what version you're on
tt firmware current

# List available versions
tt firmware list

# Downgrade to known-good version
tt firmware flash 19.4.1
# Confirm downgrade when prompted
```

### Scenario 3: CI/CD Pipeline
```bash
# Use flags to avoid interactive prompts
tt firmware flash ${TARGET_VERSION} --allow-downgrades --yes
```

## Safety Features

1. **Automatic Detection:** Compares current vs target version
2. **Clear Warning:** Shows version numbers and explains risks
3. **Easy Cancel:** Default is "No" - just press Enter
4. **Helpful Guidance:** Shows alternatives when cancelled
5. **Correct Implementation:** Uses proper `--allow-major-downgrades` flag for tt-flash

## Flags Summary

| Flag | Effect |
|------|--------|
| (none) | Interactive - prompts for confirmation on downgrades |
| `--allow-downgrades` | Skip downgrade prompt, still asks general confirmation |
| `--yes` | Skip general confirmation (but not downgrade prompt unless also using `--allow-downgrades`) |
| `--allow-downgrades --yes` | Fully automated, no prompts at all |
| `--force` | Force ROM update (tt-flash flag) |
| `--no-reset` | Don't reset devices after flash |

## Help Text

```bash
$ tt firmware flash --help

usage: tt firmware flash [-h] [--force] [--no-reset] [--allow-downgrades]
                         [--yes]
                         version_or_path

Flash firmware to devices. Downgrades require interactive confirmation or
--allow-downgrades flag.

positional arguments:
  version_or_path     Firmware version or path to .fwbundle file

options:
  --force             Force update ROM
  --no-reset          Do not reset devices after flash
  --allow-downgrades  Allow firmware downgrades (bypasses tt-flash safety checks)
  --yes               Skip confirmation prompt
```

## Troubleshooting

### Problem: "tt-flash tool not found"
```bash
# Install tt-flash
pip install tt-flash
```

### Problem: "Firmware version X not found"
```bash
# Check available versions
tt firmware list

# Use exact version string from list
tt firmware flash 19.4.2
```

### Problem: Can't downgrade
```bash
# Make sure you're using the right flag
tt firmware flash 19.3.0 --allow-downgrades
```

## Testing Your Setup

```bash
# 1. Check current version
tt firmware current

# 2. List available versions
tt firmware list

# 3. Try flashing current version (should show "already installed")
tt firmware flash $(tt firmware current --json | jq -r .primary_version)

# 4. Verify help text
tt firmware flash --help
```

## Related Documentation

- Full documentation: `FIRMWARE_DOWNGRADE_INTERACTIVE.md`
- Firmware compatibility: `tt/utils/firmware.py:FIRMWARE_RECOMMENDATIONS`
- tt-flash documentation: https://github.com/tenstorrent/tt-flash
