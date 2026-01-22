# tt-cli Quick Start Guide

## Installation

```bash
cd ~/tt-cli
pip install -e .
```

Verify installation:
```bash
tt --version
# Output: tt-cli 0.1.0
```

## First Steps

### 1. Check System Status

```bash
tt status
```

This shows:
- Hardware detection (if tt-smi available)
- Environment status (TT_METAL_HOME, PYTHONPATH, etc.)
- Installed models
- Quick command reference

### 2. Fix Environment Issues

```bash
tt env fix
```

Auto-fixes common issues:
- Sets TT_METAL_HOME
- Adds OpenMPI to LD_LIBRARY_PATH
- Configures PYTHONPATH

**Note:** Environment changes affect the current shell only. For persistent changes, add to `~/.bashrc`.

### 3. List Available Environments

```bash
tt env list
```

Shows:
- `metal` - TT-Metal development
- `vllm` - vLLM server environment
- `forge` - TT-Forge compiler
- `xla` - TT-XLA/JAX

### 4. Switch Environments

```bash
tt env use vllm
```

Automatically:
- Sets required environment variables
- Unsets conflicting variables (e.g., for TT-Forge)
- Handles path expansions

### 5. Check Models

```bash
tt model list
tt model info Qwen3-0.6B
tt model check Qwen3-0.6B
```

### 6. Device Management

```bash
tt device info     # Show hardware details
tt device test     # Test all devices
tt device reset    # Reset devices
tt device clear    # Full cleanup (processes + shared memory)
```

## Command Reference

### Status
```bash
tt status          # Human-readable overview
tt status --json   # Machine-readable JSON
```

### Environment Management
```bash
tt env list                    # List environments
tt env use <name>              # Switch environment
tt env check                   # Validate current environment
tt env fix                     # Auto-fix issues
tt env setup <name>            # Create new environment
tt env setup <name> --python 3.10  # Requires uv
tt env install-uv              # Install uv for speed
```

### Device Management
```bash
tt device test     # Test all devices with TTNN
tt device info     # Show device information
tt device reset    # Reset devices via tt-smi
tt device clear    # Full cleanup (kill processes, clear shm)
```

### Model Management
```bash
tt model list              # List installed models
tt model info <name>       # Show model details
tt model check <name>      # Validate model files
tt model get <name>        # Download (coming soon)
```

### Server Management (Coming Soon)
```bash
tt serve <model>           # Start vLLM server
tt serve <model> --port 8001  # Custom port
tt stop <model>            # Stop server
tt restart <model>         # Restart server
```

## Environment Variables (Handled Automatically)

When you run `tt env use <name>`, these are set automatically:

**tt-metal:**
- `TT_METAL_HOME=~/tt-metal`
- `PYTHONPATH=~/tt-metal`
- `LD_LIBRARY_PATH=/opt/openmpi-v5.0.7-ulfm/lib`

**vllm:**
- Same as tt-metal (vLLM runs on tt-metal)

**forge:**
- `PYTHONPATH=~/tt-forge`
- **Unsets:** `TT_METAL_HOME`, `TT_METAL_VERSION` (critical!)

**xla:**
- `PJRT_PLUGIN_LIBRARY_PATH=~/tt-xla/build/lib/libpjrt_tt.so`
- `LD_LIBRARY_PATH=/opt/openmpi-v5.0.7-ulfm/lib`

## Tips

### Speed Up Environment Operations

Install `uv` for 10-100x faster package management:

```bash
tt env install-uv
```

Then use:
```bash
tt env setup myenv --python 3.10  # Creates venv with Python 3.10
```

### Persistent Environment Changes

Add to `~/.bashrc`:
```bash
# Tenstorrent environment
export TT_METAL_HOME=~/tt-metal
export PYTHONPATH=$TT_METAL_HOME:$PYTHONPATH
export LD_LIBRARY_PATH=/opt/openmpi-v5.0.7-ulfm/lib:$LD_LIBRARY_PATH
```

Or source the result of `tt env use`:
```bash
# Not yet implemented - coming soon!
eval "$(tt env use vllm --export)"
```

### JSON Output for Scripting

```bash
tt status --json | jq '.hardware.count'
# Output: 4
```

## What's Working (v0.1.0)

✅ **Core Commands:**
- `tt status` - Full system status
- `tt env {list,use,check,fix,setup,install-uv}` - Environment management
- `tt device {info,test,reset,clear}` - Device management
- `tt model {list,info,check}` - Model management

✅ **Features:**
- Zero dependencies (stdlib only)
- Hybrid venv/uv support (uses uv when available)
- Smart environment conflict handling (Forge vs Metal)
- Comprehensive error messages

## What's Coming Next

🚧 **Phase 2 (Week 3-4):**
- `tt serve` - Server management (integrate tt-jukebox)
- `tt workflow` - tt-inference-server workflows
- `tt model get` - Model downloads
- `tt model convert` - Format conversion

🚧 **Phase 3 (Week 5-6):**
- Configuration file support
- Error recovery and suggestions
- TUI interface (`tt-tui`)
- PyPI packaging

## Getting Help

```bash
tt --help                  # Main help
tt <command> --help        # Command-specific help
tt status                  # Shows quick commands
```

## Troubleshooting

### "tt: command not found"

Install the CLI:
```bash
cd ~/tt-cli
pip install -e .
```

### Environment changes don't persist

This is expected - each command runs in a subshell. For persistent changes, add to `~/.bashrc`.

### "tt-smi not found"

Hardware detection requires tt-smi. The CLI still works without it, but:
- Can't detect hardware automatically
- Can't reset devices
- Some features limited

Install tt-smi: https://github.com/tenstorrent/tt-smi

### OpenMPI errors

Run:
```bash
tt env fix
```

This adds OpenMPI to LD_LIBRARY_PATH automatically.

## Development

To contribute or modify:

```bash
cd ~/tt-cli

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Make changes to tt/ directory
# Changes take effect immediately (no reinstall needed)

# Test
tt status

# Run tests (when available)
pytest
```

## Philosophy

1. **Zero dependencies** - Core CLI uses only stdlib
2. **Smart defaults** - Works without configuration
3. **Graceful degradation** - Falls back when tools missing
4. **Transparent** - Shows what it's doing
5. **Fast iteration** - Python for rapid development

---

**Stop writing throwaway scripts. Start using `tt`.** 🚀
