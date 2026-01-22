"""
Integration tests for workflow commands
"""

import pytest
import argparse
import json
from pathlib import Path
from unittest.mock import Mock, patch

from tt.commands import workflow


class TestWorkflowCommand:
    """Test workflow management commands."""

    def test_workflow_list(self, capsys):
        """Test listing available workflows."""
        args = argparse.Namespace(json=False)

        result = workflow.list_workflows(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'Available Workflows' in out

    def test_workflow_list_json(self, capsys):
        """Test listing workflows with JSON output."""
        args = argparse.Namespace(json=True)

        result = workflow.list_workflows(args)

        assert result == 0
        out, err = capsys.readouterr()
        data = json.loads(out)
        assert 'workflows' in data
        assert isinstance(data['workflows'], list)

    def test_workflow_run_setup(self, tmp_path, capsys):
        """Test running setup workflow."""
        args = argparse.Namespace(
            name='setup',
            dry_run=False,
        )

        with patch('tt.commands.workflow.run_setup_workflow') as mock_setup:
            mock_setup.return_value = 0

            result = workflow.run(args)

        assert result == 0
        mock_setup.assert_called_once()

    def test_workflow_run_dry_run(self, capsys):
        """Test workflow dry run (shows steps without executing)."""
        args = argparse.Namespace(
            name='setup',
            dry_run=True,
        )

        result = workflow.run(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'Dry run' in out or 'would execute' in out.lower()

    def test_workflow_run_unknown(self, capsys):
        """Test running unknown workflow."""
        args = argparse.Namespace(
            name='nonexistent',
            dry_run=False,
        )

        result = workflow.run(args)

        assert result == 1
        out, err = capsys.readouterr()
        assert 'not found' in out.lower() or 'unknown' in out.lower()

    def test_workflow_info(self, capsys):
        """Test showing workflow information."""
        args = argparse.Namespace(
            name='setup',
        )

        result = workflow.info(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'setup' in out.lower()
        assert 'description' in out.lower() or 'steps' in out.lower()


class TestSetupWorkflow:
    """Test setup workflow specifically."""

    def test_setup_workflow_checks_uv(self, capsys):
        """Test that setup workflow checks for uv."""
        with patch('tt.utils.envmanager.has_uv', return_value=False):
            with patch('tt.utils.hardware.detect_hardware', return_value=None):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0)

                    result = workflow.run_setup_workflow()

        # Should suggest installing uv if not available
        out, err = capsys.readouterr()
        assert 'uv not found' in out or 'uv' in out.lower()

    def test_setup_workflow_creates_venv(self, tmp_path, capsys):
        """Test that setup workflow creates virtual environment."""
        with patch('tt.utils.envmanager.has_uv', return_value=True):
            with patch('tt.utils.envmanager.create_venv') as mock_create:
                mock_create.return_value = 'uv'

                result = workflow.run_setup_workflow()

        # Should create venv
        assert mock_create.called or result == 0


class TestBenchmarkWorkflow:
    """Test benchmark workflow."""

    def test_benchmark_workflow_requires_model(self, capsys):
        """Test that benchmark workflow requires a model."""
        args = argparse.Namespace(
            name='benchmark',
            model=None,
            dry_run=False,
        )

        result = workflow.run(args)

        # Should fail or prompt for model
        assert result == 1 or 'model' in capsys.readouterr()[0].lower()


class TestModelWorkflow:
    """Test test-model workflow integration."""

    def test_model_workflow_checks_model_exists(self, tmp_path, capsys):
        """Test that test-model workflow checks if model exists."""
        model_path = tmp_path / "models" / "Qwen3-0.6B"
        model_path.mkdir(parents=True)
        (model_path / "config.json").write_text('{"model_type": "qwen2"}')

        args = argparse.Namespace(
            name='test-model',
            model='Qwen3-0.6B',
            dry_run=False,
        )

        with patch('tt.commands.model.check') as mock_check:
            with patch('tt.commands.serve.start') as mock_serve:
                with patch('tt.commands.serve.stop') as mock_stop:
                    mock_check.return_value = 0
                    mock_serve.return_value = 0
                    mock_stop.return_value = 0

                    result = workflow.run(args)

        # Should validate model
        assert mock_check.called

    def test_model_workflow_starts_and_stops_server(self, tmp_path, capsys):
        """Test that workflow starts and stops server."""
        args = argparse.Namespace(
            name='test-model',
            model='Qwen3-0.6B',
            dry_run=False,
            quick=False,
        )

        with patch('tt.commands.model.check', return_value=0):
            with patch('tt.commands.serve.start', return_value=0) as mock_start:
                with patch('tt.commands.serve.stop', return_value=0) as mock_stop:
                    with patch('tt.commands.workflow.test_model_inference', return_value=True):
                        result = workflow.run(args)

        # Should start and stop server
        assert mock_start.called
        assert mock_stop.called

    def test_model_workflow_quick_mode(self, capsys):
        """Test quick validation mode (no server start)."""
        args = argparse.Namespace(
            name='test-model',
            model='Qwen3-0.6B',
            dry_run=False,
            quick=True,
        )

        with patch('tt.commands.model.check', return_value=0) as mock_check:
            with patch('tt.commands.serve.start') as mock_start:
                result = workflow.run(args)

        # Should only validate, not start server
        assert mock_check.called
        assert not mock_start.called


class TestEvalWorkflow:
    """Test eval workflow."""

    def test_eval_workflow_list_available_evals(self, capsys):
        """Test listing available evaluation suites."""
        args = argparse.Namespace(
            name='eval',
            list_evals=True,
        )

        with patch('tt.commands.workflow.list_available_evals') as mock_list:
            mock_list.return_value = ['mmlu', 'hellaswag', 'truthfulqa']

            result = workflow.run(args)

        out, err = capsys.readouterr()
        # Should show available evals
