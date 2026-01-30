"""
Pytest configuration and shared fixtures
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Create a temporary home directory for testing."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def mock_tt_smi_available(monkeypatch):
    """Mock tt-smi as available."""
    def mock_which(cmd):
        if cmd == 'tt-smi':
            return '/usr/bin/tt-smi'
        return None

    monkeypatch.setattr('shutil.which', mock_which)


@pytest.fixture
def mock_tt_smi_unavailable(monkeypatch):
    """Mock tt-smi as unavailable."""
    def mock_which(cmd):
        return None

    monkeypatch.setattr('shutil.which', mock_which)


@pytest.fixture
def mock_hardware_n150():
    """Mock hardware detection for N150 (single Wormhole chip)."""
    return {
        'devices': [{
            'type': 'N150',
            'index': 0,
            'temperature': 35.0,
            'power': 45.0,
            'pci_bus': '0000:01:00.0',
            'firmware': 'v1.2.3',
        }],
        'count': 1,
        'primary_type': 'N150',
    }


@pytest.fixture
def mock_hardware_multi():
    """Mock hardware detection for 4x P300 (Blackhole multi-chip)."""
    devices = []
    for i in range(4):
        devices.append({
            'type': 'P300',
            'index': i,
            'temperature': 33.0 + i,
            'power': 50.0 + i * 5,
            'pci_bus': f'0000:0{i}:00.0',
            'firmware': 'v2.0.0',
        })

    return {
        'devices': devices,
        'count': 4,
        'primary_type': 'P300',
    }


@pytest.fixture
def mock_models_dir(temp_home):
    """Create a mock models directory with test models."""
    models_dir = temp_home / "models"
    models_dir.mkdir()

    # Create Qwen3-0.6B model
    qwen_dir = models_dir / "Qwen3-0.6B"
    qwen_dir.mkdir()

    # Create config.json
    config = {
        "architectures": ["Qwen3ForCausalLM"],
        "hidden_size": 1024,
        "num_hidden_layers": 28,
        "vocab_size": 151936,
    }
    (qwen_dir / "config.json").write_text(json.dumps(config, indent=2))

    # Create fake model weights
    (qwen_dir / "model.safetensors").write_text("fake weights")

    # Create Llama model
    llama_dir = models_dir / "Llama-3.1-8B-Instruct"
    llama_dir.mkdir()

    config = {
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 4096,
        "num_hidden_layers": 32,
        "vocab_size": 128256,
    }
    (llama_dir / "config.json").write_text(json.dumps(config, indent=2))
    (llama_dir / "model.safetensors").write_text("fake weights")

    return models_dir


@pytest.fixture
def mock_venvs(temp_home):
    """Create mock virtual environments."""
    # TT-Metal venv
    metal_venv = temp_home / "tt-metal" / "python_env"
    metal_venv.mkdir(parents=True)
    (metal_venv / "bin").mkdir()
    (metal_venv / "bin" / "python").touch()
    (metal_venv / "pyvenv.cfg").write_text("version = 3.12.3")

    # vLLM venv
    vllm_venv = temp_home / "tt-metal" / "build" / "python_env_vllm"
    vllm_venv.mkdir(parents=True)
    (vllm_venv / "bin").mkdir()
    (vllm_venv / "bin" / "python").touch()
    (vllm_venv / "pyvenv.cfg").write_text("version = 3.12.3")

    # XLA venv
    xla_venv = temp_home / "tt-xla-venv"
    xla_venv.mkdir()
    (xla_venv / "bin").mkdir()
    (xla_venv / "bin" / "python").touch()
    (xla_venv / "pyvenv.cfg").write_text("version = 3.11.14")

    return {
        'metal': metal_venv,
        'vllm': vllm_venv,
        'xla': xla_venv,
    }


@pytest.fixture
def mock_uv_available(monkeypatch):
    """Mock uv as available."""
    def mock_which(cmd):
        if cmd == 'uv':
            return '/usr/bin/uv'
        return None

    monkeypatch.setattr('shutil.which', mock_which)


@pytest.fixture
def mock_uv_unavailable(monkeypatch):
    """Mock uv as unavailable."""
    def mock_which(cmd):
        if cmd == 'uv':
            return None
        return None

    monkeypatch.setattr('shutil.which', mock_which)


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables."""
    vars_to_unset = [
        'TT_METAL_HOME',
        'PYTHONPATH',
        'LD_LIBRARY_PATH',
        'TT_METAL_VERSION',
        'MESH_DEVICE',
        'TT_METAL_ARCH_NAME',
    ]

    for var in vars_to_unset:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_tt_metal_env(temp_home, monkeypatch):
    """Set up tt-metal environment variables."""
    tt_metal = temp_home / "tt-metal"
    tt_metal.mkdir()

    monkeypatch.setenv('TT_METAL_HOME', str(tt_metal))
    monkeypatch.setenv('PYTHONPATH', str(tt_metal))
    monkeypatch.setenv('LD_LIBRARY_PATH', '/opt/openmpi-v5.0.7-ulfm/lib')

    return tt_metal


@pytest.fixture
def capture_output(capsys):
    """Helper to capture and return stdout/stderr."""
    def _capture():
        captured = capsys.readouterr()
        return captured.out, captured.err
    return _capture


@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses for firmware releases."""
    releases = [
        {
            'tag_name': 'v19.4.2',
            'published_at': '2026-01-05T12:34:56Z',
            'assets': [
                {
                    'name': 'fw_pack-80.140.41.0.fwbundle',
                    'browser_download_url': 'https://github.com/tenstorrent/tt-firmware/releases/download/v19.4.2/fw_pack-80.140.41.0.fwbundle',
                },
            ],
        },
        {
            'tag_name': 'v19.4.1',
            'published_at': '2025-12-19T10:20:30Z',
            'assets': [
                {
                    'name': 'fw_pack-80.140.40.0.fwbundle',
                    'browser_download_url': 'https://github.com/tenstorrent/tt-firmware/releases/download/v19.4.1/fw_pack-80.140.40.0.fwbundle',
                },
            ],
        },
        {
            'tag_name': 'v19.4.0',
            'published_at': '2025-12-16T08:15:00Z',
            'assets': [
                {
                    'name': 'fw_pack-80.140.39.0.fwbundle',
                    'browser_download_url': 'https://github.com/tenstorrent/tt-firmware/releases/download/v19.4.0/fw_pack-80.140.39.0.fwbundle',
                },
            ],
        },
    ]

    return {
        'releases': releases,
        'latest': releases[0],
    }


@pytest.fixture
def mock_tt_flash_available(monkeypatch):
    """Mock tt-flash as available."""
    def mock_which(cmd):
        if cmd == 'tt-flash':
            return '/usr/bin/tt-flash'
        return None

    monkeypatch.setattr('shutil.which', mock_which)


@pytest.fixture
def mock_tt_flash_unavailable(monkeypatch):
    """Mock tt-flash as unavailable."""
    def mock_which(cmd):
        if cmd == 'tt-flash':
            return None
        return None

    monkeypatch.setattr('shutil.which', mock_which)


@pytest.fixture
def mock_firmware_download(tmp_path):
    """Mock firmware download to temporary directory."""
    def _download_mock(version, cache_dir=None, show_progress=True):
        if cache_dir is None:
            cache_dir = tmp_path / ".tt" / "firmware"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create mock firmware bundle
        bundle_name = f"fw_pack-80.140.41.0.fwbundle"
        bundle_path = cache_dir / bundle_name
        bundle_path.write_text(f"Mock firmware data for {version}")

        return bundle_path

    return _download_mock


@pytest.fixture
def mock_hardware_p300c():
    """Mock hardware detection for P300C (Blackhole 2-chip board)."""
    return {
        'devices': [
            {
                'type': 'P300C',
                'index': 0,
                'temperature': 35.0,
                'power': 50.0,
                'pci_bus': '0000:01:00.0',
                'firmware': 0x13040200,  # 19.4.2.0
            },
            {
                'type': 'P300C',
                'index': 1,
                'temperature': 36.0,
                'power': 51.0,
                'pci_bus': '0000:02:00.0',
                'firmware': 0x13040200,  # 19.4.2.0
            },
        ],
        'count': 2,
        'primary_type': 'P300C',
    }
