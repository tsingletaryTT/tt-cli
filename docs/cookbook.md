# tt-cli Cookbook

**Common workflows, command sequences, and best practices for the tt-cli tool.**

This cookbook demonstrates practical usage patterns for day-to-day Tenstorrent development. Each recipe shows a complete workflow with real commands and expected outcomes.

---

## Table of Contents

1. [Daily Startup Workflow](#daily-startup-workflow)
2. [Environment Management](#environment-management)
3. [Hardware Verification](#hardware-verification)
4. [Model Management](#model-management)
5. [Server Management](#server-management)
6. [Workflow Automation](#workflow-automation)
7. [Debugging Workflows](#debugging-workflows)
8. [CI/CD Integration](#cicd-integration)
9. [Team Workflows](#team-workflows)
10. [Troubleshooting](#troubleshooting)

---

## Daily Startup Workflow

### Recipe 1: Quick System Check

**Use case**: Start your day by verifying everything is ready for development.

```bash
# Get complete system status (hardware, environment, models)
tt status

# If issues found, run environment diagnostics
tt env check

# Auto-fix any environment issues
tt env fix
```

**Expected output**:
- Hardware detected and healthy
- Environment variables properly set
- Virtual environments found
- Models listed with their locations

**Troubleshooting**: If `tt status` shows no hardware, verify tt-smi installation:
```bash
which tt-smi
tt-smi -s  # Test tt-smi directly
```

---

### Recipe 2: Switching to tt-metal Development

**Use case**: Configure your shell for tt-metal API development.

```bash
# Activate tt-metal environment
tt env use metal

# Verify configuration
tt env check

# Test device connectivity
tt device test
```

**What happens**:
1. Sets `TT_METAL_HOME=~/tt-metal`
2. Configures `PYTHONPATH` for tt-metal imports
3. Sets `LD_LIBRARY_PATH` for OpenMPI
4. Determines `MESH_DEVICE` based on detected hardware
5. Sets `TT_METAL_ARCH_NAME` if needed (Blackhole)

**Next steps**: Source the printed commands to apply to your current shell:
```bash
eval "$(tt env use metal)"
```

---

### Recipe 3: Switching to TT-Forge Development

**Use case**: Work with the experimental TT-Forge compiler.

```bash
# Activate TT-Forge environment (unsets conflicting variables)
tt env use forge

# Verify no conflicts with tt-metal
tt env check
```

**Important**: TT-Forge and tt-metal cannot coexist in the same shell. The CLI automatically:
- Unsets `TT_METAL_HOME`
- Unsets `TT_METAL_VERSION`
- Activates `~/tt-forge-venv`
- Configures `PYTHONPATH` for Forge imports

---

## Environment Management

### Recipe 4: Creating a New Virtual Environment

**Use case**: Set up a fresh environment for a new project.

```bash
# Create venv (uses uv if available, falls back to venv)
python -c "from tt.utils.envmanager import create_venv; create_venv('~/my-project-venv')"

# Verify creation
ls -la ~/my-project-venv
```

**With specific Python version** (requires uv):
```bash
python -c "from tt.utils.envmanager import create_venv; create_venv('~/py310-venv', python_version='3.10')"
```

---

### Recipe 5: Installing Packages in an Environment

**Use case**: Add dependencies to a project environment.

```bash
# Install packages (uses uv if available)
python -c "
from tt.utils.envmanager import install_packages
from pathlib import Path
install_packages(Path('~/my-project-venv'), ['numpy', 'torch', 'pytest'])
"
```

**Why this is better than manual activation**:
- Automatically uses fastest tool available (uv pip or pip)
- Works from any shell environment
- Consistent behavior across systems

---

### Recipe 6: Listing All Environments

**Use case**: See what Python environments exist on your system.

```bash
tt env list
```

**Expected output**:
```
Available Python Environments:
✓ tt-metal      ~/tt-metal/python_env (Python 3.12.3)
✓ vLLM          ~/tt-metal/build/python_env_vllm (Python 3.12.3)
✓ TT-Forge      ~/tt-forge-venv (Python 3.11.8)
✓ TT-XLA        ~/tt-xla-venv (Python 3.11.14)
```

---

## Hardware Verification

### Recipe 7: Device Information

**Use case**: Get detailed hardware specs for your system.

```bash
# Show all device information
tt device info

# JSON output for scripting
tt device info --json
```

**Example output**:
```
Hardware Information:
Type: N150 (Wormhole)
Count: 1 device
Firmware: v1.2.3

Device 0:
  Type: N150
  PCI Bus: 0000:01:00.0
  Temperature: 35.0°C
  Power: 45.0W
```

---

### Recipe 8: Testing Device Connectivity

**Use case**: Verify TTNN can communicate with devices.

```bash
tt device test
```

**What it tests**:
1. Detects available devices
2. Opens device handle via TTNN
3. Performs basic operation (tensor creation)
4. Closes device handle cleanly

**Success output**:
```
Found 1 device(s)
Testing device 0 (N150)...
✓ Device test passed
```

---

### Recipe 9: Multi-Device System Check

**Use case**: Verify all devices in a multi-chip system (N300, T3K, Galaxy).

```bash
# Get device count and configuration
tt device info

# Expected output for T3K (8x N150):
# Type: N150 (Wormhole)
# Count: 8 devices
# MESH_DEVICE: T3K
```

**Verify MESH_DEVICE**:
```bash
tt status | grep MESH_DEVICE
# Should show: MESH_DEVICE=T3K
```

---

## Model Management

### Recipe 10: List Available Models

**Use case**: See what models are already downloaded.

```bash
tt model list
```

**Example output**:
```
Available Models in ~/models:

Qwen3-0.6B
  Architecture: Qwen3ForCausalLM
  Parameters: ~600M
  Size: 1.2 GB

Llama-3.1-8B-Instruct
  Architecture: LlamaForCausalLM
  Parameters: ~8B
  Size: 16 GB
```

---

### Recipe 11: Model Information and Validation

**Use case**: Get detailed config for a specific model.

```bash
# Show model architecture and config
tt model info Qwen3-0.6B

# Validate model has required files
tt model check Qwen3-0.6B
```

**Validation checks**:
- ✓ `config.json` exists and is valid JSON
- ✓ Weight files exist (`.safetensors` or `.bin`)
- ✓ Tokenizer files exist

---

### Recipe 12: Finding Missing Model Files

**Use case**: Debug why a model won't load.

```bash
# Check model structure
tt model check my-model-name

# If files missing, inspect directory
ls -lh ~/models/my-model-name/
```

**Common issues**:
- Missing `config.json` → model not fully downloaded
- No weight files → download interrupted
- No tokenizer files → some inference tools will fail

---

### Recipe 13: Downloading Models from HuggingFace

**Use case**: Download a model directly from HuggingFace Hub.

```bash
# Download a model
tt model get Qwen/Qwen3-0.6B

# Or use download (alias for get)
tt model download Qwen/Qwen3-0.6B
```

**Expected output**:
```
📥 Downloading from HuggingFace Hub: Qwen/Qwen3-0.6B
   Destination: /home/user/models/Qwen3-0.6B

[Download progress from HuggingFace...]

✓ Download complete: /home/user/models/Qwen3-0.6B

Validating model files...
✓ Model validation passed
```

**What it does**:
- Downloads model from HuggingFace Hub using `snapshot_download`
- Saves to `~/models/<model-name>` (extracts name from repo)
- Automatically validates after download
- Supports resume if download interrupted

---

### Recipe 14: Downloading Gated Models

**Use case**: Download models that require HuggingFace authentication.

```bash
# Method 1: Pass token via command line
tt model get meta-llama/Llama-3.1-8B-Instruct --token hf_your_token_here

# Method 2: Set environment variable (recommended)
export HF_TOKEN=hf_your_token_here
tt model get meta-llama/Llama-3.1-8B-Instruct
```

**Getting a HuggingFace token**:
1. Go to https://huggingface.co/settings/tokens
2. Create a new token with "Read" permission
3. Accept the model's terms if gated (e.g., Llama models)

**Environment variable options**:
- `HF_TOKEN` (recommended)
- `HUGGING_FACE_HUB_TOKEN` (also supported)

---

### Recipe 15: Force Re-downloading a Model

**Use case**: Re-download a model to fix corruption or get latest version.

```bash
# Re-download even if model exists
tt model get Qwen/Qwen3-0.6B --force

# Useful when:
# - Model files corrupted
# - Download was interrupted
# - Model updated on HuggingFace
```

**What --force does**:
- Skips the "already exists" check
- Downloads to same location (overwrites)
- Re-validates after download

---

### Recipe 16: Custom Models Directory

**Use case**: Download models to a different location.

```bash
# Download to custom directory
tt model get Qwen/Qwen3-0.6B --models-dir /mnt/models

# Useful for:
# - Large storage on different mount
# - Shared network storage
# - Multiple model repositories
```

**Note**: Server commands will need to know the custom location:
```bash
# Start server with model from custom dir
tt serve start Qwen3-0.6B --models-dir /mnt/models
```

---

### Recipe 17: Downloading Without Validation

**Use case**: Skip validation for faster downloads (not recommended).

```bash
# Skip validation (faster but less safe)
tt model get Qwen/Qwen3-0.6B --no-validate

# Validate later if needed
tt model check Qwen3-0.6B
```

**When to skip validation**:
- You trust the source completely
- You'll validate manually later
- Debugging download issues

**Recommended**: Leave validation enabled (default).

---

### Recipe 18: Model Download Workflow

**Use case**: Complete workflow from download to deployment.

```bash
# 1. Download model
tt model get Qwen/Qwen3-0.6B

# 2. Verify download
tt model check Qwen3-0.6B

# 3. See model details
tt model info Qwen3-0.6B

# 4. Start server with model
tt serve start Qwen3-0.6B --detach

# 5. Test server
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3-0.6B",
    "prompt": "Hello world",
    "max_tokens": 20
  }'

# 6. Stop when done
tt stop Qwen3-0.6B
```

---

## Server Management

### Recipe 19: Starting a vLLM Server

**Use case**: Start a vLLM server with automatic hardware detection and optimal parameters.

```bash
# Start server with auto-detected hardware settings
tt serve start Qwen3-0.6B

# Server auto-configures:
# - Detects hardware (N150, N300, T3K, P100)
# - Sets optimal max_model_len
# - Sets optimal tensor_parallel_size
# - Sets MESH_DEVICE and TT_METAL_ARCH_NAME
```

**Expected output**:
```
Hardware: 1x N150

Starting vLLM server:
  Model: Qwen3-0.6B
  Port: 8000
  max-model-len: 2048
  tensor-parallel-size: 1
  max-num-seqs: 32
  MESH_DEVICE: N150

🚀 Starting server (foreground)...
   Press Ctrl+C to stop
```

**Foreground vs Background**:
```bash
# Foreground (see output, easy to stop with Ctrl+C)
tt serve start Qwen3-0.6B

# Background (detached, runs after shell closes)
tt serve start Qwen3-0.6B --detach
```

---

### Recipe 20: Starting Server on Custom Port

**Use case**: Run multiple models simultaneously on different ports.

```bash
# Start Qwen3-0.6B on port 8000
tt serve start Qwen3-0.6B --port 8000 --detach

# Start Llama-3.1-8B on port 8001
tt serve start Llama-3.1-8B --port 8001 --detach

# Check both are running
tt serve status
```

**Expected output**:
```
Running Servers:

  Qwen3-0.6B
    PID: 12345
    Port: 8000
    CPU: 15.2%
    Memory: 2048 MB

  Llama-3.1-8B
    PID: 12346
    Port: 8001
    CPU: 25.8%
    Memory: 16384 MB
```

---

### Recipe 21: Overriding Auto-Detected Parameters

**Use case**: Manual control over server parameters.

```bash
# Override context length and tensor parallelism
tt serve start Llama-3.1-8B \
  --max-model-len 4096 \
  --tensor-parallel 2 \
  --port 8000 \
  --detach
```

**Why override**:
- **--max-model-len**: Adjust for available memory
- **--tensor-parallel**: Force specific parallelism
- Useful when hardware detection doesn't match your needs

---

### Recipe 22: Stopping a Running Server

**Use case**: Stop a vLLM server gracefully.

```bash
# Stop by model name
tt stop Qwen3-0.6B

# Server attempts graceful shutdown (SIGTERM)
# If not responding after 5 seconds, force kills (SIGKILL)
```

**Expected output**:
```
Stopping server Qwen3-0.6B (PID: 12345, Port: 8000)...
✓ Stopped server Qwen3-0.6B
```

**Troubleshooting**:
```bash
# If server won't stop
ps aux | grep vllm  # Find process manually
kill -9 <PID>  # Force kill

# Clean up stale PID files
rm ~/.tt/servers/*.pid
```

---

### Recipe 23: Checking Server Status

**Use case**: See what servers are running and their resource usage.

```bash
# Human-readable status
tt serve status

# JSON output for scripting
tt serve status --json | jq '.servers[] | {model, port, cpu_percent}'
```

**Example JSON output**:
```json
{
  "servers": [
    {
      "model": "Qwen3-0.6B",
      "pid": 12345,
      "port": 8000,
      "running": true,
      "cpu_percent": 15.2,
      "memory_mb": 2048
    }
  ]
}
```

---

### Recipe 24: Server Logs

**Use case**: Debug server startup or runtime issues.

```bash
# Logs are automatically saved when using --detach
tt serve start Qwen3-0.6B --detach

# View logs
tail -f ~/.tt/servers/logs/qwen3-0.6b.log

# Or use less for scrolling
less ~/.tt/servers/logs/qwen3-0.6b.log
```

**Common log patterns to watch for**:
- `Loading model weights` - Model loading in progress
- `Warmup finished` - Server ready to accept requests
- `Error` - Problems during startup
- `OOM` - Out of memory issues

---

### Recipe 25: Multi-Device Server Startup

**Use case**: Use all devices in a multi-chip system (N300, T3K).

```bash
# Auto-detects device count and sets tensor parallelism
tt serve start Llama-3.1-8B --detach

# For T3K (8 devices), automatically uses:
#   --tensor-parallel-size 8
```

**Verification**:
```bash
# Check environment variables
tt serve status --json | jq '.servers[0]'

# Should show tensor_parallel matching device count
```

---

### Recipe 26: Testing Server is Working

**Use case**: Verify server accepts requests after startup.

```bash
# Start server
tt serve start Qwen3-0.6B --detach

# Wait a moment for warmup
sleep 30

# Test with curl
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3-0.6B",
    "prompt": "Once upon a time",
    "max_tokens": 50
  }'
```

**Expected response**:
```json
{
  "id": "cmpl-xxx",
  "object": "text_completion",
  "created": 1234567890,
  "model": "Qwen3-0.6B",
  "choices": [
    {
      "text": " there was a small village...",
      "index": 0,
      "finish_reason": "length"
    }
  ]
}
```

---

### Recipe 27: Development Workflow with Server

**Use case**: Iterative development with running server.

```bash
# 1. Start server in background
tt serve start Qwen3-0.6B --detach

# 2. Develop your application
python my_app.py  # Uses http://localhost:8000

# 3. Check server status occasionally
tt serve status

# 4. View logs if issues arise
tail ~/.tt/servers/logs/qwen3-0.6b.log

# 5. Stop when done
tt stop Qwen3-0.6B
```

---

### Recipe 28: Server Management in Scripts

**Use case**: Automate server lifecycle in scripts.

```bash
#!/bin/bash
# run-inference.sh

set -e

# Start server if not already running
if ! tt serve status --json | jq -e '.servers[] | select(.model=="Qwen3-0.6B")' > /dev/null; then
    echo "Starting vLLM server..."
    tt serve start Qwen3-0.6B --detach

    # Wait for warmup
    echo "Waiting for server warmup..."
    sleep 30
fi

# Run inference
python my_inference_script.py

# Optionally stop server
# tt stop Qwen3-0.6B
```

---

## Debugging Workflows

### Recipe 29: Diagnosing Environment Issues

**Use case**: Something isn't working, need to check environment.

```bash
# Check for problems
tt env check

# Look for these issues:
# - Missing TT_METAL_HOME
# - Incorrect PYTHONPATH
# - Missing OpenMPI in LD_LIBRARY_PATH
# - Conflicting Forge/Metal variables
```

**Auto-fix**:
```bash
tt env fix
```

**Manual verification**:
```bash
echo $TT_METAL_HOME
echo $PYTHONPATH
echo $LD_LIBRARY_PATH | grep openmpi
```

---

### Recipe 30: Hardware Not Detected

**Use case**: `tt status` shows "No hardware detected".

**Debugging sequence**:

1. **Check tt-smi**:
```bash
which tt-smi
tt-smi -s
```

2. **Check PCI devices**:
```bash
lspci | grep -i tenstorrent
```

3. **Check driver**:
```bash
lsmod | grep tenstorrent
```

4. **Try device test**:
```bash
tt device test
```

**Common fixes**:
- Driver not loaded: `sudo modprobe tenstorrent`
- tt-smi not in PATH: Add to `~/.bashrc`
- Permissions issue: Add user to device group

---

### Recipe 31: Virtual Environment Issues

**Use case**: Package imports failing despite installation.

**Debug steps**:

1. **Verify which Python is active**:
```bash
which python
python --version
```

2. **Check environment list**:
```bash
tt env list
```

3. **Verify PYTHONPATH**:
```bash
echo $PYTHONPATH
```

4. **Re-activate environment**:
```bash
eval "$(tt env use metal)"
```

5. **Reinstall packages if needed**:
```bash
source ~/tt-metal/python_env/bin/activate
pip install --force-reinstall <package>
```

---

## CI/CD Integration

### Recipe 32: Pre-Commit Hardware Check

**Use case**: Verify hardware before running expensive test suite.

```bash
#!/bin/bash
# .git/hooks/pre-push

set -e

echo "Checking Tenstorrent hardware..."
tt device test || {
    echo "❌ Device test failed. Fix hardware before pushing."
    exit 1
}

echo "✓ Hardware check passed"
```

---

### Recipe 33: CI Environment Setup

**Use case**: Configure environment in GitHub Actions / GitLab CI.

```yaml
# .github/workflows/test.yml
- name: Setup Tenstorrent Environment
  run: |
    # Install CLI
    cd /path/to/tt-cli
    pip install -e .

    # Verify hardware
    tt status

    # Configure environment
    eval "$(tt env use metal)"

    # Export for subsequent steps
    echo "TT_METAL_HOME=$TT_METAL_HOME" >> $GITHUB_ENV
    echo "PYTHONPATH=$PYTHONPATH" >> $GITHUB_ENV
    echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH" >> $GITHUB_ENV
    echo "MESH_DEVICE=$MESH_DEVICE" >> $GITHUB_ENV
```

---

### Recipe 34: Model Validation in CI

**Use case**: Ensure required models exist before running inference tests.

```bash
#!/bin/bash
# scripts/verify-models.sh

set -e

REQUIRED_MODELS=("Qwen3-0.6B" "Llama-3.1-8B-Instruct")

for model in "${REQUIRED_MODELS[@]}"; do
    echo "Checking $model..."
    tt model check "$model" || {
        echo "❌ Required model $model not found or invalid"
        exit 1
    }
done

echo "✓ All required models present"
```

---

## Team Workflows

### Recipe 35: Onboarding New Developer

**Use case**: Help teammate set up their environment quickly.

```bash
# 1. Install CLI
git clone /path/to/tt-cli
cd tt-cli
pip install -e .

# 2. Quick system check
tt status

# 3. Fix any environment issues
tt env fix

# 4. Configure for project
tt env use metal
eval "$(tt env use metal)"

# 5. Test device access
tt device test

# 6. Verify models
tt model list
```

**Create setup script** (`setup-dev.sh`):
```bash
#!/bin/bash
set -e

echo "Setting up Tenstorrent development environment..."

# Install CLI
pip install -e /path/to/tt-cli

# Environment setup
tt env fix
eval "$(tt env use metal)"

# Verification
tt device test
tt model list

echo "✓ Setup complete! Run 'tt status' to verify."
```

---

### Recipe 36: Shared Hardware Diagnostics

**Use case**: Team member reports hardware issue, need diagnostics.

```bash
# Collect system info
tt status --json > system-report.json
tt device info --json > device-report.json

# Share reports with team
cat system-report.json
cat device-report.json
```

**Automated diagnostic script**:
```bash
#!/bin/bash
# collect-diagnostics.sh

OUTPUT_DIR="tt-diagnostics-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUTPUT_DIR"

tt status --json > "$OUTPUT_DIR/status.json"
tt device info --json > "$OUTPUT_DIR/devices.json"
tt model list > "$OUTPUT_DIR/models.txt"
tt env check > "$OUTPUT_DIR/environment.txt"

# System info
uname -a > "$OUTPUT_DIR/system.txt"
lspci | grep -i tenstorrent > "$OUTPUT_DIR/pci.txt"

tar -czf "$OUTPUT_DIR.tar.gz" "$OUTPUT_DIR"
echo "Diagnostics saved to $OUTPUT_DIR.tar.gz"
```

---

## Troubleshooting

### Recipe 37: "ImportError: No module named ttnn"

**Problem**: Python can't find TTNN module.

**Solution**:
```bash
# 1. Check environment
tt env check

# 2. Verify PYTHONPATH includes tt-metal
echo $PYTHONPATH | grep tt-metal

# 3. Re-activate environment
eval "$(tt env use metal)"

# 4. Test import
python -c "import ttnn; print('✓ TTNN imported successfully')"
```

---

### Recipe 38: "RuntimeError: No TT devices found"

**Problem**: TTNN can't detect hardware.

**Solution**:
```bash
# 1. Check hardware detection
tt device info

# 2. If no hardware shown, check tt-smi
tt-smi -s

# 3. Check PCI devices
lspci | grep -i tenstorrent

# 4. Check driver
lsmod | grep tenstorrent

# 5. Try loading driver
sudo modprobe tenstorrent

# 6. Test device
tt device test
```

---

### Recipe 39: "OSError: libmpi.so.40: cannot open shared object file"

**Problem**: OpenMPI library not in LD_LIBRARY_PATH.

**Solution**:
```bash
# 1. Fix environment
tt env fix

# 2. Verify LD_LIBRARY_PATH
echo $LD_LIBRARY_PATH | grep openmpi

# 3. Re-activate environment
eval "$(tt env use metal)"

# 4. Verify fix
python -c "import ttnn; print('✓ Libraries loaded')"
```

---

### Recipe 40: TT-Forge and tt-metal Conflict

**Problem**: "Conflicting environment variables detected".

**Solution**:
```bash
# 1. Check for conflicts
tt env check

# 2. Choose which environment you need
tt env use forge   # For TT-Forge work
# OR
tt env use metal   # For tt-metal work

# 3. Apply to shell
eval "$(tt env use forge)"

# 4. Verify no conflicts
tt env check
```

**Why conflicts occur**: TT-Forge and tt-metal use incompatible environment configurations. They cannot run in the same shell session.

---

### Recipe 41: Slow Environment Activation

**Problem**: `tt env use` feels slow.

**Solution**: Install `uv` for 10-100x faster operations:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version

# Now env operations will be much faster
tt env use metal  # Uses uv automatically
```

---

## Advanced Patterns

### Recipe 42: Scripting with JSON Output

**Use case**: Parse CLI output in scripts.

```bash
#!/bin/bash

# Get device info as JSON
DEVICE_JSON=$(tt device info --json)

# Extract specific fields with jq
DEVICE_COUNT=$(echo "$DEVICE_JSON" | jq -r '.count')
PRIMARY_TYPE=$(echo "$DEVICE_JSON" | jq -r '.primary_type')

echo "Found $DEVICE_COUNT x $PRIMARY_TYPE devices"

# Make decisions based on hardware
if [ "$PRIMARY_TYPE" = "N150" ] && [ "$DEVICE_COUNT" -eq 1 ]; then
    echo "Single N150 detected - using small model"
    MODEL="Qwen3-0.6B"
elif [ "$PRIMARY_TYPE" = "N150" ] && [ "$DEVICE_COUNT" -eq 8 ]; then
    echo "T3K detected - using large model"
    MODEL="Llama-3.1-70B"
fi
```

---

### Recipe 43: Environment Variables for Automation

**Use case**: Capture environment config for later use.

```bash
#!/bin/bash

# Save environment to file
tt env use metal > env-metal.sh

# Later, in another shell:
source env-metal.sh

# Or apply to current shell:
eval "$(cat env-metal.sh)"
```

---

### Recipe 44: Multi-Hardware Test Matrix

**Use case**: Test code on different hardware configs.

```bash
#!/bin/bash
# test-matrix.sh

# Detect hardware
HARDWARE_INFO=$(tt device info --json)
DEVICE_TYPE=$(echo "$HARDWARE_INFO" | jq -r '.primary_type')
DEVICE_COUNT=$(echo "$HARDWARE_INFO" | jq -r '.count')

# Determine test suite
case "$DEVICE_TYPE:$DEVICE_COUNT" in
    "N150:1")
        echo "Running N150 single-device tests"
        pytest tests/test_n150.py
        ;;
    "N150:2")
        echo "Running N300 tests"
        pytest tests/test_n300.py
        ;;
    "N150:8")
        echo "Running T3K tests"
        pytest tests/test_t3k.py
        ;;
    "P100:"*)
        echo "Running Blackhole tests"
        pytest tests/test_blackhole.py
        ;;
    *)
        echo "Unknown hardware configuration"
        exit 1
        ;;
esac
```

---

## Workflow Automation

### Recipe 45: Development Environment Setup

**Use case**: Set up your development environment from scratch.

```bash
# Run the setup workflow
tt workflow run setup
```

**What it does**:
1. Checks for `uv` installation (recommends installation if missing)
2. Validates current environment status
3. Applies automatic fixes for common issues
4. Verifies hardware detection
5. Provides next steps guidance

**Output example**:
```
Step 1/5: Checking for uv installation...
✓ uv is installed

Step 2/5: Checking environment status...
✓ Environment is configured correctly

Step 3/5: Checking for environment fixes...
✓ No fixes needed

Step 4/5: Verifying hardware detection...
✓ Detected 2 x P300 device(s)

Step 5/5: Setup complete!

Next steps:
  1. Activate an environment: tt env use metal
  2. List models: tt model list
  3. Check system status: tt status
```

**When to use**: First time setup, after system changes, or when troubleshooting environment issues.

---

### Recipe 46: Complete Model Testing

**Use case**: Download, validate, and test a model end-to-end.

```bash
# Full test (downloads if needed, starts server, tests inference, stops)
tt workflow run test-model --model Qwen3-0.6B

# Quick validation only (no server startup)
tt workflow run test-model --model Qwen3-0.6B --quick
```

**What it does**:
1. Validates model files (config.json, weights, tokenizer)
2. Starts vLLM server in detached mode (if not --quick)
3. Waits for server readiness
4. Runs basic inference test
5. Verifies server status
6. Stops server (always runs, even if test fails)

**Full workflow output**:
```
🧪 Testing Model: Qwen3-0.6B
============================================================

Step 1/5: Validating model files...
✓ Model exists at /home/user/models/Qwen3-0.6B
✓ config.json: valid
✓ Model weights found (2 safetensors files)
✓ tokenizer.json: valid

Step 2/5: Starting vLLM server...
Hardware: 1x N150
Starting vLLM server in background...
✓ Server started successfully (PID: 12345)

Step 3/5: Testing inference...
  Waiting for server to be ready...
  ✓ Server is ready
  Running inference test...
  ✓ Inference test passed

Step 4/5: Verifying server status...
Running Servers:
  Qwen3-0.6B
    PID: 12345
    Port: 8000
    CPU: 15.2%
    Memory: 2048 MB

Step 5/5: Stopping server...
✓ Stopped server Qwen3-0.6B

✓ Model test workflow complete!
```

**Quick mode output**:
```
Step 1/5: Validating model files...
✓ Model exists and all files valid

✓ Model validation complete (quick mode)

To run full test with inference: tt workflow run test-model --model Qwen3-0.6B
```

**When to use**:
- After downloading a new model
- Before deploying to production
- In CI/CD pipelines
- Troubleshooting model issues

---

### Recipe 47: Dry-Run Preview

**Use case**: Preview what a workflow will do without executing it.

```bash
# See what the setup workflow would do
tt workflow run setup --dry-run

# Preview model testing workflow
tt workflow run test-model --model Qwen3-0.6B --dry-run
```

**Output example**:
```
Dry run: Model Testing

Would execute the following steps:
  1. Download model from HuggingFace (if not present)
  2. Validate model files
  3. Start vLLM server
  4. Run basic inference test
  5. Stop server
```

**When to use**: When learning workflows, documenting processes, or verifying workflow steps before execution.

---

### Recipe 48: List Available Workflows

**Use case**: Discover what workflows are available.

```bash
# Human-readable list
tt workflow list

# Machine-readable JSON
tt workflow list --json
```

**Output**:
```
Available Workflows:

  setup
    Development Setup - Set up development environment with uv and create virtual environments

  test-model
    Model Testing - Complete model testing workflow: download, validate, serve, test
    Requires: model

  benchmark
    Model Benchmarking - Run performance benchmarks on a model
    Requires: model

  eval
    Model Evaluation - Run evaluation suites (MMLU, HellaSwag, etc.)
    Requires: model, eval_suite
```

---

### Recipe 49: Workflow Details

**Use case**: Get detailed information about a specific workflow.

```bash
# Show workflow details
tt workflow info test-model
```

**Output**:
```
Model Testing
=============

Description: Complete model testing workflow: download, validate, serve, test

Requires: model

Steps:
  1. Download model from HuggingFace (if not present)
  2. Validate model files
  3. Start vLLM server
  4. Run basic inference test
  5. Stop server

Run with: tt workflow run test-model
Example: tt workflow run test-model --model Qwen3-0.6B
```

---

### Recipe 50: CI/CD Integration with Workflows

**Use case**: Use workflows in continuous integration pipelines.

```bash
#!/bin/bash
# ci-test-pipeline.sh

set -e  # Exit on any error

echo "=== Setting up environment ==="
tt workflow run setup

echo "=== Testing models ==="
# Quick validation for all models
for model in Qwen3-0.6B Llama-3.1-8B; do
    echo "Testing $model..."
    tt workflow run test-model --model "$model" --quick
    if [ $? -ne 0 ]; then
        echo "❌ Model $model failed validation"
        exit 1
    fi
done

echo "=== Full inference test on primary model ==="
tt workflow run test-model --model Qwen3-0.6B

echo "✓ All tests passed!"
```

**GitHub Actions example**:
```yaml
name: Model Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: [self-hosted, tenstorrent]
    steps:
      - uses: actions/checkout@v2

      - name: Setup environment
        run: tt workflow run setup

      - name: Quick model validation
        run: |
          tt workflow run test-model --model Qwen3-0.6B --quick
          tt workflow run test-model --model Llama-3.1-8B --quick

      - name: Full inference test
        run: tt workflow run test-model --model Qwen3-0.6B
```

---

### Recipe 51: Combining Workflows with Other Commands

**Use case**: Mix workflow automation with manual commands for custom pipelines.

```bash
# Setup environment
tt workflow run setup

# Activate tt-metal
eval "$(tt env use metal)"

# Download new model if needed
if ! tt model check DeepSeek-R1-Distill-Llama-70B 2>/dev/null; then
    echo "Downloading model..."
    tt model get deepseek-ai/DeepSeek-R1-Distill-Llama-70B
fi

# Test the model
tt workflow run test-model --model DeepSeek-R1-Distill-Llama-70B --quick

# Start server manually with custom settings
tt serve start DeepSeek-R1-Distill-Llama-70B \
    --detach \
    --port 8001 \
    --max-model-len 16384

# Run custom tests
python my_custom_tests.py --port 8001

# Cleanup
tt stop DeepSeek-R1-Distill-Llama-70B
```

---

### Recipe 52: Troubleshooting Workflow Failures

**Use case**: Debug workflow issues when they fail.

**Scenario 1: Model not found**
```bash
$ tt workflow run test-model --model NonExistent-Model

Step 1/5: Validating model files...
❌ Model not found: /home/user/models/NonExistent-Model

Download with: tt model get NonExistent-Model
```

**Solution**: Download the model first:
```bash
tt model get Qwen/Qwen3-0.6B
tt workflow run test-model --model Qwen3-0.6B
```

---

**Scenario 2: Server fails to start**
```bash
$ tt workflow run test-model --model Qwen3-0.6B

Step 2/5: Starting vLLM server...
❌ Failed to start server
```

**Debug steps**:
```bash
# Check hardware
tt device info
tt device test

# Check environment
tt env check
eval "$(tt env fix --export)"

# Try starting server manually to see full error
tt serve start Qwen3-0.6B

# Check logs
tail -50 ~/.tt/servers/logs/qwen3-0.6b.log
```

---

**Scenario 3: Inference test fails**
```bash
Step 3/5: Testing inference...
  Waiting for server to be ready...
  ❌ Server did not become ready in time
```

**Debug steps**:
```bash
# Check server is actually running
tt serve status

# Check logs for startup errors
tail -100 ~/.tt/servers/logs/qwen3-0.6b.log

# Try manual inference test
curl http://localhost:8000/v1/models

# If port conflict:
tt stop Qwen3-0.6B
tt serve start Qwen3-0.6B --port 8001 --detach
```

---

## Firmware Management Recipes

### Recipe: Checking Current Firmware Version

**Use case**: Verify firmware version on your devices before debugging issues.

```bash
# Show current firmware for all devices
tt firmware current

# Example output:
# Current Firmware:
# Device 0: 19.4.2 (0x13040200)
# Device 1: 19.4.2 (0x13040200)
# ✓ Firmware is recommended for P300C hardware

# Get firmware info as JSON (for scripts)
tt firmware current --json
```

**Why**: Firmware version affects hardware behavior. Checking it first can save debugging time.

---

### Recipe: Listing Available Firmware Versions

**Use case**: See what firmware versions are available for download.

```bash
# List all available firmware versions
tt firmware list

# Example output:
# Available Firmware Versions (for P300C):
# ✓ 19.4.2 (current, recommended) - Released 2026-01-05
# ⭐ 19.4.1 (recommended)          - Released 2025-12-19
# ⭐ 19.4.0 (recommended)          - Released 2025-12-16
# • 19.3.1                        - Released 2025-12-05

# Show only versions recommended for your hardware
tt firmware list --recommended

# Get as JSON
tt firmware list --json
```

**Legend**:
- ✓ = Current version installed
- ⭐ = Recommended for your hardware
- • = Available but not recommended

**Why**: Helps you choose the right firmware version for your hardware.

---

### Recipe: Updating to Latest Firmware

**Use case**: You want to update to the newest available firmware.

```bash
# Check what the latest version is
tt firmware latest

# Example output:
# Hardware: P300C (Blackhole)
# Latest Firmware: 19.4.2 (released 2026-01-05)
# Current Firmware: 19.4.1
# ⬆ Update available: 19.4.1 → 19.4.2
# ✓ Latest firmware is recommended for your hardware

# Download and flash latest (with confirmation)
tt firmware latest --flash

# Skip confirmation prompt (for automation)
tt firmware latest --flash --yes
```

**Recommended workflow**:
1. Check current: `tt firmware current`
2. Check latest: `tt firmware latest`
3. Update if needed: `tt firmware latest --flash`

**Why**: Staying up-to-date ensures you have latest fixes and features.

---

### Recipe: Flashing Firmware with Compatibility Checks

**Use case**: Install specific firmware version to devices.

```bash
# Flash firmware by version (downloads if needed)
tt firmware flash 19.4.2

# Example output:
# Hardware detected: P300C
# Target firmware: 19.4.2
# Current firmware: 19.4.1
# This will flash firmware to all devices. Continue? [y/N]: y
# Flashing firmware: ~/.tt/firmware/fw_pack-80.140.41.0.fwbundle
# ✓ Firmware flashed successfully

# Flash from local bundle file
tt firmware flash /path/to/firmware.fwbundle

# Skip confirmation (for automation/CI)
tt firmware flash 19.4.2 --yes
```

**Important**: The CLI detects your hardware and shows compatibility warnings but **never blocks** the operation. You always have full control.

**Why**: Hardware-aware recommendations help avoid common issues while respecting developer expertise.

---

### Recipe: Flashing Firmware in Automation/CI

**Use case**: Automated firmware updates in CI pipelines without human interaction.

```bash
#!/bin/bash
# CI firmware update script

# Check current firmware
CURRENT=$(tt firmware current --json | jq -r '.primary_version')

# Check latest recommended
tt firmware latest --recommended
LATEST=$(tt firmware latest --json | jq -r '.version')

# Update if needed (skip all prompts)
if [ "$CURRENT" != "$LATEST" ]; then
    echo "Updating firmware from $CURRENT to $LATEST..."
    tt firmware flash $LATEST --yes || exit 1
else
    echo "Firmware up to date: $CURRENT"
fi

# Verify installation
tt firmware verify || exit 1

# Test devices
tt device test || exit 1
```

**Key flags for automation**:
- `--yes`: Skip confirmation prompts
- `--json`: Machine-readable output
- `--recommended`: Show only compatible versions

**Why**: Enables automated firmware management in CI/CD pipelines.

---

## Multi-Device Deployment

Deploy models on individual chips for maximum throughput and isolation.

### Recipe: Starting Server on Specific Device

**Use case**: You want to run a vLLM server on a single chip (device 0) in a multi-chip system.

**Prerequisites**:
- Multi-chip system (e.g., 4x P300C)
- Model downloaded locally
- Active stack configured for single-chip mode

**Command**:
```bash
tt serve start Qwen3-0.6B --port 8000 --device-id 0 --detach
```

**What happens**:
1. CLI detects 4 devices available
2. Sets `TT_VISIBLE_DEVICES=0` to isolate to device 0
3. Creates device-specific cache: `~/.cache/tt_metal_0`
4. Generates mesh descriptor: `single_device_0.textproto`
5. Sets `MESH_DEVICE=P150` (single-chip mode)
6. Starts vLLM server in background
7. Creates PID file: `~/.tt/servers/qwen3-0.6b-dev0.pid`
8. Logs to: `~/.tt/servers/logs/qwen3-0.6b-dev0.log`

**Output**:
```
Hardware: 4x P300C

Using active stack: qwen3-0.6b-p100

Starting vLLM server:
  Model: Qwen3-0.6B
  Port: 8000
  Target device: 0
  TT_VISIBLE_DEVICES: 0
  TT_METAL_CACHE: /home/user/.cache/tt_metal_0
  TT_MESH_GRAPH_DESC_PATH: .../single_device_0.textproto

🚀 Server started in background
✓ Server started successfully (PID: 12345)
```

**Why**: Device isolation ensures each server only accesses its assigned chip, avoiding conflicts.

---

### Recipe: Deploying on All Devices Simultaneously

**Use case**: You want to maximize throughput by running independent servers on all 4 chips.

**Prerequisites**:
- 4-chip system
- Model downloaded
- Stack configured for single-chip mode

**Commands**:
```bash
# Start servers on all 4 devices
tt serve start Qwen3-0.6B --port 8000 --device-id 0 --detach
tt serve start Qwen3-0.6B --port 8001 --device-id 1 --detach
tt serve start Qwen3-0.6B --port 8002 --device-id 2 --detach
tt serve start Qwen3-0.6B --port 8003 --device-id 3 --detach

# Check all servers
tt status
```

**What happens**:
- Each server gets isolated to its device via `TT_VISIBLE_DEVICES`
- Each has separate cache directory
- Each has unique mesh descriptor
- All run independently on different ports
- No data-parallel coordination overhead

**Output**:
```
🚀 Running Servers
   Total: 4 server(s)
   Ready: 4 | Initializing: 0

   ✓ Port 8000 (device 0): READY
   ✓ Port 8001 (device 1): READY
   ✓ Port 8002 (device 2): READY
   ✓ Port 8003 (device 3): READY
```

**Performance**:
- **4x throughput**: Each device runs at full capacity
- **No coordination overhead**: No data-parallel synchronization
- **Independent scaling**: Each server has its own request queue
- **Fault isolation**: One device failing doesn't affect others

**Why**: Ideal for maximizing aggregate throughput across all chips.

---

### Recipe: Testing Multi-Device Deployment

**Use case**: You want to verify all 4 servers are working correctly.

**Prerequisites**:
- 4 servers running on ports 8000-8003

**Commands**:
```bash
# Test each server with simple inference request
for port in 8000 8001 8002 8003; do
  echo "=== Testing device on port $port ==="
  curl -s http://localhost:$port/v1/completions \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"/home/user/models/Qwen3-0.6B\",
      \"prompt\": \"Hello from device $port!\",
      \"max_tokens\": 10
    }" | jq '.choices[0].text'
  echo
done
```

**Expected output**:
```
=== Testing device on port 8000 ===
" I'm a test server running..."

=== Testing device on port 8001 ===
" This is device 1 responding..."

=== Testing device on port 8002 ===
" Device 2 online and ready..."

=== Testing device on port 8003 ===
" Server 3 is operational..."
```

**Load balancing test**:
```bash
# Send concurrent requests to all devices
for i in {1..10}; do
  port=$((8000 + i % 4))
  curl -s http://localhost:$port/v1/completions \
    -H "Content-Type: application/json" \
    -d '{"model": "/home/user/models/Qwen3-0.6B", "prompt": "Test", "max_tokens": 5}' &
done
wait

echo "All 10 requests completed across 4 devices"
```

**Why**: Verifies device isolation is working and servers can handle concurrent load.

---

### Recipe: Switching Between Single-Chip and Multi-Chip Modes

**Use case**: You want to toggle between "all devices" (data parallel) and "per device" (independent servers).

**Prerequisites**:
- Multiple stack configurations defined
- Servers can be stopped/started

**Multi-chip mode (data parallel)**:
```bash
# Stop all per-device servers
tt stop Qwen3-0.6B --device-id 0
tt stop Qwen3-0.6B --device-id 1
tt stop Qwen3-0.6B --device-id 2
tt stop Qwen3-0.6B --device-id 3

# Switch to multi-chip stack
tt stack use qwen3-0.6b-p150x4

# Start single server using all devices
tt serve start Qwen3-0.6B --detach
```

**Single-chip mode (per device)**:
```bash
# Stop multi-chip server
tt stop Qwen3-0.6B

# Switch to single-chip stack
tt stack use qwen3-0.6b-p100

# Start independent servers
tt serve start Qwen3-0.6B --port 8000 --device-id 0 --detach
tt serve start Qwen3-0.6B --port 8001 --device-id 1 --detach
tt serve start Qwen3-0.6B --port 8002 --device-id 2 --detach
tt serve start Qwen3-0.6B --port 8003 --device-id 3 --detach
```

**Stack configurations**:

Multi-chip (`qwen3-0.6b-p150x4`):
```yaml
stacks:
  qwen3-0.6b-p150x4:
    description: 'Qwen3 0.6B on P150X4 (4-chip data parallel)'
    metal: v0.66.0-rc7
    model: Qwen3-0.6B
    hardware: P150X4
    config:
      max_model_len: 4096
      max_num_seqs: 64  # 16 * 4 for data parallel
      data_parallel: 4
    override_tt_config:
      data_parallel: 4
```

Single-chip (`qwen3-0.6b-p100`):
```yaml
stacks:
  qwen3-0.6b-p100:
    description: 'Qwen3 0.6B on P150 (single chip per instance)'
    metal: v0.66.0-rc7
    model: Qwen3-0.6B
    hardware: P150
    config:
      max_model_len: 2048
      max_num_seqs: 16
      tensor_parallel: 1
```

**Why**: Different workloads benefit from different modes:
- **Data parallel (multi-chip)**: Better for large batch inference
- **Independent (per-chip)**: Better for maximum throughput with small batches

---

**Key flags for automation**:
- `--yes`: Skip confirmation prompts
- `--json`: Machine-readable output
- `--recommended`: Show only compatible versions

**Why**: Enables automated firmware management in CI/CD pipelines.

---

## Best Practices

### 1. Always Check Status First

Start every session with `tt status` to catch issues early.

### 2. Use Environment Validation

Run `tt env check` before debugging mysterious failures. Many issues are environment-related.

### 3. Leverage Auto-Fix

`tt env fix` can automatically resolve most environment issues. Try it before manual debugging.

### 4. Use JSON for Scripting

Always use `--json` flag when parsing CLI output in scripts. Text output format may change.

### 5. Test Device Connectivity

Run `tt device test` after environment changes to verify TTNN can still access hardware.

### 6. Keep Environments Separate

Never mix TT-Forge and tt-metal in the same shell. Use `tt env use` to switch cleanly.

### 7. Document Your Model Requirements

Use `tt model list` and `tt model check` in CI to enforce model prerequisites.

### 8. Install uv for Speed

Installing `uv` provides 10-100x faster environment operations with zero downside.

---

## Command Cheat Sheet

| Task | Command |
|------|---------|
| **System & Status** | |
| System overview | `tt status` |
| Hardware info | `tt device info` |
| Test devices | `tt device test` |
| **Models** | |
| Download model | `tt model get <repo>` |
| Download gated model | `tt model get <repo> --token <token>` |
| List models | `tt model list` |
| Check model | `tt model check <name>` |
| Model info | `tt model info <name>` |
| **Servers** | |
| Start vLLM server | `tt serve start <model> [--detach]` |
| Start on specific device | `tt serve start <model> --device-id N --port P [--detach]` |
| Stop server | `tt stop <model>` |
| Stop device-specific | `tt stop <model> --device-id N` |
| Server status | `tt serve status [--json]` |
| **Environment** | |
| Check environment | `tt env check` |
| Fix environment | `eval "$(tt env fix --export)"` |
| Activate tt-metal | `eval "$(tt env use metal)"` |
| Activate TT-Forge | `eval "$(tt env use forge)"` |
| List environments | `tt env list` |
| **Firmware** | |
| Current firmware | `tt firmware current` |
| List available | `tt firmware list` |
| List recommended | `tt firmware list --recommended` |
| Latest version | `tt firmware latest` |
| Download firmware | `tt firmware download <version>` |
| Flash firmware | `tt firmware flash <version>` |
| Flash (no prompts) | `tt firmware flash <version> --yes` |
| Verify firmware | `tt firmware verify` |
| **Workflows** | |
| List workflows | `tt workflow list` |
| Workflow details | `tt workflow info <name>` |
| Run workflow | `tt workflow run <name>` |
| Setup environment | `tt workflow run setup` |
| Test model | `tt workflow run test-model --model <name>` |
| Quick model check | `tt workflow run test-model --model <name> --quick` |
| Dry-run preview | `tt workflow run <name> --dry-run` |
| **Configuration** | |
| Get config value | `tt config get <key>` |
| Set config value | `tt config set <key> <value>` |
| List all config | `tt config list` |
| Reset config | `tt config reset` |
| **Output Formats** | |
| JSON output | Add `--json` flag to most commands |

---

## Questions or Issues?

- File issues: `/path/to/tt-cli/issues`
- Read docs: `README.md`, `docs/quickstart.md`
- Check status: `docs/status.md`

**Remember**: The CLI is designed to eliminate one-off scripts. If you find yourself writing throwaway code, consider whether it should be a CLI command instead.
