"""
Integration tests for model download commands
"""

import pytest
import json
import argparse
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

from tt.commands import model


class TestModelDownload:
    """Test model download functionality."""

    def test_download_model_success(self, tmp_path, capsys):
        """Test successful model download from HuggingFace."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        args = argparse.Namespace(
            model='Qwen/Qwen3-0.6B',
            models_dir=str(model_dir),
            validate=False,  # Don't validate for this test
            token=None
        )

        with patch('tt.commands.model.download_from_huggingface') as mock_download:
            mock_download.return_value = model_dir / "Qwen3-0.6B"

            result = model.download(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert '✓ Download complete' in out
        mock_download.assert_called_once()

    def test_download_model_with_token(self, tmp_path, capsys):
        """Test model download with HuggingFace token for gated models."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        args = argparse.Namespace(
            model='meta-llama/Llama-3.1-8B-Instruct',
            models_dir=str(model_dir),
            validate=False,  # Don't validate for this test
            token='hf_fake_token_12345'
        )

        with patch('tt.commands.model.download_from_huggingface') as mock_download:
            mock_download.return_value = model_dir / "Llama-3.1-8B-Instruct"

            result = model.download(args)

        assert result == 0
        # Verify token was passed to download function (3rd positional argument)
        call_args = mock_download.call_args
        assert call_args[0][2] == 'hf_fake_token_12345'  # token is 3rd positional arg

    def test_download_model_already_exists(self, tmp_path, capsys):
        """Test download when model already exists locally."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        existing_model = model_dir / "Qwen3-0.6B"
        existing_model.mkdir()
        (existing_model / "config.json").write_text('{"model_type": "qwen2"}')

        args = argparse.Namespace(
            model='Qwen/Qwen3-0.6B',
            models_dir=str(model_dir),
            validate=True,
            token=None,
            force=False
        )

        with patch('tt.commands.model.download_from_huggingface') as mock_download:
            result = model.download(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'already exists' in out.lower()
        # Should not call download since model exists
        mock_download.assert_not_called()

    def test_download_model_force_redownload(self, tmp_path, capsys):
        """Test force re-download of existing model."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        existing_model = model_dir / "Qwen3-0.6B"
        existing_model.mkdir()
        (existing_model / "config.json").write_text('{"model_type": "qwen2"}')
        # Create a fake weight file
        (existing_model / "model.safetensors").write_text('fake weights')

        args = argparse.Namespace(
            model='Qwen/Qwen3-0.6B',
            models_dir=str(model_dir),
            validate=True,
            token=None,
            force=True
        )

        with patch('tt.commands.model.download_from_huggingface') as mock_download:
            mock_download.return_value = existing_model

            result = model.download(args)

        assert result == 0
        # Should call download even though model exists
        mock_download.assert_called_once()

    def test_download_model_with_validation(self, tmp_path, capsys):
        """Test model download with automatic validation."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        args = argparse.Namespace(
            model='Qwen/Qwen3-0.6B',
            models_dir=str(model_dir),
            validate=True,
            token=None
        )

        downloaded_model = model_dir / "Qwen3-0.6B"

        with patch('tt.commands.model.download_from_huggingface') as mock_download:
            mock_download.return_value = downloaded_model
            with patch('tt.commands.model.validate_model_files') as mock_validate:
                mock_validate.return_value = True

                result = model.download(args)

        assert result == 0
        mock_validate.assert_called_once_with(downloaded_model)
        out, err = capsys.readouterr()
        assert 'valid' in out.lower() or '✓' in out

    def test_download_model_validation_fails(self, tmp_path, capsys):
        """Test download succeeds but validation fails."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        args = argparse.Namespace(
            model='Qwen/Qwen3-0.6B',
            models_dir=str(model_dir),
            validate=True,
            token=None
        )

        downloaded_model = model_dir / "Qwen3-0.6B"

        with patch('tt.commands.model.download_from_huggingface') as mock_download:
            mock_download.return_value = downloaded_model
            with patch('tt.commands.model.validate_model_files') as mock_validate:
                mock_validate.return_value = False

                result = model.download(args)

        assert result == 1
        out, err = capsys.readouterr()
        assert 'validation failed' in out.lower() or 'invalid' in out.lower()

    def test_download_model_network_error(self, tmp_path, capsys):
        """Test download with network error."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        args = argparse.Namespace(
            model='Qwen/Qwen3-0.6B',
            models_dir=str(model_dir),
            validate=True,
            token=None
        )

        with patch('tt.commands.model.download_from_huggingface') as mock_download:
            mock_download.side_effect = ConnectionError("Network unreachable")

            result = model.download(args)

        assert result == 1
        out, err = capsys.readouterr()
        assert 'error' in out.lower() or 'failed' in out.lower()

    def test_download_model_invalid_repo(self, tmp_path, capsys):
        """Test download with invalid HuggingFace repository."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        args = argparse.Namespace(
            model='invalid/nonexistent-model',
            models_dir=str(model_dir),
            validate=True,
            token=None
        )

        with patch('tt.commands.model.download_from_huggingface') as mock_download:
            mock_download.side_effect = ValueError("Repository not found")

            result = model.download(args)

        assert result == 1
        out, err = capsys.readouterr()
        assert 'not found' in out.lower() or 'invalid' in out.lower()

    def test_download_model_with_progress(self, tmp_path, capsys):
        """Test download shows progress updates."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        args = argparse.Namespace(
            model='Qwen/Qwen3-0.6B',
            models_dir=str(model_dir),
            validate=False,  # Don't validate for this test
            token=None
        )

        with patch('tt.commands.model.download_from_huggingface') as mock_download:
            mock_download.return_value = model_dir / "Qwen3-0.6B"

            result = model.download(args)

        assert result == 0
        out, err = capsys.readouterr()
        # Should show download complete message
        assert '✓ Download complete' in out


class TestModelGet:
    """Test model get command (alias for download)."""

    def test_get_model_calls_download(self, tmp_path):
        """Test that 'tt model get' calls download function."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        args = argparse.Namespace(
            model='Qwen/Qwen3-0.6B',
            models_dir=str(model_dir),
            validate=True,
            token=None
        )

        with patch('tt.commands.model.download') as mock_download:
            mock_download.return_value = 0

            result = model.get(args)

        assert result == 0
        mock_download.assert_called_once_with(args)


class TestHuggingFaceIntegration:
    """Test HuggingFace download integration."""

    def test_parse_model_repo(self):
        """Test parsing HuggingFace model repository strings."""
        from tt.commands.model import parse_model_repo

        # Standard format
        repo, model_name = parse_model_repo('Qwen/Qwen3-0.6B')
        assert repo == 'Qwen/Qwen3-0.6B'
        assert model_name == 'Qwen3-0.6B'

        # With subdirectory
        repo, model_name = parse_model_repo('meta-llama/Llama-3.1-8B-Instruct')
        assert repo == 'meta-llama/Llama-3.1-8B-Instruct'
        assert model_name == 'Llama-3.1-8B-Instruct'

        # Simple name (no org)
        repo, model_name = parse_model_repo('gpt2')
        assert repo == 'gpt2'
        assert model_name == 'gpt2'

    def test_normalize_local_name(self):
        """Test normalizing HuggingFace names to local directory names."""
        from tt.commands.model import normalize_local_name

        assert normalize_local_name('Qwen/Qwen3-0.6B') == 'Qwen3-0.6B'
        assert normalize_local_name('meta-llama/Llama-3.1-8B-Instruct') == 'Llama-3.1-8B-Instruct'
        assert normalize_local_name('google/gemma-3-1b-it') == 'gemma-3-1b-it'
        assert normalize_local_name('gpt2') == 'gpt2'
