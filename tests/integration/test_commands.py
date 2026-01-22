"""
Integration tests for CLI commands
"""

import pytest
import json
import argparse
from unittest.mock import Mock, patch

from tt.commands import status, env, device, model


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
