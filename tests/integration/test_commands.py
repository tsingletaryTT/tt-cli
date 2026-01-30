"""
Integration tests for CLI commands
"""

import pytest
import json
import argparse
from unittest.mock import Mock, patch

from tt.commands import status, env, device, model, firmware


class TestStatusCommand:
    """Test status command integration."""

    def test_status_with_hardware(self, mock_hardware_n150, capture_output, capsys):
        """Test status command with hardware detected."""
        args = argparse.Namespace(json=False)

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_n150):
            status.status(args)

        out, err = capsys.readouterr()

        assert 'Hardware' in out
        assert 'N150' in out
        assert 'Environment' in out

    def test_status_without_hardware(self, capsys):
        """Test status command without hardware."""
        args = argparse.Namespace(json=False)

        with patch('tt.utils.hardware.detect_hardware', return_value=None):
            status.status(args)

        out, err = capsys.readouterr()

        assert 'No hardware detected' in out

    def test_status_json_output(self, mock_hardware_n150, capsys):
        """Test status command with JSON output."""
        args = argparse.Namespace(json=True)

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_n150):
            status.status(args)

        out, err = capsys.readouterr()

        # Should be valid JSON
        data = json.loads(out)
        assert 'hardware' in data
        assert 'environment' in data
        assert 'models' in data


class TestEnvCommands:
    """Test environment management commands."""

    def test_env_list(self, mock_venvs, capsys):
        """Test env list command."""
        args = argparse.Namespace()

        env.list_envs(args)

        out, err = capsys.readouterr()

        assert 'metal' in out
        assert 'vllm' in out
        assert 'forge' in out
        assert 'xla' in out

    def test_env_use(self, temp_home, clean_env, capsys):
        """Test env use command."""
        # Create tt-metal directory
        tt_metal = temp_home / "tt-metal"
        tt_metal.mkdir()

        args = argparse.Namespace(name='metal')

        result = env.use(args)

        out, err = capsys.readouterr()

        assert result is None  # Success
        assert 'Environment configured' in out
        assert 'TT_METAL_HOME' in out

    def test_env_use_invalid(self, capsys):
        """Test env use with invalid environment."""
        args = argparse.Namespace(name='invalid')

        # Should not be in the allowed choices, but test error handling
        # In real CLI, argparse would catch this, but test the function
        try:
            env.use(args)
        except:
            pass  # Expected to fail

    def test_env_check_clean(self, temp_home, mock_tt_metal_env, capsys):
        """Test env check with clean environment."""
        args = argparse.Namespace()

        env.check(args)

        out, err = capsys.readouterr()

        # With mock environment, should be OK
        assert '✓' in out or 'good' in out.lower()

    def test_env_fix(self, temp_home, clean_env, capsys):
        """Test env fix command."""
        # Create tt-metal directory
        tt_metal = temp_home / "tt-metal"
        tt_metal.mkdir()

        args = argparse.Namespace()

        env.fix(args)

        out, err = capsys.readouterr()

        assert 'Applied fixes' in out or 'No fixes needed' in out


class TestDeviceCommands:
    """Test device management commands."""

    def test_device_info_with_hardware(self, mock_hardware_n150, capsys):
        """Test device info command."""
        args = argparse.Namespace()

        with patch('tt.utils.hardware.has_tt_smi', return_value=True):
            with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_n150):
                device.info(args)

        out, err = capsys.readouterr()

        assert 'Hardware Information' in out
        assert 'N150' in out
        assert 'Device 0' in out

    def test_device_info_no_tt_smi(self, capsys):
        """Test device info without tt-smi."""
        args = argparse.Namespace()

        with patch('tt.utils.hardware.has_tt_smi', return_value=False):
            result = device.info(args)

        out, err = capsys.readouterr()

        assert result == 1  # Error
        assert 'tt-smi not found' in out

    def test_device_test_no_ttnn(self, mock_hardware_n150, capsys):
        """Test device test without TTNN available."""
        args = argparse.Namespace()

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_n150):
            # Import will fail
            result = device.test(args)

        out, err = capsys.readouterr()

        # Should handle ImportError gracefully
        assert 'TTNN not available' in out or result is not None


class TestModelCommands:
    """Test model management commands."""

    def test_model_list_with_models(self, mock_models_dir, capsys):
        """Test model list command with models."""
        args = argparse.Namespace()

        result = model.list_models(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'Qwen3-0.6B' in out
        assert 'Llama-3.1-8B-Instruct' in out

    def test_model_list_no_models_dir(self, temp_home, capsys):
        """Test model list when models directory doesn't exist."""
        args = argparse.Namespace()

        result = model.list_models(args)

        out, err = capsys.readouterr()

        assert result == 1
        assert 'not found' in out

    def test_model_info_existing(self, mock_models_dir, capsys):
        """Test model info for existing model."""
        args = argparse.Namespace(name='Qwen3-0.6B')

        result = model.info(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'Qwen3-0.6B' in out
        assert 'Qwen3ForCausalLM' in out
        assert '1024' in out  # Hidden size

    def test_model_info_nonexistent(self, mock_models_dir, capsys):
        """Test model info for nonexistent model."""
        args = argparse.Namespace(name='NonExistent')

        result = model.info(args)

        out, err = capsys.readouterr()

        assert result == 1
        assert 'not found' in out

    def test_model_check_valid(self, mock_models_dir, capsys):
        """Test model check for valid model."""
        args = argparse.Namespace(name='Qwen3-0.6B')

        result = model.check(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert '✓' in out
        assert 'config.json' in out
        assert 'weight file' in out.lower()

    def test_model_check_invalid(self, mock_models_dir, capsys):
        """Test model check for invalid model."""
        # Create model without required files
        models_dir = mock_models_dir
        bad_model = models_dir / "BadModel"
        bad_model.mkdir()

        args = argparse.Namespace(name='BadModel')

        result = model.check(args)

        out, err = capsys.readouterr()

        assert result == 1
        assert '✗' in out


class TestFirmwareCommands:
    """Test firmware management commands."""

    def test_firmware_list(self, mock_github_api, capsys):
        """Test firmware list command."""
        args = argparse.Namespace(json=False, recommended=False)

        # Mock GitHub API
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_github_api['releases']).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            with patch('tt.utils.hardware.detect_hardware', return_value=None):
                result = firmware.list_firmware(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'Available Firmware Versions' in out
        assert '19.4.2' in out
        assert '19.4.1' in out

    def test_firmware_list_with_hardware(self, mock_github_api, mock_hardware_p300c, capsys):
        """Test firmware list with hardware detection."""
        args = argparse.Namespace(json=False, recommended=False)

        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_github_api['releases']).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c):
                with patch('tt.utils.firmware.get_current_firmware') as mock_current:
                    mock_current.return_value = {
                        'devices': [],
                        'primary_version': '19.4.2',
                    }

                    result = firmware.list_firmware(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'P300C' in out
        assert 'current' in out

    def test_firmware_list_json(self, mock_github_api, capsys):
        """Test firmware list with JSON output."""
        args = argparse.Namespace(json=True, recommended=False)

        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_github_api['releases']).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            with patch('tt.utils.hardware.detect_hardware', return_value=None):
                result = firmware.list_firmware(args)

        out, err = capsys.readouterr()

        assert result == 0

        # Parse JSON
        data = json.loads(out)
        assert 'firmware_versions' in data
        assert len(data['firmware_versions']) > 0

    def test_firmware_list_network_error(self, capsys):
        """Test firmware list with network error."""
        args = argparse.Namespace(json=False, recommended=False)

        with patch('urllib.request.urlopen', side_effect=Exception("Network error")):
            result = firmware.list_firmware(args)

        out, err = capsys.readouterr()

        assert result == 1
        assert 'Failed to fetch' in out

    def test_firmware_current(self, mock_hardware_p300c, capsys):
        """Test firmware current command."""
        args = argparse.Namespace(json=False)

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c):
            result = firmware.current_firmware(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'Current Firmware' in out
        assert '19.4.2' in out
        assert 'Device 0' in out
        assert 'Device 1' in out

    def test_firmware_current_no_hardware(self, capsys):
        """Test firmware current with no hardware."""
        args = argparse.Namespace(json=False)

        with patch('tt.utils.hardware.detect_hardware', return_value=None):
            result = firmware.current_firmware(args)

        out, err = capsys.readouterr()

        assert result == 1
        assert 'No hardware detected' in out

    def test_firmware_current_json(self, mock_hardware_p300c, capsys):
        """Test firmware current with JSON output."""
        args = argparse.Namespace(json=True)

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c):
            result = firmware.current_firmware(args)

        out, err = capsys.readouterr()

        assert result == 0

        # Parse JSON
        data = json.loads(out)
        assert 'devices' in data
        assert 'primary_version' in data

    def test_firmware_download(self, mock_github_api, tmp_path, capsys):
        """Test firmware download command."""
        args = argparse.Namespace(version='19.4.2', output=None)

        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_github_api['releases']).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            with patch('tt.utils.firmware.DEFAULT_CACHE_DIR', tmp_path):
                with patch('urllib.request.urlretrieve') as mock_retrieve:
                    # Mock download
                    def mock_download_func(url, path, reporthook=None):
                        from pathlib import Path
                        Path(path).write_text("firmware data")

                    mock_retrieve.side_effect = mock_download_func

                    result = firmware.download(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'downloaded' in out.lower()

    def test_firmware_download_invalid_version(self, mock_github_api, tmp_path, capsys):
        """Test firmware download with invalid version."""
        args = argparse.Namespace(version='99.99.99', output=None)

        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_github_api['releases']).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            with patch('tt.utils.firmware.DEFAULT_CACHE_DIR', tmp_path):
                result = firmware.download(args)

        out, err = capsys.readouterr()

        assert result == 1
        assert 'not found' in out

    def test_firmware_flash_with_path(self, tmp_path, mock_hardware_p300c, mock_tt_flash_available, capsys):
        """Test firmware flash with bundle path."""
        # Create mock bundle
        bundle_path = tmp_path / "firmware.fwbundle"
        bundle_path.write_text("firmware data")

        args = argparse.Namespace(
            version_or_path=str(bundle_path),
            force=False,
            no_reset=False,
            allow_downgrades=False,
            yes=True,  # Skip confirmation
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c):
            with patch('tt.utils.firmware.get_current_firmware') as mock_current:
                mock_current.return_value = {
                    'devices': [],
                    'primary_version': '19.4.2',
                }

                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0)

                    result = firmware.flash(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'successfully' in out.lower()

    def test_firmware_flash_with_version(self, tmp_path, mock_github_api, mock_hardware_p300c, mock_tt_flash_available, capsys):
        """Test firmware flash with version string."""
        args = argparse.Namespace(
            version_or_path='19.4.2',
            force=False,
            no_reset=False,
            allow_downgrades=False,
            yes=True,
        )

        # Create cached bundle
        cache_dir = tmp_path / ".tt" / "firmware"
        cache_dir.mkdir(parents=True)
        bundle_path = cache_dir / "fw_pack-80.140.41.0.fwbundle"
        bundle_path.write_text("firmware data")

        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_github_api['releases']).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            with patch('tt.utils.firmware.DEFAULT_CACHE_DIR', cache_dir):
                with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c):
                    with patch('tt.utils.firmware.get_current_firmware') as mock_current:
                        mock_current.return_value = {
                            'devices': [],
                            'primary_version': '19.4.1',
                        }

                        with patch('subprocess.run') as mock_run:
                            mock_run.return_value = Mock(returncode=0)

                            result = firmware.flash(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'successfully' in out.lower()

    def test_firmware_flash_no_tt_flash(self, tmp_path, mock_tt_flash_unavailable, capsys):
        """Test firmware flash without tt-flash."""
        bundle_path = tmp_path / "firmware.fwbundle"
        bundle_path.write_text("firmware data")

        args = argparse.Namespace(
            version_or_path=str(bundle_path),
            force=False,
            no_reset=False,
            allow_downgrades=False,
            yes=True,
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=None):
            result = firmware.flash(args)

        out, err = capsys.readouterr()

        assert result == 1
        assert 'tt-flash' in out

    def test_firmware_verify(self, tmp_path, mock_tt_flash_available, capsys):
        """Test firmware verify command."""
        bundle_path = tmp_path / "firmware.fwbundle"
        bundle_path.write_text("firmware data")

        args = argparse.Namespace(version_or_path=str(bundle_path))

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = firmware.verify(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'passed' in out.lower()

    def test_firmware_verify_no_bundle(self, mock_tt_flash_available, capsys):
        """Test firmware verify without bundle (verify current)."""
        args = argparse.Namespace(version_or_path=None)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = firmware.verify(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'passed' in out.lower()

    def test_firmware_latest(self, mock_github_api, capsys):
        """Test firmware latest command."""
        args = argparse.Namespace(download=False, flash=False, recommended=False, yes=False)

        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_github_api['releases']).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            with patch('tt.utils.hardware.detect_hardware', return_value=None):
                result = firmware.latest(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'Latest Firmware' in out
        assert '19.4.2' in out

    def test_firmware_latest_with_current(self, mock_github_api, mock_hardware_p300c, capsys):
        """Test firmware latest with current firmware."""
        args = argparse.Namespace(download=False, flash=False, recommended=False, yes=False)

        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_github_api['releases']).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c):
                with patch('tt.utils.firmware.get_current_firmware') as mock_current:
                    mock_current.return_value = {
                        'devices': [],
                        'primary_version': '19.4.2',
                    }

                    result = firmware.latest(args)

        out, err = capsys.readouterr()

        assert result == 0
        assert 'up to date' in out.lower()
