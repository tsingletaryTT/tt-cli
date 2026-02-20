"""
Unit tests for CLI argument parsing and error handling.
Tests 'did you mean?' suggestions and help text.
"""

import pytest
import sys
from io import StringIO
from contextlib import redirect_stderr

from tt.core.cli import create_parser, SmartArgumentParser
from tt.utils.similarity import find_similar_command, find_multiple_suggestions


class TestSmartArgumentParser:
    """Test custom ArgumentParser with 'did you mean?' suggestions."""

    def test_invalid_main_command_suggests_similar(self, capsys):
        """Test suggestion for typo in main command."""
        parser = create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['stat'])  # Should suggest 'status'

        assert exc_info.value.code == 2  # argparse error exit code

        # Capture stderr (where argparse writes errors)
        captured = capsys.readouterr()
        assert "invalid choice: 'stat'" in captured.err
        assert "Did you mean 'status'?" in captured.err

    def test_invalid_subcommand_suggests_similar(self, capsys):
        """Test suggestion for typo in subcommand."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['model', 'lst'])  # Should suggest 'list'

        captured = capsys.readouterr()
        assert "invalid choice: 'lst'" in captured.err
        assert "Did you mean 'list'?" in captured.err

    def test_serve_subcommand_typo(self, capsys):
        """Test suggestion for serve subcommand typo."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['serve', 'stat'])  # Should suggest 'start' or 'status'

        captured = capsys.readouterr()
        assert "invalid choice: 'stat'" in captured.err
        # Should suggest either 'start' or 'status' - both are similar
        assert "Did you mean" in captured.err

    def test_firmware_subcommand_typo(self, capsys):
        """Test suggestion for firmware subcommand typo."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['firmware', 'lst'])  # Should suggest 'list'

        captured = capsys.readouterr()
        assert "invalid choice: 'lst'" in captured.err
        assert "Did you mean 'list'?" in captured.err

    def test_invalid_command_no_close_match(self, capsys):
        """Test that very different commands don't get suggestions."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['xyz123'])  # No similar command

        captured = capsys.readouterr()
        assert "invalid choice: 'xyz123'" in captured.err
        assert "Did you mean" not in captured.err  # No suggestion

    def test_valid_command_no_error(self):
        """Test that valid commands don't trigger errors."""
        parser = create_parser()

        # These should parse without error
        args = parser.parse_args(['status', '--json'])
        assert args.command == 'status'
        assert args.json == True

    def test_valid_subcommand_no_error(self):
        """Test that valid subcommands parse correctly."""
        parser = create_parser()

        args = parser.parse_args(['model', 'list'])
        assert args.command == 'model'
        assert args.model_command == 'list'


class TestStringSimilarity:
    """Test string similarity utility functions."""

    def test_find_similar_exact_match(self):
        """Test finding exact match returns it."""
        result = find_similar_command('status', ['status', 'start', 'stop'])
        assert result == 'status'

    def test_find_similar_typo(self):
        """Test finding similar command for common typo."""
        result = find_similar_command('stat', ['status', 'start', 'stop'])
        # Both 'status' and 'start' are equally similar to 'stat'
        assert result in ['status', 'start']

    def test_find_similar_missing_letter(self):
        """Test finding command with missing letter."""
        result = find_similar_command('lst', ['list', 'last', 'lost'])
        # 'lst' is similar to all three options - any reasonable match is good
        assert result in ['list', 'last', 'lost']

    def test_find_similar_swapped_letters(self):
        """Test finding command with swapped letters."""
        result = find_similar_command('serev', ['serve', 'server', 'service'])
        assert result == 'serve'

    def test_find_similar_no_match(self):
        """Test that very different string returns None."""
        result = find_similar_command('xyz', ['status', 'start', 'stop'])
        assert result is None

    def test_find_similar_cutoff_respected(self):
        """Test that cutoff threshold is respected."""
        # With high cutoff, weak match should return None
        result = find_similar_command('st', ['status', 'start', 'stop'], cutoff=0.8)
        assert result is None

        # With low cutoff, weak match should return something
        result = find_similar_command('st', ['status', 'start', 'stop'], cutoff=0.3)
        assert result in ['status', 'start', 'stop']

    def test_find_similar_prefix_match(self):
        """Test that prefix matching works well."""
        result = find_similar_command('sta', ['status', 'start', 'stop'])
        # Should match one of the 'sta*' commands
        assert result in ['status', 'start']

    def test_find_multiple_suggestions(self):
        """Test finding multiple similar commands."""
        results = find_multiple_suggestions('sta', ['status', 'start', 'stop', 'stack'])

        # Should return multiple matches
        assert len(results) > 0
        assert len(results) <= 3  # n=3 by default
        assert all(s in ['status', 'start', 'stop', 'stack'] for s in results)

    def test_find_multiple_respects_n(self):
        """Test that n parameter limits results."""
        results = find_multiple_suggestions('s', ['status', 'start', 'stop', 'stack', 'serve'], n=2)
        assert len(results) <= 2

    def test_find_multiple_empty_on_no_match(self):
        """Test that no matches returns empty list."""
        results = find_multiple_suggestions('xyz', ['status', 'start', 'stop'])
        assert results == []


class TestHelpText:
    """Test help text and examples."""

    def test_main_help_has_examples(self, capsys):
        """Test main help includes usage examples."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['--help'])

        captured = capsys.readouterr()
        assert 'Examples:' in captured.out
        assert 'tt status' in captured.out
        assert 'tt run' in captured.out

    def test_model_subcommand_help(self, capsys):
        """Test model subcommand help has examples."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['model', '--help'])

        captured = capsys.readouterr()
        assert 'Examples:' in captured.out
        assert 'tt model list' in captured.out
        assert 'tt model get' in captured.out

    def test_serve_subcommand_help(self, capsys):
        """Test serve subcommand help has examples."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['serve', '--help'])

        captured = capsys.readouterr()
        assert 'Examples:' in captured.out
        assert 'tt serve start' in captured.out

    def test_device_subcommand_help(self, capsys):
        """Test device subcommand help has examples."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['device', '--help'])

        captured = capsys.readouterr()
        assert 'Examples:' in captured.out
        assert 'tt device info' in captured.out


class TestCommandParsing:
    """Test parsing of various command combinations."""

    def test_parse_model_list(self):
        """Test parsing model list command."""
        parser = create_parser()
        args = parser.parse_args(['model', 'list'])

        assert args.command == 'model'
        assert args.model_command == 'list'

    def test_parse_serve_with_options(self):
        """Test parsing serve command with options."""
        parser = create_parser()
        args = parser.parse_args(['serve', 'start', 'my-model', '--port', '8001'])

        assert args.command == 'serve'
        assert args.serve_command == 'start'
        assert args.model == 'my-model'
        assert args.port == 8001

    def test_parse_run_with_mesh_device(self):
        """Test parsing run command with mesh-device flag."""
        parser = create_parser()
        args = parser.parse_args(['run', 'llama-3.1-8b', '--mesh-device', 'P150X4'])

        assert args.command == 'run'
        assert args.model == 'llama-3.1-8b'
        assert args.mesh_device == 'P150X4'

    def test_parse_firmware_flash(self):
        """Test parsing firmware flash command."""
        parser = create_parser()
        args = parser.parse_args(['firmware', 'flash', 'v19.4.2', '--yes'])

        assert args.command == 'firmware'
        assert args.firmware_command == 'flash'
        assert args.version_or_path == 'v19.4.2'
        assert args.yes == True

    def test_parse_status_json(self):
        """Test parsing status with JSON flag."""
        parser = create_parser()
        args = parser.parse_args(['status', '--json'])

        assert args.command == 'status'
        assert args.json == True

    def test_parse_metal_checkout(self):
        """Test parsing metal checkout command."""
        parser = create_parser()
        args = parser.parse_args(['metal', 'checkout', '--tag', 'v0.66.0-rc7'])

        assert args.command == 'metal'
        assert args.metal_command == 'checkout'
        assert args.tag == 'v0.66.0-rc7'

    def test_parse_env_use(self):
        """Test parsing env use command."""
        parser = create_parser()
        args = parser.parse_args(['env', 'use', 'vllm'])

        assert args.command == 'env'
        assert args.env_command == 'use'
        assert args.name == 'vllm'

    def test_parse_device_info(self):
        """Test parsing device info command."""
        parser = create_parser()
        args = parser.parse_args(['device', 'info'])

        assert args.command == 'device'
        assert args.device_command == 'info'

    def test_parse_stop_with_device_id(self):
        """Test parsing stop command with device ID."""
        parser = create_parser()
        args = parser.parse_args(['stop', 'my-model', '--device-id', '2'])

        assert args.command == 'stop'
        assert args.model == 'my-model'
        assert args.device_id == 2


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_missing_required_subcommand(self, capsys):
        """Test error when required subcommand is missing."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['model'])  # Missing subcommand

        captured = capsys.readouterr()
        # Should show error about required subcommand
        assert 'required' in captured.err.lower() or 'model_command' in captured.err

    def test_invalid_port_number(self, capsys):
        """Test error for invalid port number."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['serve', 'start', 'model', '--port', 'not-a-number'])

        captured = capsys.readouterr()
        assert 'invalid' in captured.err.lower()

    def test_unknown_flag(self, capsys):
        """Test error for unknown flag."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(['status', '--unknown-flag'])

        captured = capsys.readouterr()
        assert 'unrecognized' in captured.err.lower() or 'invalid' in captured.err.lower()
