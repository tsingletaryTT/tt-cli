# tt-cli: One Command to Rule Them All

<div align="center">

**Unified command-line interface for Tenstorrent hardware development**

[![Tests](https://img.shields.io/badge/tests-88%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-90%25+-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](setup.py)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Stop maintaining throwaway scripts. Start using `tt`.

[Quick Start](#quick-start) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

---

## The Problem

Every Tenstorrent developer has a `~/tt-scratchpad/` directory full of scripts they don't want to maintain:

```bash
~/tt-scratchpad/
├── start-vllm-server.py           # 200 lines just to start a server
├── start-vllm-server-n150.py      # Same script, different hardware
├── start-vllm-server-qwen.py      # Same script, different model
├── setup-vllm-env.sh              # 50 lines of environment boilerplate
├── activate-metal-env.sh          # More environment scripts
├── test-multi-device.py           # Device testing wrapper
├── download-model.py              # Model download logic
└── ...15 more scripts...          # ~1,100 lines of throwaway code
```

**These scripts are all solving the same problems**:
- Starting servers with the right arguments
- Setting up environments with correct variables
- Testing hardware is working
- Managing models

**You should write application code, not infrastructure boilerplate.**

## The Solution

`tt-cli` replaces ~270 lines of scripts with simple, memorable commands:

```bash
# ✨ Start a server (auto-detects hardware, sets optimal params)
tt serve start llama-3.1-8b

# ✨ Switch environments (handles conflicts automatically)
tt env use vllm

# ✨ Test your devices
tt device test

# ✨ Check model is valid
tt model check Qwen3-0.6B

# ✨ See everything at a glance
tt status
```

**Before and after**:

| Task | Before (scripts) | After (tt-cli) |
|------|------------------|----------------|
| Start vLLM server | `python ~/tt-scratchpad/start-vllm-server.py --model ~/models/Llama-3.1-8B --max-model-len 2048 --tensor-parallel 2 --max-num-seqs 16 ...` | `tt serve start llama-3.1-8b` |
| Switch to tt-metal | `source ~/tt-scratchpad/activate-metal-env.sh` | `tt env use metal` |
| Test 8 devices | `python ~/tt-scratchpad/test-multi-device.py` | `tt device test` |
| Check model valid | `python ~/tt-scratchpad/validate-model.py Qwen3-0.6B` | `tt model check Qwen3-0.6B` |
| System overview | `python ~/tt-scratchpad/show-status.py` | `tt status` |

---

## Installation

### Quick Start (Development)

```bash
# Clone and install
git clone https://github.com/tenstorrent/tt-cli.git
cd tt-cli
pip install -e .

# Verify installation
tt --version
tt status
```

### From PyPI (Coming Soon)

```bash
pip install tt-cli
```

### Optional: Install uv for 10-100x Faster Operations

```bash
# Install uv (optional but recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify
uv --version
```

When `uv` is installed, `tt` automatically uses it for venv operations. When not available, falls back to standard `venv`. **Zero configuration required.**

---

## Quick Start

### First Run

```bash
# Check everything is working
$ tt status

Hardware: N150 (Wormhole)
  Devices: 1x N150
  Firmware: v1.2.3
  Status: ✓ Healthy

Environment:
  TT_METAL_HOME: /home/user/tt-metal
  MESH_DEVICE: N150
  PYTHONPATH: ✓ Configured
  LD_LIBRARY_PATH: ✓ Configured

Models:
  Qwen3-0.6B (600M params)
  Llama-3.1-8B-Instruct (8B params)
```

### Common Workflows

**Daily development startup**:
```bash
# Check system status
tt status

# Fix any environment issues
tt env fix

# Test devices are working
tt device test
```

**Switch between projects**:
```bash
# Working on tt-metal
tt env use metal

# Switch to TT-Forge
tt env use forge

# Switch to TT-XLA
tt env use xla
```

**Model management**:
```bash
# List installed models
tt model list

# Validate model
tt model check Qwen3-0.6B

# Get model details
tt model info Llama-3.1-8B-Instruct
```

**Hardware testing**:
```bash
# Get device info
tt device info

# Test devices (TTNN connectivity)
tt device test
```

---

## Features

### ✅ Phase 1: Core CLI (Implemented)

#### 🖥️ Hardware Management
- **Auto-detect devices** via tt-smi integration
- **Multi-device support** (N150, N300, T3K, P100, Galaxy)
- **Device testing** with TTNN CreateDevices/CloseDevices API
- **Hardware info** with temperature, power, PCI details

```bash
$ tt device info

Hardware Information:
Type: N150 (Wormhole)
Count: 1 device
Firmware: v1.2.3

Device 0:
  PCI Bus: 0000:01:00.0
  Temperature: 35.0°C
  Power: 45.0W
  Status: ✓ Healthy
```

#### 🔧 Environment Management
- **Hybrid venv approach** (uses `uv` when available, falls back to `venv`)
- **Conflict detection** (TT-Forge vs tt-metal auto-handled)
- **Auto-fix common issues** (missing vars, wrong paths)
- **Multi-environment support** (tt-metal, vLLM, TT-Forge, TT-XLA)

```bash
$ tt env use metal

export TT_METAL_HOME=/home/user/tt-metal
export PYTHONPATH=/home/user/tt-metal
export LD_LIBRARY_PATH=/opt/openmpi-v5.0.7-ulfm/lib:$LD_LIBRARY_PATH
export MESH_DEVICE=N150

✓ Environment configured for tt-metal

# Apply to current shell:
eval "$(tt env use metal)"
```

#### 📦 Model Management
- **List installed models** with architecture and size
- **Validate models** (check config.json, weights, tokenizer)
- **Model info** with detailed config inspection

```bash
$ tt model list

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

#### 📊 Status Dashboard
- **At-a-glance overview** (hardware, environment, models)
- **JSON output** for scripting and automation
- **Health checks** (devices, paths, configurations)

```bash
$ tt status --json | jq '.hardware'

{
  "count": 1,
  "primary_type": "N150",
  "devices": [
    {
      "type": "N150",
      "index": 0,
      "temperature": 35.0,
      "power": 45.0,
      "pci_bus": "0000:01:00.0",
      "firmware": "v1.2.3"
    }
  ]
}
```

### 🎯 Phase 2: Advanced Features (✅ Complete)

#### 🚀 Server Management (✅ Implemented)
- **Start vLLM servers** with auto-detected hardware config
- **Process management** (start, stop, status with CPU/memory)
- **Smart defaults** (optimal context length, tensor parallelism, batch size)
- **Background mode** (detached servers with log files)
- **Multi-device support** (auto-configures tensor parallelism)

```bash
$ tt serve start Qwen3-0.6B --detach

Hardware: 1x N150

Starting vLLM server:
  Model: Qwen3-0.6B
  Port: 8000
  max-model-len: 2048
  tensor-parallel-size: 1
  max-num-seqs: 32
  MESH_DEVICE: N150

🚀 Starting server in background...
✓ Server started successfully
  PID: 12345
  Log: ~/.tt/servers/logs/qwen3-0.6b.log

# Check status
$ tt serve status

Running Servers:

  Qwen3-0.6B
    PID: 12345
    Port: 8000
    CPU: 15.2%
    Memory: 2048 MB

# Stop server
$ tt stop Qwen3-0.6B
```

**See**: [COOKBOOK.md](COOKBOOK.md) recipes 19-28 for server management workflows.

#### 📥 Model Downloads (✅ Implemented)
- **HuggingFace integration** using `huggingface_hub`
- **Progress tracking** during downloads
- **Automatic validation** after download
- **Resume support** for interrupted downloads
- **Gated model support** (Llama, etc. with HF token)

```bash
$ tt model get Qwen/Qwen3-0.6B

📥 Downloading from HuggingFace Hub: Qwen/Qwen3-0.6B
   Destination: /home/user/models/Qwen3-0.6B

[Download progress...]

✓ Download complete: /home/user/models/Qwen3-0.6B

Validating model files...
✓ Model validation passed

# Download gated models
$ tt model get meta-llama/Llama-3.1-8B-Instruct --token hf_your_token

# Force re-download
$ tt model get Qwen/Qwen3-0.6B --force
```

**See**: [COOKBOOK.md](COOKBOOK.md) recipes 13-18 for model download workflows.

#### 🔄 Workflow Automation (Coming Soon)
- **Pre-defined workflows** for common tasks
- **Custom workflow support** (YAML config)
- **Integration with tt-inference-server**

```bash
# Future commands
tt workflow run training           # Run training workflow
tt workflow run inference          # Run inference workflow
tt workflow list                   # List available workflows
```

---

## Documentation

- **[COOKBOOK.md](COOKBOOK.md)** - 38 recipes for common workflows and troubleshooting
- **[QUICKSTART.md](QUICKSTART.md)** - Installation and first steps
- **[TESTING.md](TESTING.md)** - Testing guide (TDD workflow, 76 tests)
- **[CLAUDE.md](CLAUDE.md)** - AI assistant guide (architecture, patterns, decisions)
- **[STATUS.md](STATUS.md)** - Project status, metrics, and roadmap
- **[TT_CLI_VISION.md](TT_CLI_VISION.md)** - Comprehensive vision document

---

## Command Reference

### Status
```bash
tt status                     # Show everything (hardware, env, models)
tt status --json              # Machine-readable output
```

### Environment Management
```bash
tt env list                   # List all virtual environments
tt env use <name>             # Switch environment (metal, vllm, forge, xla)
tt env check                  # Validate current environment
tt env fix                    # Auto-fix common issues (shows what would be fixed)
eval "$(tt env fix --export)" # Apply fixes to current shell
```

### Device Management
```bash
tt device info                # Show hardware information
tt device info --json         # JSON output
tt device test                # Test TTNN device connectivity
```

### Model Management
```bash
tt model get <repo>           # Download model from HuggingFace
tt model download <repo>      # Alias for get
tt model get <repo> --token <token>  # Download gated model
tt model get <repo> --force   # Force re-download
tt model list                 # List installed models
tt model info <name>          # Show model details
tt model check <name>         # Validate model (config, weights, tokenizer)
```

### Server Management
```bash
# Start vLLM servers
tt serve start <model>                    # Start vLLM server (foreground)
tt serve start <model> --detach           # Start in background
tt serve start <model> --port 8001        # Custom port
tt serve start <model> --max-model-len 4096  # Override context length
tt serve start <model> --tensor-parallel 2   # Override parallelism

# Manage running servers
tt serve status                           # Show all running servers
tt serve status --json                    # JSON output with CPU/memory
tt stop <model>                           # Stop specific server
tt restart <model>                        # Restart server
```

### Workflow Automation
```bash
# List available workflows
tt workflow list                          # Show all workflows
tt workflow info setup                    # Show workflow details

# Run workflows
tt workflow run setup                     # Development environment setup
tt workflow run test-model --model Qwen3-0.6B  # Complete model testing
tt workflow run test-model --model Qwen3-0.6B --quick  # Quick validation only
tt workflow run benchmark --model <name>  # Performance benchmarks
tt workflow run eval --model <name> --eval-suite mmlu  # Run evaluations

# Dry run mode (preview without executing)
tt workflow run setup --dry-run           # Show what would be done
```

### Configuration Management
```bash
# View configuration
tt config list                            # Show all config values
tt config list --json                     # JSON output
tt config get models_dir                  # Get specific value
tt config get server.default_port         # Get nested value

# Update configuration
tt config set models_dir ~/my-models      # Set custom models directory
tt config set server.default_port 9000    # Set default port
tt config reset                           # Reset to defaults
```

---

## Architecture

### Project Structure

```
tt-cli/
├── tt/
│   ├── core/
│   │   └── cli.py           # Main CLI entry point, argument parsing
│   ├── commands/
│   │   ├── status.py        # tt status
│   │   ├── env.py           # tt env *
│   │   ├── device.py        # tt device *
│   │   ├── model.py         # tt model *
│   │   └── serve.py         # tt serve * (Phase 2)
│   ├── integrations/
│   │   └── (future)         # tt-jukebox, tt-inference-server
│   └── utils/
│       ├── hardware.py      # Hardware detection (tt-smi wrapper)
│       └── envmanager.py    # Environment management (hybrid uv/venv)
├── tests/
│   ├── conftest.py          # Shared fixtures (15+ fixtures)
│   ├── unit/                # Unit tests (50 tests)
│   └── integration/         # Integration tests (14 tests)
└── setup.py                 # Package metadata
```

### Design Decisions

**Why Python?**
- Fast iteration (built 1,500 lines in ~2 hours)
- Direct API access (import ttnn, torch, etc.)
- I/O-bound workloads (subprocess, file reads)
- Team familiarity (ML/AI lingua franca)

**Why Zero Dependencies?**
- Works on any Python 3.9+ system
- No dependency hell
- Fast cold start
- Maximum reliability

**Why Hybrid uv/venv?**
- Speed when available (10-100x faster)
- Portability when not (built-in venv fallback)
- Zero user configuration
- Proven in production (tt-inference-server)

---

## Development

### Test-Driven Development

**We practice TDD for all features.**

Test suite includes:
- **64 tests** (100% passing)
- **Unit tests** - `tests/unit/` for hardware, envmanager
- **Integration tests** - `tests/integration/` for CLI commands
- **Fixtures** - `tests/conftest.py` with shared mocks

```bash
# Install development dependencies
pip install -e .
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=tt --cov-report=html

# Run specific test file
pytest tests/unit/test_hardware.py

# Run tests matching pattern
pytest -k "test_detect_hardware"
```

### Adding New Features

1. **Write tests first** (TDD workflow)
2. **Implement feature** to pass tests
3. **Update cookbook** with usage recipes
4. **Document in README** command reference

See [CLAUDE.md](CLAUDE.md) for detailed development guide.

### Code Quality

```bash
# Format code
black tt/

# Lint code
ruff check tt/ --fix

# Type check (optional)
mypy tt/
```

---

## Building on tt-jukebox

This CLI builds on [tt-jukebox](https://github.com/tenstorrent/tt-jukebox)'s solid foundation:
- Hardware detection via tt-smi
- Model spec matching (model → hardware compatibility)
- Smart command generation

And extends it to eliminate **all** throwaway scripts:
- Server management (vLLM, inference servers)
- Environment management (auto-conflict resolution)
- Device management (testing, reset, monitoring)
- Model management (download, validate, convert)

---

## Requirements

- **Python 3.9+** (built-in, no external dependencies)
- **Optional:** `uv` for 10-100x faster environment operations
- **Optional:** `tt-smi` for hardware detection
- **Optional:** `textual` + `rich` for TUI interface (Phase 3)

---

## Philosophy

1. **Zero dependencies** - Core CLI uses only Python stdlib
2. **Smart defaults** - Works without configuration
3. **Graceful degradation** - Falls back when optional tools missing
4. **Transparent** - Shows what it's doing (no magic)
5. **Fast iteration** - Built in Python for rapid development
6. **Test-driven** - 100% test coverage for all features
7. **User experience first** - Clear errors, helpful messages

---

## Troubleshooting

### Quick Fixes

**Hardware not detected**:
```bash
# Check tt-smi is installed
which tt-smi
tt-smi -s

# Check PCI devices
lspci | grep -i tenstorrent
```

**Environment issues**:
```bash
# Check for problems
tt env check

# Auto-fix common issues
tt env fix

# Re-activate environment
eval "$(tt env use metal)"
```

**Import errors**:
```bash
# Verify PYTHONPATH
echo $PYTHONPATH

# Test import
python -c "import ttnn; print('✓ TTNN imported')"
```

See [COOKBOOK.md](COOKBOOK.md) for 28 troubleshooting recipes.

---

## Roadmap

### Phase 1: Core CLI ✅ Complete (Jan 2026)
- ✅ Hardware detection and device management
- ✅ Environment management with conflict handling
- ✅ Model management (list, info, validate)
- ✅ Status dashboard with JSON output
- ✅ Test suite (88 tests, 100% passing)
- ✅ Comprehensive documentation

### Phase 2: Advanced Features ✅ Complete (Jan 2026)
- ✅ **Server management** (vLLM start/stop/status with auto-config)
- ✅ **Model downloads** (HuggingFace integration with progress & validation)
- ✅ **88/88 tests passing** with comprehensive coverage
- [ ] Workflow automation (tt-inference-server integration) - moved to Phase 3
- [ ] Configuration file support (~/.ttconfig) - moved to Phase 3

### Phase 3: Workflow Integration & Polish ✅ Complete (Jan 2026)
- ✅ **Workflow automation** (`tt workflow run setup/test-model/benchmark/eval`)
- ✅ **Configuration file support** (`~/.ttconfig` for user preferences)
- ✅ **121/121 tests passing** with comprehensive coverage
- ✅ **TT hardware compatibility** (DeepSeek-R1-Distill-Llama-70B on P300 Blackhole)
- ✅ **COOKBOOK updated** with 52 recipes including 8 workflow examples

### Phase 4: Distribution & Community 📅 Future (Q2 2026)
- [ ] PyPI release (pip install tt-cli)
- [ ] TUI interface (textual + rich)
- [ ] Plugin system for extensibility
- [ ] Bash/Zsh completion
- [ ] Performance optimization (if needed)

---

## Project Metrics

| Metric | Value |
|--------|-------|
| Lines of Code | 3,200+ |
| Tests | 121 (100% passing) |
| Coverage | 90%+ |
| Dependencies | 0 (stdlib only, PyYAML optional) |
| Python Version | 3.9+ |
| Commands | 23 implemented |
| Workflows | 4 (setup, test-model, benchmark, eval) |
| Scripts Eliminated | ~15 scripts (~880 lines) |

---

## Contributing

Contributions welcome! We follow test-driven development:

1. Write tests first
2. Implement feature
3. Update documentation (COOKBOOK.md + README.md)
4. Submit PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Credits

Built with ❤️ by the Tenstorrent community.

Special thanks to [tt-jukebox](https://github.com/tenstorrent/tt-jukebox) for the foundation.

---

<div align="center">

**Stop writing throwaway scripts. Start using `tt`.** 🚀

[Installation](#installation) • [Quick Start](#quick-start) • [Documentation](#documentation)

</div>
# tt-cli
