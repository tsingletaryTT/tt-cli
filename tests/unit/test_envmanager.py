"""
Unit tests for environment manager
"""

import pytest
import os
import sys
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from tt.utils import envmanager


class TestHasUv:
    """Test uv availability detection."""

    def test_has_uv_available(self, mock_uv_available):
        """Test when uv is available."""
        assert envmanager.has_uv() is True

    def test_has_uv_unavailable(self, mock_uv_unavailable):
        """Test when uv is not available."""
        assert envmanager.has_uv() is False


class TestGetCurrentPythonVersion:
    """Test current Python version detection."""

    def test_get_python_version(self):
        """Test getting current Python version."""
        result = envmanager.get_current_python_version()

        # Should be format "3.12" or similar
        assert isinstance(result, str)
        parts = result.split('.')
        assert len(parts) == 2
        assert parts[0] == '3'  # Python 3.x
        assert int(parts[1]) >= 9  # 3.9+


class TestCreateVenv:
    """Test virtual environment creation."""

    def test_create_venv_with_uv(self, tmp_path, mock_uv_available):
        """Test venv creation with uv."""
        venv_path = tmp_path / "test_venv"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = envmanager.create_venv(venv_path)

            assert result == 'uv'
            mock_run.assert_called_once()
            assert 'uv venv' in mock_run.call_args[0][0]

    def test_create_venv_with_uv_python_version(self, tmp_path, mock_uv_available):
        """Test venv creation with uv and specific Python version."""
        venv_path = tmp_path / "test_venv"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = envmanager.create_venv(venv_path, python_version="3.10")

            assert result == 'uv'
            assert '--python=3.10' in mock_run.call_args[0][0]

    def test_create_venv_without_uv(self, tmp_path, mock_uv_unavailable):
        """Test venv creation without uv (fallback to standard venv)."""
        venv_path = tmp_path / "test_venv"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = envmanager.create_venv(venv_path)

            assert result == 'venv'
            mock_run.assert_called_once()
            assert f'{sys.executable} -m venv' in mock_run.call_args[0][0]

    def test_create_venv_fallback_on_uv_failure(self, tmp_path, mock_uv_available):
        """Test fallback to venv when uv fails."""
        venv_path = tmp_path / "test_venv"

        with patch('subprocess.run') as mock_run:
            # First call (uv) fails, second call (venv) succeeds
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, 'uv venv'),
                Mock(returncode=0),
            ]

            result = envmanager.create_venv(venv_path)

            assert result == 'venv'
            assert mock_run.call_count == 2


class TestInstallPackages:
    """Test package installation."""

    def test_install_packages_with_uv(self, tmp_path, mock_uv_available):
        """Test package installation with uv."""
        venv_path = tmp_path / "test_venv"
        venv_path.mkdir()
        (venv_path / "bin").mkdir()

        packages = ['numpy', 'torch']

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            envmanager.install_packages(venv_path, packages)

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert 'uv pip install' in cmd
            assert 'numpy' in cmd
            assert 'torch' in cmd

    def test_install_packages_without_uv(self, tmp_path, mock_uv_unavailable):
        """Test package installation without uv."""
        venv_path = tmp_path / "test_venv"
        venv_path.mkdir()
        (venv_path / "bin").mkdir()

        packages = ['numpy', 'torch']

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            envmanager.install_packages(venv_path, packages)

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert '/bin/pip install' in cmd
            assert 'numpy' in cmd
            assert 'torch' in cmd


class TestActivateEnvironment:
    """Test environment activation."""

    def test_activate_metal_environment(self, temp_home, clean_env):
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

    def test_activate_forge_environment(self, temp_home, clean_env, monkeypatch):
        """Test activating TT-Forge environment."""
        # Set conflicting variables first
        monkeypatch.setenv('TT_METAL_HOME', '/some/path')
        monkeypatch.setenv('TT_METAL_VERSION', 'v1.0.0')

        result = envmanager.activate_environment('forge')

        # Should unset conflicting variables
        assert 'TT_METAL_HOME' not in os.environ
        assert 'TT_METAL_VERSION' not in os.environ

        # Should set Forge variables
        assert 'PYTHONPATH' in result

    def test_activate_unknown_environment(self):
        """Test activating unknown environment raises error."""
        with pytest.raises(ValueError, match="Unknown environment"):
            envmanager.activate_environment('nonexistent')

    def test_path_variables_append(self, temp_home, clean_env, monkeypatch):
        """Test that PATH-like variables append instead of replace."""
        # Set existing LD_LIBRARY_PATH
        monkeypatch.setenv('LD_LIBRARY_PATH', '/existing/path')

        result = envmanager.activate_environment('metal')

        ld_path = os.environ['LD_LIBRARY_PATH']
        assert '/opt/openmpi-v5.0.7-ulfm/lib' in ld_path
        assert '/existing/path' in ld_path


class TestCheckEnvironment:
    """Test environment validation."""

    def test_check_environment_ok(self, temp_home, mock_tt_metal_env):
        """Test checking a valid environment."""
        result = envmanager.check_environment()

        assert result['status'] == 'ok'
        assert len(result['issues']) == 0

    def test_check_environment_missing_tt_metal_home(self, clean_env):
        """Test checking when TT_METAL_HOME not set."""
        result = envmanager.check_environment()

        assert 'TT_METAL_HOME not set' in result['warnings']

    def test_check_environment_missing_openmpi(self, temp_home, clean_env, monkeypatch):
        """Test checking when OpenMPI path missing."""
        monkeypatch.setenv('LD_LIBRARY_PATH', '/some/other/path')

        result = envmanager.check_environment()

        assert result['status'] == 'error'
        assert any('OpenMPI' in issue for issue in result['issues'])

    def test_check_environment_forge_conflict(self, temp_home, clean_env, monkeypatch):
        """Test detecting TT-Forge conflicts."""
        monkeypatch.setenv('TT_METAL_HOME', '/home/user/tt-metal')
        monkeypatch.setenv('PYTHONPATH', '/home/user/tt-forge')

        result = envmanager.check_environment()

        assert result['forge_conflict'] is True
        assert any('Forge conflict' in issue for issue in result['issues'])


class TestFixEnvironment:
    """Test automatic environment fixing."""

    def test_fix_adds_openmpi(self, temp_home, clean_env):
        """Test fixing adds OpenMPI to LD_LIBRARY_PATH."""
        # Start with no LD_LIBRARY_PATH
        fixes, env_vars = envmanager.fix_environment()

        assert any('OpenMPI' in fix or 'openmpi' in fix for fix in fixes)
        assert os.environ.get('LD_LIBRARY_PATH')
        assert 'LD_LIBRARY_PATH' in env_vars

    def test_fix_sets_tt_metal_home(self, temp_home, clean_env):
        """Test fixing sets TT_METAL_HOME when tt-metal exists."""
        # Create tt-metal directory
        tt_metal = temp_home / "tt-metal"
        tt_metal.mkdir()

        fixes, env_vars = envmanager.fix_environment()

        assert any('TT_METAL_HOME' in fix for fix in fixes)
        assert os.environ.get('TT_METAL_HOME') == str(tt_metal)
        assert env_vars.get('TT_METAL_HOME') == str(tt_metal)

    def test_fix_sets_pythonpath(self, temp_home, clean_env):
        """Test fixing sets PYTHONPATH."""
        tt_metal = temp_home / "tt-metal"
        tt_metal.mkdir()

        fixes, env_vars = envmanager.fix_environment()

        assert any('PYTHONPATH' in fix for fix in fixes)
        assert os.environ.get('PYTHONPATH')
        assert 'PYTHONPATH' in env_vars

    def test_fix_no_fixes_needed(self, temp_home, mock_tt_metal_env):
        """Test fixing when environment already correct."""
        fixes, env_vars = envmanager.fix_environment()

        # May still add paths that don't exist
        # or may return empty if everything is perfect
        assert isinstance(fixes, list)
        assert isinstance(env_vars, dict)


class TestGetVenvPythonVersion:
    """Test getting Python version from venv."""

    def test_get_venv_python_version(self, tmp_path):
        """Test getting Python version from existing venv."""
        venv_path = tmp_path / "test_venv"
        venv_path.mkdir()
        (venv_path / "bin").mkdir()
        python_bin = venv_path / "bin" / "python"
        python_bin.touch()
        python_bin.chmod(0o755)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Python 3.10.12\n"
            )

            result = envmanager.get_venv_python_version(venv_path)

            assert result == "3.10.12"

    def test_get_venv_python_version_nonexistent(self, tmp_path):
        """Test getting version from nonexistent venv."""
        venv_path = tmp_path / "nonexistent"

        result = envmanager.get_venv_python_version(venv_path)

        assert result is None


class TestEnvironmentConfigurations:
    """Test environment configuration constants."""

    def test_all_environments_defined(self):
        """Test that all expected environments are defined."""
        expected = ['metal', 'vllm', 'forge', 'xla']

        for env in expected:
            assert env in envmanager.ENVIRONMENTS

    def test_environment_has_required_fields(self):
        """Test that each environment has required fields."""
        required_fields = ['name', 'venv_path', 'vars', 'unset', 'description']

        for env_name, config in envmanager.ENVIRONMENTS.items():
            for field in required_fields:
                assert field in config, f"Environment {env_name} missing {field}"

    def test_forge_unsets_metal_variables(self):
        """Test that Forge environment unsets conflicting variables."""
        forge_config = envmanager.ENVIRONMENTS['forge']

        assert 'TT_METAL_HOME' in forge_config['unset']
        assert 'TT_METAL_VERSION' in forge_config['unset']
