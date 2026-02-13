# Testing Documentation

**Test-Driven Development setup for tt-cli**

## Overview

The tt-cli project follows test-driven development practices with comprehensive unit and integration testing.

## Test Statistics

- **Total Tests**: 64
- **Pass Rate**: 100%
- **Test Files**: 4
- **Fixtures**: 15+

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures for all tests
├── unit/
│   ├── test_hardware.py     # Hardware detection tests (27 tests)
│   └── test_envmanager.py   # Environment management tests (23 tests)
└── integration/
    └── test_commands.py     # CLI command integration tests (14 tests)
```

## Test Coverage

### Hardware Detection (`test_hardware.py`)

**27 tests covering**:
- tt-smi availability detection
- Device parsing from JSON output
- Multi-device system handling
- MESH_DEVICE configuration logic (N150, N300, T3K, P100, etc.)
- Architecture detection (Wormhole vs Blackhole)
- Temperature and telemetry parsing
- Hardware summary formatting
- Timeout and error handling

**Key test classes**:
- `TestHasTtSmi` - Tool availability
- `TestDetectHardware` - Device detection and parsing
- `TestGetMeshDevice` - MESH_DEVICE logic
- `TestGetArchName` - Architecture determination
- `TestArchitectureChecks` - Hardware type validation
- `TestFormatHardwareSummary` - Output formatting

### Environment Management (`test_envmanager.py`)

**23 tests covering**:
- uv availability detection
- Python version detection
- Virtual environment creation (uv and venv)
- Package installation (hybrid uv/pip)
- Environment activation (metal, vllm, forge, xla)
- Variable conflict detection (TT-Forge vs tt-metal)
- Environment validation (`env check`)
- Automatic fixing (`env fix`)
- PYTHONPATH and LD_LIBRARY_PATH handling

**Key test classes**:
- `TestHasUv` - uv tool detection
- `TestGetCurrentPythonVersion` - Version string parsing
- `TestCreateVenv` - Venv creation with fallback
- `TestInstallPackages` - Package installation
- `TestActivateEnvironment` - Environment switching
- `TestCheckEnvironment` - Environment validation
- `TestFixEnvironment` - Auto-repair logic
- `TestGetVenvPythonVersion` - Venv introspection
- `TestEnvironmentConfigurations` - Config constants

### Command Integration (`test_commands.py`)

**14 tests covering**:
- `tt status` command (with/without hardware, JSON output)
- `tt env list` command
- `tt env use` command (success and error cases)
- `tt env check` command
- `tt env fix` command
- `tt device info` command (with/without tt-smi)
- `tt device test` command (with/without TTNN)
- `tt model list` command
- `tt model info` command
- `tt model check` command (valid and invalid models)

**Key test classes**:
- `TestStatusCommand` - System status reporting
- `TestEnvCommands` - Environment management
- `TestDeviceCommands` - Device operations
- `TestModelCommands` - Model management

## Shared Fixtures (`conftest.py`)

### Environment Fixtures
- `temp_home` - Temporary HOME directory for isolation
- `clean_env` - Unset all TT environment variables
- `mock_tt_metal_env` - Simulated tt-metal environment
- `mock_venvs` - Mock virtual environment directories

### Hardware Fixtures
- `mock_tt_smi_available` - tt-smi is available
- `mock_tt_smi_unavailable` - tt-smi not found
- `mock_hardware_n150` - Single N150 device
- `mock_hardware_multi` - 4x P300 multi-device system

### Tool Fixtures
- `mock_uv_available` - uv tool is available
- `mock_uv_unavailable` - uv not installed
- `capture_output` - Helper for stdout/stderr capture

### Model Fixtures
- `mock_models_dir` - Directory with test models (Qwen3-0.6B, Llama-3.1-8B)

## Running Tests

### Basic Usage

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_hardware.py

# Run specific test class
pytest tests/unit/test_hardware.py::TestDetectHardware

# Run specific test
pytest tests/unit/test_hardware.py::TestDetectHardware::test_detect_hardware_single_device

# Run tests matching pattern
pytest -k "test_detect"
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=tt --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=tt --cov-report=html
open htmlcov/index.html

# Fail if coverage below threshold
pytest --cov=tt --cov-fail-under=80
```

### Continuous Integration

```bash
# Run tests with all warnings
pytest -W error

# Run with stricter settings
pytest --strict-markers --strict-config

# Fast fail on first error
pytest -x

# Parallel execution (requires pytest-xdist)
pytest -n auto
```

## Writing New Tests

### Test Pattern: Hardware Detection

```python
def test_detect_hardware_single_device(self, mock_tt_smi_available):
    """Test detection of single device."""
    mock_output = {
        'devices': [{
            'board_type': 'n150',
            'index': 0,
            'telemetry': {
                'ASIC_TEMPERATURE': 35.5,
                'ASIC_POWER': 45.2,
            },
            'pci_bus': '0000:01:00.0',
            'fw_bundle_version': 'v1.2.3',
        }]
    }

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_output)
        )

        result = hardware.detect_hardware()

        assert result is not None
        assert result['count'] == 1
        assert result['primary_type'] == 'N150'
```

### Test Pattern: Environment Management

```python
def test_activate_environment(self, temp_home, clean_env):
    """Test activating tt-metal environment."""
    # Create tt-metal directory
    tt_metal = temp_home / "tt-metal"
    tt_metal.mkdir()

    result = envmanager.activate_environment('metal')

    assert 'TT_METAL_HOME' in result
    assert result['TT_METAL_HOME'] == str(tt_metal)
    assert 'PYTHONPATH' in result
    assert 'LD_LIBRARY_PATH' in result

    # Check os.environ was actually set
    assert os.environ['TT_METAL_HOME'] == str(tt_metal)
```

### Test Pattern: Command Integration

```python
def test_status_with_hardware(self, mock_hardware_n150, capsys):
    """Test status command with hardware detected."""
    args = argparse.Namespace(json=False)

    with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_n150):
        status.status(args)

    out, err = capsys.readouterr()

    assert 'Hardware' in out
    assert 'N150' in out
    assert 'Environment' in out
```

## Test-Driven Development Workflow

### 1. Write Test First

```python
# tests/unit/test_newfeature.py
def test_new_feature():
    """Test description of what should happen."""
    result = newfeature.do_something()
    assert result == expected_value
```

### 2. Run Test (Should Fail)

```bash
pytest tests/unit/test_newfeature.py
# FAILED - newfeature module doesn't exist
```

### 3. Implement Feature

```python
# tt/utils/newfeature.py
def do_something():
    return expected_value
```

### 4. Run Test (Should Pass)

```bash
pytest tests/unit/test_newfeature.py
# PASSED
```

### 5. Refactor and Add More Tests

```python
def test_new_feature_edge_case():
    """Test edge case behavior."""
    result = newfeature.do_something(edge_case_input)
    assert result == expected_edge_case_output
```

### 6. Update Cookbook

Add recipe to `docs/cookbook.md` showing how users can use the new feature.

## Mocking Best Practices

### Mock External Commands

```python
with patch('subprocess.run') as mock_run:
    mock_run.return_value = Mock(returncode=0, stdout="output")
    result = function_that_calls_subprocess()
```

### Mock File System

```python
def test_with_temp_files(tmp_path):
    """Use pytest's tmp_path fixture for file operations."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    result = function_that_reads_file(test_file)
    assert result == "content"
```

### Mock Environment Variables

```python
def test_with_env_vars(monkeypatch):
    """Use monkeypatch to set environment variables."""
    monkeypatch.setenv('TT_METAL_HOME', '/fake/path')

    result = function_that_checks_env()
    assert result is not None
```

## Common Issues

### Issue: Tests Pass Individually But Fail Together

**Cause**: Tests are modifying shared state (os.environ, filesystem)

**Solution**: Use fixtures to clean up after each test:
```python
@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables."""
    vars_to_unset = ['TT_METAL_HOME', 'PYTHONPATH', 'LD_LIBRARY_PATH']
    for var in vars_to_unset:
        monkeypatch.delenv(var, raising=False)
```

### Issue: Mock Not Working

**Cause**: Patching wrong location (should patch where it's used, not where it's defined)

**Wrong**:
```python
with patch('shutil.which'):  # ❌ Patches original, not used location
```

**Right**:
```python
with patch('tt.utils.hardware.which'):  # ✓ Patches where it's imported
```

### Issue: Fixture Not Found

**Cause**: Fixture defined in wrong location or not imported

**Solution**: Define shared fixtures in `conftest.py` at appropriate level:
- `tests/conftest.py` - Shared by all tests
- `tests/unit/conftest.py` - Shared by unit tests only
- `tests/integration/conftest.py` - Shared by integration tests only

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest --cov=tt --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Test Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Total Tests | 64 | ✓ |
| Pass Rate | 100% | ✓ |
| Unit Tests | 50 | ✓ |
| Integration Tests | 14 | ✓ |
| Fixtures | 15+ | ✓ |
| Test Files | 4 | ✓ |

## Future Test Improvements

### Phase 2 Testing (Planned)

- [ ] End-to-end tests for `tt serve` commands
- [ ] Integration tests with real tt-metal API
- [ ] Performance benchmarks
- [ ] Multi-device test scenarios
- [ ] Model download/conversion tests
- [ ] TUI interaction tests
- [ ] Load testing for server management

### Test Coverage Goals

- [ ] Achieve 90%+ code coverage
- [ ] Add property-based testing (hypothesis)
- [ ] Add mutation testing (mutmut)
- [ ] Add performance regression tests

## Resources

- **pytest Documentation**: https://docs.pytest.org/
- **unittest.mock Guide**: https://docs.python.org/3/library/unittest.mock.html
- **Fixture Best Practices**: https://docs.pytest.org/en/stable/fixture.html
- **Coverage.py**: https://coverage.readthedocs.io/

---

**Remember**: Write tests first, implement features second. It's not just about catching bugs—it's about designing better APIs.
