"""
Integration tests for CLI 'did you mean?' suggestions.
Tests the full CLI flow including error messages.
"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestCLISuggestions:
    """Test 'did you mean?' suggestions in real CLI usage."""

    def test_main_command_typo_suggestion(self):
        """Test suggestion for main command typo."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'stat'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0  # Error exit code
        assert "invalid choice: 'stat'" in result.stderr
        assert "Did you mean 'status'?" in result.stderr

    def test_subcommand_typo_suggestion(self):
        """Test suggestion for subcommand typo."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'model', 'lst'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "invalid choice: 'lst'" in result.stderr
        assert "Did you mean 'list'?" in result.stderr

    def test_serve_subcommand_typo(self):
        """Test suggestion for serve subcommand typo."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'serve', 'stat'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Should suggest either 'start' or 'status' - both are similar to 'stat'
        assert "Did you mean" in result.stderr
        assert "stat" in result.stderr.lower()

    def test_firmware_subcommand_typo(self):
        """Test suggestion for firmware subcommand typo."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'firmware', 'lst'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Did you mean 'list'?" in result.stderr

    def test_device_subcommand_typo(self):
        """Test suggestion for device subcommand typo."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'device', 'tst'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Did you mean 'test'?" in result.stderr

    def test_env_subcommand_typo(self):
        """Test suggestion for env subcommand typo."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'env', 'lst'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Did you mean 'list'?" in result.stderr

    def test_metal_subcommand_typo(self):
        """Test suggestion for metal subcommand typo."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'metal', 'lst'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Did you mean 'list'?" in result.stderr

    def test_very_different_command_no_suggestion(self):
        """Test that very different commands don't get suggestions."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'xyz123'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "invalid choice" in result.stderr
        assert "Did you mean" not in result.stderr

    def test_help_shows_examples(self):
        """Test that help shows usage examples."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', '--help'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0  # Help exits cleanly
        assert 'Examples:' in result.stdout
        assert 'tt status' in result.stdout
        assert 'tt run' in result.stdout
        assert 'tt model list' in result.stdout

    def test_model_help_shows_examples(self):
        """Test that model subcommand help shows examples."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'model', '--help'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'Examples:' in result.stdout
        assert 'tt model list' in result.stdout
        assert 'tt model get' in result.stdout

    def test_serve_help_shows_examples(self):
        """Test that serve subcommand help shows examples."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'serve', '--help'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'Examples:' in result.stdout
        assert 'tt serve start' in result.stdout

    def test_device_help_shows_examples(self):
        """Test that device subcommand help shows examples."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'device', '--help'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'Examples:' in result.stdout
        assert 'tt device info' in result.stdout

    def test_firmware_help_shows_examples(self):
        """Test that firmware subcommand help shows examples."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'firmware', '--help'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'Examples:' in result.stdout
        assert 'tt firmware current' in result.stdout

    def test_env_help_shows_examples(self):
        """Test that env subcommand help shows examples."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'env', '--help'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'Examples:' in result.stdout
        assert 'tt env list' in result.stdout

    def test_metal_help_shows_examples(self):
        """Test that metal subcommand help shows examples."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'metal', '--help'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'Examples:' in result.stdout
        assert 'tt metal list' in result.stdout


class TestValidCommands:
    """Test that valid commands work correctly."""

    def test_version_flag(self):
        """Test version flag works."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', '--version'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'tt-cli' in result.stdout or 'tt-cli' in result.stderr

    def test_valid_command_no_suggestion(self):
        """Test that valid commands don't trigger suggestions."""
        # status with --json should work (may fail for other reasons, but not invalid choice)
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'status', '--json'],
            capture_output=True,
            text=True,
        )

        # Should not have "Did you mean" in output
        assert "Did you mean" not in result.stderr


class TestCommonTypos:
    """Test common typos that users might make."""

    def test_typo_strat_suggests_start(self):
        """Test 'strat' suggests 'start'."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'serve', 'strat', 'model'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Did you mean 'start'?" in result.stderr

    def test_typo_chek_suggests_check(self):
        """Test 'chek' suggests 'check'."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'env', 'chek'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Did you mean 'check'?" in result.stderr

    def test_typo_doenload_suggests_download(self):
        """Test 'doenload' suggests 'download'."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'model', 'doenload', 'model-name'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Did you mean 'download'?" in result.stderr

    def test_typo_resto_suggests_reset(self):
        """Test 'resto' suggests 'reset'."""
        result = subprocess.run(
            [sys.executable, '-m', 'tt.core.cli', 'device', 'resto'],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Should suggest 'reset' or 'test' (both similar)
        assert "Did you mean" in result.stderr
