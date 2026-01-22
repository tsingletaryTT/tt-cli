"""
Unit tests for configuration management
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from tt.utils import config


class TestConfigLoad:
    """Test configuration file loading."""

    def test_load_config_default_values(self, tmp_path):
        """Test loading config with default values."""
        cfg = config.load_config(config_path=None)

        assert cfg is not None
        assert 'models_dir' in cfg
        assert 'server' in cfg
        assert 'environments' in cfg

    def test_load_config_from_file(self, tmp_path):
        """Test loading config from YAML file."""
        config_file = tmp_path / ".ttconfig"
        config_file.write_text("""
models_dir: ~/custom-models
server:
  default_port: 9000
  default_max_model_len: 4096
environments:
  default: metal
""")

        cfg = config.load_config(config_path=str(config_file))

        assert cfg['models_dir'] == '~/custom-models'
        assert cfg['server']['default_port'] == 9000
        assert cfg['server']['default_max_model_len'] == 4096
        assert cfg['environments']['default'] == 'metal'

    def test_load_config_file_not_found(self, tmp_path):
        """Test loading config when file doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"

        cfg = config.load_config(config_path=str(config_file))

        # Should return defaults
        assert cfg is not None
        assert 'models_dir' in cfg

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test loading config with invalid YAML."""
        config_file = tmp_path / ".ttconfig"
        config_file.write_text("""
this is not: valid: yaml: content
""")

        cfg = config.load_config(config_path=str(config_file))

        # Should return defaults on error
        assert cfg is not None

    def test_load_config_searches_standard_locations(self, tmp_path):
        """Test that load_config searches standard locations."""
        with patch('pathlib.Path.home', return_value=tmp_path):
            # Create config in home directory
            config_file = tmp_path / ".ttconfig"
            config_file.write_text("models_dir: ~/test-models")

            cfg = config.load_config()

            assert cfg['models_dir'] == '~/test-models'


class TestConfigGet:
    """Test getting configuration values."""

    def test_get_value_exists(self):
        """Test getting a value that exists."""
        cfg = {'server': {'default_port': 8000}}

        value = config.get_value(cfg, 'server.default_port')

        assert value == 8000

    def test_get_value_with_default(self):
        """Test getting a value with default fallback."""
        cfg = {'server': {}}

        value = config.get_value(cfg, 'server.default_port', default=9000)

        assert value == 9000

    def test_get_value_nested(self):
        """Test getting nested values."""
        cfg = {'environments': {'metal': {'python_version': '3.10'}}}

        value = config.get_value(cfg, 'environments.metal.python_version')

        assert value == '3.10'

    def test_get_value_not_exists_no_default(self):
        """Test getting non-existent value without default."""
        cfg = {}

        value = config.get_value(cfg, 'nonexistent.key')

        assert value is None


class TestConfigSet:
    """Test setting configuration values."""

    def test_set_value_simple(self):
        """Test setting a simple value."""
        cfg = {}

        config.set_value(cfg, 'models_dir', '~/my-models')

        assert cfg['models_dir'] == '~/my-models'

    def test_set_value_nested(self):
        """Test setting nested values."""
        cfg = {}

        config.set_value(cfg, 'server.default_port', 9000)

        assert cfg['server']['default_port'] == 9000

    def test_set_value_overwrites_existing(self):
        """Test that set_value overwrites existing values."""
        cfg = {'server': {'default_port': 8000}}

        config.set_value(cfg, 'server.default_port', 9000)

        assert cfg['server']['default_port'] == 9000


class TestConfigSave:
    """Test saving configuration."""

    def test_save_config_creates_file(self, tmp_path):
        """Test that save_config creates a file."""
        config_file = tmp_path / ".ttconfig"
        cfg = {
            'models_dir': '~/models',
            'server': {'default_port': 8000},
        }

        config.save_config(cfg, config_path=str(config_file))

        assert config_file.exists()

    def test_save_config_valid_yaml(self, tmp_path):
        """Test that saved config is valid YAML."""
        config_file = tmp_path / ".ttconfig"
        cfg = {
            'models_dir': '~/models',
            'server': {'default_port': 8000},
        }

        config.save_config(cfg, config_path=str(config_file))

        # Should be able to load it back
        loaded = config.load_config(config_path=str(config_file))
        assert loaded['models_dir'] == '~/models'
        assert loaded['server']['default_port'] == 8000


class TestConfigCommand:
    """Test config command integration."""

    def test_config_get_command(self, tmp_path, capsys):
        """Test tt config get command."""
        import argparse
        from tt.commands import config as config_cmd

        args = argparse.Namespace(
            key='models_dir',
            config_file=None,
        )

        result = config_cmd.get(args)

        out, err = capsys.readouterr()
        assert result == 0
        assert 'models' in out.lower()

    def test_config_set_command(self, tmp_path):
        """Test tt config set command."""
        import argparse
        from tt.commands import config as config_cmd

        config_file = tmp_path / ".ttconfig"

        args = argparse.Namespace(
            key='models_dir',
            value='~/custom-models',
            config_file=str(config_file),
        )

        result = config_cmd.set(args)

        assert result == 0
        assert config_file.exists()

    def test_config_list_command(self, capsys):
        """Test tt config list command."""
        import argparse
        from tt.commands import config as config_cmd

        args = argparse.Namespace(
            json=False,
            config_file=None,
        )

        result = config_cmd.list_config(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert len(out) > 0
