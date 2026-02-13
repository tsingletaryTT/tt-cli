# tt-cli Development Guide

**Architecture, patterns, and best practices for contributors**

This guide helps contributors understand the project context, design decisions, development workflow, and coding patterns to maintain consistency when working on tt-cli.

---

## Table of Contents

1. [Project Context](#project-context)
2. [Architecture Decisions](#architecture-decisions)
3. [Development Workflow](#development-workflow)
4. [Code Patterns](#code-patterns)
5. [Testing Strategy](#testing-strategy)
6. [Common Tasks](#common-tasks)
7. [Pitfalls to Avoid](#pitfalls-to-avoid)
8. [Project Status](#project-status)

---

## Project Context

### What tt-cli Does

**tt-cli** is a unified command-line tool for Tenstorrent hardware development:

```bash
# System status at a glance
tt status

# Environment management with version control
tt env use metal@v0.66.0-rc7

# Hardware testing and management
tt device test

# Server deployment with smart defaults
tt serve start llama-3.1-8b

# Pre-configured deployment stacks
tt stack use llama-3.1-8b-p150x4
```

### Project Goals

1. **Unified interface** - Single tool for hardware, environments, models, and servers
2. **Smart defaults** - Auto-detect hardware, set optimal parameters
3. **Zero configuration** - Work out of the box with sensible defaults
4. **Version management** - Multiple TT-Metal versions side-by-side
5. **Graceful degradation** - Fall back when optional tools unavailable
6. **Fast iteration** - Python for rapid development

### Relationship to tt-jukebox

**tt-jukebox** (1,442 lines) is the foundation:
- Hardware detection via tt-smi
- Model spec matching (model → hardware compatibility)
- Smart command generation

**tt-cli** extends this to cover ALL common workflows:
- Server management (vLLM, inference servers)
- Environment management (tt-metal, TT-Forge, TT-XLA, vLLM)
- Device management (testing, reset, info)
- Model management (download, validate, list)
- Status dashboard (system overview)

---

## Architecture Decisions

### Why Python, Not Rust?

**Decision**: Build in Python first, consider Rust later if needed.

**Rationale**:
1. **Development speed**: Built 1,500 lines functional code in ~2 hours vs weeks in Rust
2. **I/O bound**: Most operations are I/O-bound (tt-smi calls, file reads, subprocess)
3. **Direct API access**: Can import tt-metal, ttnn directly
4. **100ms startup acceptable**: Humans won't notice; can optimize later if needed
5. **Team familiarity**: Python is lingua franca of ML/AI development

**When to reconsider**: If startup time becomes a user complaint or performance bottleneck.

### Why Zero Dependencies?

**Decision**: Core CLI uses only Python stdlib (no external packages).

**Rationale**:
1. **Portability**: Works on any Python 3.9+ system
2. **Installation simplicity**: `pip install tt-cli` with no dependency hell
3. **Cold start speed**: No import overhead from heavy packages
4. **Reliability**: Fewer moving parts = fewer breakage points

**Optional dependencies**:
- `uv` - For 10-100x faster venv operations (graceful fallback to `venv`)
- `textual` + `rich` - For TUI interface (future Phase 2+)

### Why Hybrid uv/venv Approach?

**Decision**: Use `uv` when available, fall back to `venv` when not.

**Rationale**:
1. **Speed**: uv is 10-100x faster than venv for common operations
2. **Portability**: Not everyone has uv installed; venv is built-in
3. **Proven pattern**: tt-inference-server already uses uv successfully
4. **Zero user configuration**: CLI auto-detects and uses best available tool

**Implementation**: `tt/utils/envmanager.py::has_uv()` checks for uv, all functions fall back gracefully.

### Why Flat Command Structure?

**Decision**: `tt <category> <command>` not `tt-<category>-<command>`.

**Rationale**:
1. **Discoverability**: `tt --help` shows all categories
2. **Consistency**: All commands follow same pattern
3. **Namespace**: Avoids polluting user's PATH with many executables
4. **Future extensibility**: Easy to add plugins/subcommands later

**Examples**:
```bash
tt env use metal        # Not: tt-env-use metal
tt device test          # Not: tt-device-test
tt status               # Not: tt-status
```

---

## Development Workflow

### Test-Driven Development (TDD)

**We practice TDD for all features.** This is non-negotiable.

#### TDD Workflow

1. **Write test first** - Define expected behavior
2. **Run test (should fail)** - Verify test works
3. **Implement feature** - Make test pass
4. **Run test (should pass)** - Verify implementation
5. **Refactor** - Improve code while keeping tests green
6. **Update cookbook** - Add usage recipe to docs/cookbook.md
7. **Document** - Update README.md command reference

#### Example: Adding a New Command

```python
# Step 1: Write test first
# tests/integration/test_commands.py
def test_model_download(self, tmp_path, capsys):
    """Test model download command."""
    args = argparse.Namespace(name='Qwen3-0.6B', force=False)

    result = model.download(args)

    assert result == 0
    out, err = capsys.readouterr()
    assert 'Downloading Qwen3-0.6B' in out
    assert 'Download complete' in out

# Step 2: Run test (should fail)
# pytest tests/integration/test_commands.py::test_model_download
# FAILED - AttributeError: module 'tt.commands.model' has no attribute 'download'

# Step 3: Implement feature
# tt/commands/model.py
def download(args):
    """Download model from HuggingFace."""
    print(f"Downloading {args.name}...")
    # ... implementation ...
    print("Download complete")
    return 0

# Step 4: Run test (should pass)
# pytest tests/integration/test_commands.py::test_model_download
# PASSED

# Step 5: Refactor (if needed)
# Step 6: Update cookbook (see docs/cookbook.md)
# Step 7: Document (see README.md)
```

### Git Workflow

**Branch naming**:
- `feature/<name>` - New features
- `fix/<name>` - Bug fixes
- `test/<name>` - Test improvements
- `docs/<name>` - Documentation only

**Commit messages**:
```
feat: add model download command

- Implement HuggingFace model download
- Add progress bar with rich
- Add force flag to overwrite existing
- Tests: 3 new integration tests
- Cookbook: Recipe 29 (downloading models)
```

**Before committing**:
```bash
# Run tests
pytest

# Format code
black tt/
ruff check tt/ --fix

# Check types (if using mypy)
mypy tt/
```

---

## Code Patterns

### Command Structure

All commands follow this pattern:

```python
# tt/commands/<category>.py
import argparse
from typing import Optional

def command_name(args: argparse.Namespace) -> int:
    """
    Brief description of what command does.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        # 1. Validate inputs
        if not validate_something(args.param):
            print(f"❌ Error: {error_message}")
            return 1

        # 2. Do the work
        result = do_the_actual_work(args)

        # 3. Report results
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_human_readable(result)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
```

**Key patterns**:
- Return exit codes (0 = success, non-zero = error)
- Support both human-readable and JSON output
- Use emoji sparingly (only for status indicators: ✓, ❌, ⚠️)
- Print to stdout (not logging for user-facing output)
- Handle errors gracefully, show helpful messages

### Hardware Detection

Always use `tt.utils.hardware` module:

```python
from tt.utils import hardware

# Detect hardware
hw = hardware.detect_hardware()
if not hw:
    print("❌ No hardware detected")
    return 1

# Get MESH_DEVICE value
mesh_device = hardware.get_mesh_device()
print(f"MESH_DEVICE={mesh_device}")

# Check architecture
if hardware.is_blackhole():
    print("TT_METAL_ARCH_NAME=blackhole")
```

**Available functions**:
- `has_tt_smi()` - Check if tt-smi is available
- `detect_hardware()` - Parse tt-smi JSON output
- `get_mesh_device()` - Determine MESH_DEVICE value
- `get_arch_name()` - Determine TT_METAL_ARCH_NAME
- `is_wormhole()`, `is_blackhole()` - Architecture checks
- `format_hardware_summary()` - Human-readable output

### Environment Management

Always use `tt.utils.envmanager` module:

```python
from tt.utils import envmanager

# Check if uv is available
if envmanager.has_uv():
    print("Using uv for fast environment operations")

# Create virtual environment (hybrid approach)
envmanager.create_venv(path, python_version="3.10")

# Install packages (hybrid approach)
envmanager.install_packages(path, ['numpy', 'torch'])

# Activate environment
env_vars = envmanager.activate_environment('metal')
for key, value in env_vars.items():
    print(f"export {key}={value}")

# Check environment
status = envmanager.check_environment()
if status['status'] == 'error':
    print("Issues found:", status['issues'])

# Fix environment
fixes = envmanager.fix_environment()
print(f"Applied {len(fixes)} fixes")
```

**Available functions**:
- `has_uv()` - Check for uv availability
- `create_venv()` - Create venv (uv or venv)
- `install_packages()` - Install packages (uv pip or pip)
- `activate_environment()` - Set env vars for tt-metal/forge/xla/vllm
- `check_environment()` - Validate current environment
- `fix_environment()` - Auto-fix common issues
- `get_venv_python_version()` - Get Python version from venv

### Firmware Management

Always use `tt.utils.firmware` module:

```python
from tt.utils import firmware

# Get current firmware versions
current = firmware.get_current_firmware()
if current:
    print(f"Primary version: {current['primary_version']}")

# List available firmware from GitHub
available = firmware.list_available_firmware()
for fw in available:
    print(f"{fw['version']} - {fw['date']}")

# Get latest firmware
latest = firmware.get_latest_firmware()
print(f"Latest: {latest['version']}")

# Check firmware compatibility
compat = firmware.get_firmware_compatibility("19.4.2", "P300C")
if not compat['compatible']:
    print(f"Warning: {compat['warning']}")

# Get recommended firmware for hardware
recommended = firmware.get_recommended_firmware("P300C")
for fw in recommended:
    print(f"Recommended: {fw['version']}")

# Download firmware
bundle_path = firmware.download_firmware("19.4.2", show_progress=True)
print(f"Downloaded: {bundle_path}")

# Flash firmware (requires tt-flash)
if firmware.has_tt_flash():
    exit_code = firmware.flash_firmware(bundle_path)
    if exit_code == 0:
        print("Flash successful")

# Verify firmware
exit_code = firmware.verify_firmware(bundle_path)
```

**Available functions**:
- `parse_firmware_version(hex)` - Convert hex to semantic version (0x13040200 → "19.4.2.0")
- `format_firmware_version(str)` - Format for display ("19.4.2.0" → "19.4.2")
- `get_current_firmware()` - Get firmware from devices via tt-smi
- `list_available_firmware()` - Fetch releases from GitHub API
- `get_latest_firmware()` - Get latest release
- `compare_versions(v1, v2)` - Compare semantic versions (-1/0/1)
- `get_firmware_compatibility(version, hw_type)` - Check hardware compatibility (advisory)
- `get_recommended_firmware(hw_type)` - Filter firmware by hardware compatibility
- `download_firmware(version, cache_dir)` - Download firmware bundle
- `has_tt_flash()` - Check for tt-flash availability
- `flash_firmware(bundle_path, ...)` - Flash firmware with tt-flash
- `verify_firmware(bundle_path)` - Verify firmware with tt-flash

**Compatibility recommendations**:
```python
FIRMWARE_RECOMMENDATIONS = {
    # Blackhole devices (P-series) - recommend 19.4.x+
    'P100': {'min_version': '19.4.0', 'arch': 'blackhole'},
    'P150': {'min_version': '19.4.0', 'arch': 'blackhole'},
    'P300C': {'min_version': '19.4.0', 'arch': 'blackhole'},

    # Wormhole devices (N-series) - recommend 19.x+
    'N150': {'min_version': '19.0.0', 'arch': 'wormhole'},
    'N300': {'min_version': '19.0.0', 'arch': 'wormhole'},
}
```

**Important**: Recommendations are advisory only. The CLI never blocks firmware operations - it shows warnings but always allows developers to proceed. This respects developer expertise while providing helpful guidance.

### TT-Metal Installation Management

Always use `tt.utils.metal` module for managing multiple TT-Metal installations:

```python
from tt.utils import metal
from pathlib import Path

# Get all registered installations
installations = metal.get_metal_installations()
for version, info in installations.items():
    print(f"{version}: {info['path']}")

# Get active version
active = metal.get_active_metal()
print(f"Active version: {active}")

# Set active version
metal.set_active_metal("v0.66.0-rc7")

# Register a new installation
metal.register_metal_installation(
    version="v0.66.0-rc7",
    path=Path.home() / "tt-metal",
    tag="v0.66.0-rc7",
    python_env=Path.home() / "tt-metal/python_env",
    vllm_env=Path.home() / "tt-metal/build/python_env_vllm",
)

# Validate installation
validation = metal.validate_metal_installation(Path.home() / "tt-metal")
if not validation['valid']:
    print(f"Issues: {validation['issues']}")

# Checkout and build new version
exit_code = metal.checkout_metal(
    tag="v0.66.0-rc7",
    path=Path.home() / "tt-metal-versions/v0.66.0-rc7",
    force_update_submodules=True,
)

# Build installation
exit_code = metal.build_metal(
    metal_path=Path.home() / "tt-metal-versions/v0.66.0-rc7",
    build_tt_train=True,
    clean=False,
)

# Create environments
metal.create_python_env(metal_path, python_version="3.12")
metal.create_vllm_env(metal_path, python_version="3.12")
metal.install_vllm_dependencies(metal_path)
```

**Available functions**:
- `get_metal_installations()` - Get all registered installations from config
- `get_active_metal()` - Get currently active version
- `set_active_metal(version)` - Set active version
- `register_metal_installation(...)` - Register installation in config
- `unregister_metal_installation(version)` - Remove from config
- `checkout_metal(tag, path, ...)` - Clone and checkout specific version
- `install_dependencies(path)` - Run install_dependencies.sh
- `build_metal(path, ...)` - Build with cmake
- `create_python_env(path, ...)` - Create python_env
- `create_vllm_env(path, ...)` - Create vLLM environment
- `install_vllm_dependencies(path)` - Install TT llama-models, etc.
- `validate_metal_installation(path)` - Check installation validity
- `parse_version_spec(spec)` - Parse `env@version` syntax

**Version-specific environment activation**:
```python
from tt.utils import envmanager

# Activate specific version
env_vars = envmanager.activate_metal_version(Path.home() / "tt-metal")

# This is used by: tt env use metal@v0.66.0-rc7
```

**Integration with env commands**:
- `tt env use metal` - Use active metal version
- `tt env use metal@v0.66.0-rc7` - Use specific version
- Active version is stored in `~/.ttconfig` under `metal.active`
- Installations are tracked in `~/.ttconfig` under `metal.installations`

**Config structure** (`~/.ttconfig`):
```yaml
metal:
  active: v0.66.0-rc7
  installations:
    v0.66.0-rc7:
      path: /home/user/tt-metal
      tag: v0.66.0-rc7
      python_env: /home/user/tt-metal/python_env
      vllm_env: /home/user/tt-metal/build/python_env_vllm
      created: '2026-02-03T23:39:47Z'
```

**Future: Stack management**:
This foundation enables future tt-jukebox-style stack management:
```yaml
stacks:
  qwen-dev:
    metal: v0.66.0-rc7
    model: Qwen3-0.6B
    hardware: P300C
    config:
      max_model_len: 2048
      tensor_parallel: 2
```

Commands like `tt serve start qwen-dev` would automatically:
1. Activate metal v0.66.0-rc7
2. Load Qwen3-0.6B model
3. Configure for P300C hardware
4. Start vLLM server with specified config

### Error Handling

**Pattern**: Fail gracefully with helpful error messages.

```python
def some_command(args):
    """Command that might fail."""
    # Check prerequisites
    if not has_required_tool():
        print("❌ Error: Required tool not found")
        print("   Install with: sudo apt install tool-name")
        return 1

    # Try operation
    try:
        result = do_risky_operation()
    except FileNotFoundError as e:
        print(f"❌ Error: File not found: {e.filename}")
        print("   Check that path exists and try again")
        return 1
    except PermissionError:
        print("❌ Error: Permission denied")
        print("   Run with sudo or fix permissions")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("   Please report this issue with the full error message")
        return 1

    print("✓ Success")
    return 0
```

**Guidelines**:
- Catch specific exceptions first, generic Exception last
- Show user-friendly error messages
- Suggest fixes when possible
- Return appropriate exit codes

### JSON Output

**Pattern**: Support `--json` flag for machine-readable output.

```python
def info_command(args):
    """Show information (supports JSON output)."""
    # Collect data
    data = {
        'version': get_version(),
        'hardware': detect_hardware(),
        'environment': get_env_vars(),
    }

    # Output
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(format_human_readable(data))

    return 0
```

**JSON guidelines**:
- Use consistent key names (snake_case)
- Include all data in JSON mode (no truncation)
- Make JSON parseable even on error (return error object)
- Test JSON output is valid: `tt status --json | jq`

---

## Testing Strategy

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (15+ fixtures)
├── unit/                    # Unit tests (50 tests)
│   ├── test_hardware.py     # Hardware detection logic
│   └── test_envmanager.py   # Environment management
└── integration/             # Integration tests (14 tests)
    └── test_commands.py     # End-to-end command testing
```

### Writing Unit Tests

**Test one function/method in isolation**:

```python
# tests/unit/test_newfeature.py
import pytest
from unittest.mock import Mock, patch
from tt.utils import newfeature

class TestNewFeature:
    """Test new feature functionality."""

    def test_basic_case(self):
        """Test basic functionality."""
        result = newfeature.do_something(input_value)
        assert result == expected_value

    def test_edge_case(self):
        """Test edge case handling."""
        result = newfeature.do_something(edge_case_input)
        assert result == edge_case_output

    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError, match="Invalid input"):
            newfeature.do_something(invalid_input)

    def test_with_mocked_external_call(self):
        """Test with external dependency mocked."""
        with patch('tt.utils.newfeature.external_call') as mock_call:
            mock_call.return_value = Mock(status='success')
            result = newfeature.do_something()
            assert result.status == 'success'
            mock_call.assert_called_once()
```

### Writing Integration Tests

**Test complete command flow**:

```python
# tests/integration/test_commands.py
class TestNewCommand:
    """Integration tests for new command."""

    def test_command_success(self, capsys):
        """Test successful command execution."""
        args = argparse.Namespace(param='value', json=False)

        result = command.new_command(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'Success message' in out

    def test_command_with_json_output(self, capsys):
        """Test command with JSON output."""
        args = argparse.Namespace(param='value', json=True)

        result = command.new_command(args)

        assert result == 0
        out, err = capsys.readouterr()
        data = json.loads(out)
        assert data['key'] == 'value'

    def test_command_error_handling(self, capsys):
        """Test command error handling."""
        args = argparse.Namespace(param='invalid', json=False)

        result = command.new_command(args)

        assert result != 0
        out, err = capsys.readouterr()
        assert 'Error' in out
```

### Using Fixtures

**Common fixtures in conftest.py**:

```python
# Use temp_home for file operations
def test_with_temp_home(temp_home):
    config_dir = temp_home / ".config"
    config_dir.mkdir()
    # ... test code using temp_home ...

# Use clean_env to start with clean environment
def test_with_clean_env(clean_env):
    # No TT_* variables set
    assert 'TT_METAL_HOME' not in os.environ

# Use mock hardware fixtures
def test_with_n150(mock_hardware_n150):
    hw = mock_hardware_n150
    assert hw['primary_type'] == 'N150'
    assert hw['count'] == 1

# Use mock tool availability
def test_with_uv(mock_uv_available):
    assert envmanager.has_uv() is True
```

**Creating new fixtures**:

```python
# tests/conftest.py
@pytest.fixture
def mock_new_thing(monkeypatch):
    """Mock new external dependency."""
    def mock_call(*args, **kwargs):
        return expected_result

    monkeypatch.setattr('module.function', mock_call)
    return expected_result
```

### Test Coverage Goals

- **Current**: 64 tests, 100% passing
- **Target**: 90%+ code coverage
- **Focus**: All command paths, error handling, edge cases

```bash
# Check coverage
pytest --cov=tt --cov-report=term-missing

# Generate HTML report
pytest --cov=tt --cov-report=html
open htmlcov/index.html
```

---

## Common Tasks

### Adding a New Command

**Example**: Adding `tt model download <name>`

1. **Write test first** (`tests/integration/test_commands.py`):
```python
def test_model_download(self, tmp_path, capsys):
    args = argparse.Namespace(name='Qwen3-0.6B', force=False)
    result = model.download(args)
    assert result == 0
```

2. **Implement command** (`tt/commands/model.py`):
```python
def download(args):
    """Download model from HuggingFace."""
    # Implementation
    return 0
```

3. **Register command** (`tt/core/cli.py`):
```python
# In model subparser
download_parser = model_subparsers.add_parser('download', help='Download model')
download_parser.add_argument('name', help='Model name')
download_parser.set_defaults(func=model.download)
```

4. **Update cookbook** (`docs/cookbook.md`):
```markdown
### Recipe 30: Downloading Models

**Use case**: Download model from HuggingFace Hub.

\`\`\`bash
tt model download Qwen3-0.6B
\`\`\`
```

5. **Update README** (`README.md`):
```markdown
### Model Management
\`\`\`bash
tt model download <name>      # Download from HuggingFace
\`\`\`
```

### Adding Hardware Support

**Example**: Adding support for new device type (P150)

1. **Update hardware detection** (`tt/utils/hardware.py`):
```python
# Add to DEVICE_TYPE_MAP
DEVICE_TYPE_MAP = {
    'n150': 'N150',
    'n300': 'N300',
    'p100': 'P100',
    'p150': 'P150',  # NEW
}

# Update get_mesh_device if needed
def get_mesh_device():
    # ... existing logic ...
    if device_type == 'P150':
        return 'P150'
```

2. **Write tests** (`tests/unit/test_hardware.py`):
```python
def test_detect_hardware_p150(self):
    mock_output = {'devices': [{'board_type': 'p150', ...}]}
    # ... test implementation ...
```

3. **Update documentation** (all mentions of hardware types)

### Adding Environment Support

**Example**: Adding TT-Quantum environment

1. **Define environment** (`tt/utils/envmanager.py`):
```python
ENVIRONMENTS = {
    # ... existing ...
    'quantum': {
        'name': 'TT-Quantum',
        'venv_path': '~/tt-quantum-venv',
        'vars': {
            'PYTHONPATH': '~/tt-quantum',
            'TT_QUANTUM_HOME': '~/tt-quantum',
        },
        'unset': [],  # Variables to unset
        'description': 'TT-Quantum experimental framework',
    },
}
```

2. **Write tests** (`tests/unit/test_envmanager.py`):
```python
def test_activate_quantum_environment(self, temp_home, clean_env):
    result = envmanager.activate_environment('quantum')
    assert 'TT_QUANTUM_HOME' in result
```

3. **Update cookbook** with usage recipes

---

## Pitfalls to Avoid

### ❌ Don't Mock What You Own

**Bad**:
```python
# Mocking your own function in same module
with patch('tt.commands.status.get_hardware'):
    status.status(args)
```

**Good**:
```python
# Mock external dependencies only
with patch('tt.utils.hardware.detect_hardware'):
    status.status(args)
```

**Why**: You want to test your code, not mocks. Only mock external boundaries.

### ❌ Don't Use Subprocess for File Operations

**Bad**:
```python
subprocess.run('cat file.txt', shell=True, capture_output=True)
```

**Good**:
```python
with open('file.txt', 'r') as f:
    content = f.read()
```

**Why**: Subprocess is slower, less portable, harder to test. Use Python stdlib.

### ❌ Don't Hard-Code Paths

**Bad**:
```python
TT_METAL_HOME = '/home/user/tt-metal'
```

**Good**:
```python
TT_METAL_HOME = os.path.expanduser('~/tt-metal')
```

**Why**: Paths are system-specific. Always use `expanduser()` and `Path()`.

### ❌ Don't Ignore Return Codes

**Bad**:
```python
def command(args):
    do_something()
    # No return value
```

**Good**:
```python
def command(args):
    try:
        do_something()
        return 0
    except Exception:
        return 1
```

**Why**: Commands need exit codes for scripting and automation.

### ❌ Don't Print Debug Info in Production

**Bad**:
```python
print(f"DEBUG: Processing {item}")
```

**Good**:
```python
import logging
logger.debug(f"Processing {item}")
```

**Why**: Debug output pollutes user experience. Use logging with levels.

### ❌ Don't Catch Exception Without Re-raising

**Bad**:
```python
try:
    risky_operation()
except Exception:
    pass  # Silent failure
```

**Good**:
```python
try:
    risky_operation()
except SpecificError as e:
    print(f"❌ Error: {e}")
    return 1
```

**Why**: Silent failures are impossible to debug. Always handle or re-raise.

### ❌ Don't Test Implementation Details

**Bad**:
```python
def test_internal_helper():
    result = module._private_helper_function()
    assert result == expected
```

**Good**:
```python
def test_public_api():
    result = module.public_function()
    assert result == expected
```

**Why**: Tests should validate behavior, not implementation. Internal refactoring shouldn't break tests.

### ❌ Don't Use Aggressive Timeouts for Model Loading

**Bad**:
```python
# Kill server if not ready in 2 minutes
timeout = 120
start = time.time()
while time.time() - start < timeout:
    if server_ready():
        break
    time.sleep(5)
else:
    kill_server()  # ❌ Prematurely kills during cache generation
    raise TimeoutError("Server not ready")
```

**Good**:
```python
# Monitor progress, be patient with model loading
while True:
    if server_ready():
        break

    # Check if process is alive
    if not is_process_alive(pid):
        raise RuntimeError("Server process died")

    # Check for log progress (file growing = still working)
    if log_file_growing():
        print("📝 Model still loading (cache generation in progress)...")

    time.sleep(60)  # Check every minute, but don't timeout
```

**Why**: **Timeouts won't help us much** for model loading. Different models have vastly different initialization times:

- **Llama models**: ~2-3 minutes (faster cache generation)
- **Qwen models**: ~6 minutes (slower cache generation, ~2s per layer × 36 layers)
- **Larger models**: Could take 10-15+ minutes

**What happens during "slow" loading**:
1. Model downloads weights from HuggingFace (if not cached)
2. **Cache generation**: Converts weights to P300-optimized tensor format
   - This is the longest phase
   - Progress indicator: "Generating cache for model_cache/.../layer.X"
   - Each layer takes ~1-3 seconds
   - 36 layers × 2s = ~5 minutes for Qwen3-8B
3. Warmup/compilation: Model traces through different sequence lengths
4. Server ready

**Real example from Qwen3-8B testing (2026-01-13)**:
- Started: 19:37:06
- Cache generation: 19:37:06 - 19:37:48 (~5 minutes for 36 layers)
- Warmup: 19:37:48 - 19:38:37 (~1 minute)
- Server ready: 19:38:37
- **Total: 6 minutes** (would have been killed by 2-minute timeout!)

**Monitoring approach**:
- Check process is alive (not crashed)
- Monitor log file growth (proves progress)
- Look for "Server is responding" on API port
- Check for actual errors vs. normal slowness
- Use UNIX tools: `ps`, `tail -f`, `wc -l`, `curl`

**Key insight**: If the log file is growing and the process is alive, **be patient**. The model is loading normally, even if it takes 10+ minutes.

---

## Project Status

### Phase 1: Core CLI (✅ Complete)

**Implemented**:
- ✅ Hardware detection (`tt device info`, `tt device test`)
- ✅ Environment management (`tt env use/list/check/fix`)
- ✅ **TT-Metal installation management** (`tt metal checkout/list/use/info/remove/build/setup`) - **NEW**
- ✅ Model management (`tt model list/info/check`)
- ✅ Firmware management (`tt firmware list/current/download/flash/verify/latest`)
- ✅ Status dashboard (`tt status`)
- ✅ Test suite (122 tests, 119 passing, 3 pre-existing failures)
- ✅ Documentation (COOKBOOK, TESTING, README, CLAUDE)

**Metrics**:
- 3,000+ lines of Python code
- 122 tests
- 0 external dependencies (stdlib only)
- 6 command categories
- 25 commands implemented

**Recent additions (2026-02-03)**:
- ✅ **TT-Metal installation management** - Complete version management system
  - `tt/utils/metal.py` - Metal installation utilities (500+ lines)
  - `tt/commands/metal.py` - Metal command handlers (600+ lines)
  - Version-specific environment activation: `tt env use metal@v0.66.0-rc7`
  - Installation registry in config: `~/.ttconfig`
  - Full workflow: checkout → build → setup → use
  - Foundation for future tt-jukebox-style stack management

**Previous additions (2026-01-30)**:
- ✅ Firmware utility module (`tt/utils/firmware.py`) - 650+ lines
- ✅ Firmware commands (`tt/commands/firmware.py`) - 500+ lines
- ✅ 42 unit tests for firmware utilities
- ✅ 16 integration tests for firmware commands
- ✅ Hardware-aware firmware recommendations (advisory, never blocking)
- ✅ GitHub API integration for firmware releases
- ✅ tt-flash wrapper for device flashing
- ✅ Comprehensive firmware recipes in COOKBOOK.md

### Phase 2: Advanced Features (🚧 In Progress)

**Planned**:
- [ ] Server management (`tt serve`, `tt stop`, `tt restart`, `tt logs`)
- [ ] Model downloads (`tt model get`, `tt model convert`)
- [ ] Workflow automation (`tt workflow run`, `tt workflow list`)
- [ ] Integration with tt-jukebox for server specs
- [ ] Configuration file support (`~/.ttconfig`)

**Priority order**:
1. Server management (most requested)
2. Model downloads (enables self-service)
3. Workflow automation (reduces manual steps)

### Phase 3: Polish & Release (📅 Future)

**Planned**:
- [ ] PyPI release
- [ ] TUI interface (textual + rich)
- [ ] Plugin system
- [ ] Community contributions
- [ ] Performance optimization (if needed)
- [ ] Bash/Zsh completion

---

## Quick Reference

### File Structure

```
tt-cli/
├── tt/
│   ├── core/
│   │   └── cli.py              # Main CLI entry point
│   ├── commands/
│   │   ├── status.py           # tt status
│   │   ├── env.py              # tt env *
│   │   ├── device.py           # tt device *
│   │   ├── firmware.py         # tt firmware * (NEW)
│   │   ├── model.py            # tt model *
│   │   └── serve.py            # tt serve * (Phase 2)
│   └── utils/
│       ├── hardware.py         # Hardware detection
│       ├── firmware.py         # Firmware management (NEW)
│       └── envmanager.py       # Environment management
├── tests/
│   ├── conftest.py             # Shared fixtures (with firmware fixtures)
│   ├── unit/                   # Unit tests
│   │   ├── test_firmware.py    # Firmware unit tests (NEW)
│   │   └── ...
│   └── integration/            # Integration tests
│       └── test_commands.py    # Includes firmware tests (NEW)
└── docs/
    ├── cookbook.md             # Usage recipes
    ├── testing.md              # Testing guide
    └── development.md          # This file
└── README.md                   # User documentation
```

### Key Commands

```bash
# Development
pytest                          # Run tests
pytest --cov=tt                 # Check coverage
black tt/                       # Format code
ruff check tt/ --fix            # Lint code

# Testing
pytest -k "test_hardware"       # Run specific tests
pytest -v                       # Verbose output
pytest --pdb                    # Debug on failure

# Usage
tt status                       # System overview
tt env use metal                # Switch environment
tt device test                  # Test devices
tt firmware current             # Check firmware versions
tt firmware latest --flash      # Update to latest firmware
tt model list                   # List models
```

### Important Patterns

```python
# Command structure
def command(args: argparse.Namespace) -> int:
    try:
        # Do work
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

# Hardware detection
from tt.utils import hardware
hw = hardware.detect_hardware()

# Environment management
from tt.utils import envmanager
env_vars = envmanager.activate_environment('metal')

# Testing
def test_something(mock_hardware_n150, capsys):
    result = function_under_test()
    assert result == expected
```

---

## Getting Help

- **Project status**: See `docs/status.md`
- **User guide**: See `README.md`
- **Usage recipes**: See `docs/cookbook.md`
- **Testing guide**: See `docs/testing.md`

---

## Remember

1. **TDD always** - Write tests first
2. **Zero dependencies** - Keep core CLI stdlib-only
3. **Graceful degradation** - Fall back when tools missing
4. **User experience first** - Clear errors, helpful messages
5. **Test coverage** - Maintain 90%+ coverage
6. **Documentation** - Update cookbook + README
7. **Exit codes** - Always return 0 (success) or non-zero (error)

---

**Last updated**: 2026-01-10
**Phase**: 1 (Core CLI Complete)
**Test status**: 64/64 passing ✓
