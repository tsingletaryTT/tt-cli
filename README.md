# tt-cli

**Unified command-line interface for Tenstorrent hardware development**

[![Tests](https://img.shields.io/badge/tests-121%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-90%25+-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](setup.py)

A single CLI tool for managing Tenstorrent hardware, environments, models, and servers.

```bash
# Check system status
tt status

# Switch environments
tt env use metal@v0.66.0-rc7

# Test devices
tt device test

# Start a server
tt serve start llama-3.1-8b

# Use pre-configured stacks
tt stack use llama-3.1-8b-p150x4
```

## Installation

```bash
git clone https://github.com/tenstorrent/tt-cli.git
cd tt-cli
pip install -e .

# Verify
tt --version
tt status
```

## Core Features

### Environment Management
Switch between TT-Metal versions and frameworks with automatic conflict resolution:

```bash
tt env use metal                  # Use active TT-Metal version
tt env use metal@v0.66.0-rc7      # Use specific version
tt env check                      # Validate environment
tt env fix                        # Auto-fix common issues
```

### TT-Metal Version Management
Manage multiple TT-Metal installations side-by-side:

```bash
tt metal checkout --tag v0.66.0-rc7 --set-active
tt metal list
tt metal use v0.66.0-rc7
```

### Stack Management
Pre-configured deployment setups combining Metal version, model, hardware, and server settings:

```bash
tt stack list                     # Show available stacks
tt stack use llama-3.1-8b-p150x4  # Activate complete environment
tt serve start                    # Start server with stack config
```

Default stacks:
- `llama-3.1-8b-p150x4` - Coding-optimized (128K context, data parallel 4x)
- `llama-3.3-70b-p150x4` - Best reasoning (128K context, higher quality)

### Device Management
Hardware info, testing, and firmware updates:

```bash
tt device info                    # Show hardware details
tt device test                    # Test TTNN connectivity
tt firmware current               # Check firmware versions
tt firmware latest --flash        # Update to latest
```

### Server Management
Start and manage vLLM servers with automatic hardware configuration:

```bash
tt serve start Qwen3-0.6B
tt serve start Qwen3-0.6B --detach --port 8000
tt serve status
tt stop Qwen3-0.6B
```

Multi-device deployment (run independent servers on each chip):

```bash
tt serve start Qwen3-0.6B --port 8000 --device-id 0 --detach
tt serve start Qwen3-0.6B --port 8001 --device-id 1 --detach
tt serve start Qwen3-0.6B --port 8002 --device-id 2 --detach
tt serve start Qwen3-0.6B --port 8003 --device-id 3 --detach
```

### Model Management
Download, validate, and manage models:

```bash
tt model get Qwen/Qwen3-0.6B
tt model list
tt model info Qwen3-0.6B
tt model check Qwen3-0.6B
```

### Workflow Automation
Pre-defined workflows for common tasks:

```bash
tt workflow run setup                      # Development environment setup
tt workflow run test-model --model Qwen3-0.6B
tt workflow run benchmark --model Qwen3-0.6B
```

## Documentation

- **[Quick Start](docs/quickstart.md)** - Get up and running
- **[Cookbook](docs/cookbook.md)** - Practical recipes and examples
- **[Development Guide](docs/development.md)** - For contributors
- **[Testing Guide](docs/testing.md)** - TDD workflow
- **[Project Status](docs/status.md)** - Current state and roadmap

## Command Reference

### System Status
```bash
tt status                         # Overview of everything
tt status --json                  # Machine-readable output
```

### Environment & Version Management
```bash
tt env list                       # List environments
tt env use <name>[@version]       # Switch environment
tt env check                      # Validate environment
tt env fix                        # Auto-fix issues

tt metal list                     # Show TT-Metal installations
tt metal checkout --tag <tag>     # Install new version
tt metal use <version>            # Set active version
```

### Stack Management
```bash
tt stack list                     # Show available stacks
tt stack use <name>               # Activate stack
tt stack info <name>              # Show stack details
tt stack create <name>            # Create custom stack
```

### Device Management
```bash
tt device info                    # Hardware information
tt device test                    # Test connectivity
```

### Firmware Management
```bash
tt firmware current               # Show current versions
tt firmware list                  # List available versions
tt firmware latest --flash        # Update to latest
```

### Model Management
```bash
tt model get <repo>               # Download from HuggingFace
tt model list                     # List installed models
tt model info <name>              # Show details
tt model check <name>             # Validate files
```

### Server Management
```bash
tt serve start <model>            # Start vLLM server
tt serve start <model> --detach   # Background mode
tt serve status                   # Show running servers
tt stop <model>                   # Stop server
```

### Workflows
```bash
tt workflow list                  # Show available workflows
tt workflow run <name>            # Execute workflow
```

### Configuration
```bash
tt config list                    # Show all config values
tt config get <key>               # Get specific value
tt config set <key> <value>       # Update value
```

## Architecture

Built with:
- **Python 3.9+** - No external dependencies for core functionality
- **Hybrid uv/venv** - Fast when available, portable always
- **Test-driven** - 121 tests, 90%+ coverage
- **Zero config** - Smart defaults, auto-detection

Key design principles:
1. Zero dependencies (stdlib only)
2. Smart defaults (auto-detect hardware)
3. Graceful degradation (fallbacks when tools missing)
4. Fast iteration (Python for rapid development)

## Development

```bash
# Install dev dependencies
pip install -e .
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black tt/
ruff check tt/ --fix
```

See [Development Guide](docs/development.md) for detailed information.

## Requirements

- **Python 3.9+**
- **Optional**: `uv` for 10-100x faster environment operations
- **Optional**: `tt-smi` for hardware detection
- **Optional**: `tt-flash` for firmware updates

## Project Status

**Current**: Phase 3 Complete (121/121 tests passing)

- ✅ Phase 1: Core CLI (hardware, environment, models, devices)
- ✅ Phase 2: Advanced features (server management, model downloads)
- ✅ Phase 3: Workflow automation & configuration
- 📅 Phase 4: Distribution & community (PyPI, TUI, plugins)

See [Project Status](docs/status.md) for detailed roadmap.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Built by the Tenstorrent community.

Foundation provided by [tt-jukebox](https://github.com/tenstorrent/tt-jukebox).
