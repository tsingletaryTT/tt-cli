"""
Integration tests for server management commands
"""

import pytest
import json
import signal
import argparse
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from tt.commands import serve
from tt.core import cli


class TestServeCommand:
    """Test server management commands."""

    def test_serve_with_hardware_detection(self, mock_hardware_n150, tmp_path, capsys):
        """Test starting server with auto-detected hardware."""
        # Create mock model directory
        model_dir = tmp_path / "models" / "Qwen3-0.6B"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text('{"model_type": "qwen2"}')

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            port=8000,
            max_model_len=None,
            tensor_parallel=None,
            detach=False,
            models_dir=str(tmp_path / "models")
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_n150):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.pid = 12345
                mock_popen.return_value = mock_process

                result = serve.start(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'Starting vLLM server' in out
        assert 'N150' in out
        # In foreground mode, we don't print PID directly
        assert 'Press Ctrl+C to stop' in out

    def test_serve_with_manual_parameters(self, mock_hardware_n150, tmp_path, capsys):
        """Test starting server with manual parameter overrides."""
        model_dir = tmp_path / "models" / "Llama-3.1-8B"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text('{"model_type": "llama"}')

        args = argparse.Namespace(
            model='Llama-3.1-8B',
            port=8001,
            max_model_len=4096,
            tensor_parallel=2,
            detach=False,
            models_dir=str(tmp_path / "models")
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_n150):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.pid = 12346
                mock_popen.return_value = mock_process

                result = serve.start(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'max-model-len: 4096' in out
        assert 'tensor-parallel-size: 2' in out

    def test_serve_no_hardware_detected(self, tmp_path, capsys):
        """Test starting server when no hardware detected."""
        model_dir = tmp_path / "models" / "Qwen3-0.6B"
        model_dir.mkdir(parents=True)

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            port=8000,
            max_model_len=None,
            tensor_parallel=None,
            detach=False,
            models_dir=str(tmp_path / "models")
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=None):
            result = serve.start(args)

        assert result == 1
        out, err = capsys.readouterr()
        assert 'No hardware detected' in out

    def test_serve_model_not_found(self, mock_hardware_n150, tmp_path, capsys):
        """Test starting server with non-existent model."""
        args = argparse.Namespace(
            model='NonExistentModel',
            port=8000,
            max_model_len=None,
            tensor_parallel=None,
            detach=False,
            models_dir=str(tmp_path / "models")
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_n150):
            result = serve.start(args)

        assert result == 1
        out, err = capsys.readouterr()
        assert 'Model not found' in out or 'not found' in out.lower()

    def test_serve_detached_mode(self, mock_hardware_n150, tmp_path, capsys):
        """Test starting server in detached mode."""
        model_dir = tmp_path / "models" / "Qwen3-0.6B"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text('{"model_type": "qwen2"}')

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            port=8000,
            max_model_len=None,
            tensor_parallel=None,
            detach=True,
            models_dir=str(tmp_path / "models")
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_n150):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.pid = 12347
                mock_popen.return_value = mock_process

                result = serve.start(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'background' in out.lower()

    def test_serve_multi_device(self, mock_hardware_multi, tmp_path, capsys):
        """Test starting server on multi-device system."""
        model_dir = tmp_path / "models" / "Llama-3.1-8B"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text('{"model_type": "llama"}')

        args = argparse.Namespace(
            model='Llama-3.1-8B',
            port=8000,
            max_model_len=None,
            tensor_parallel=None,  # Should auto-set based on device count
            detach=False,
            models_dir=str(tmp_path / "models")
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_multi):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.pid = 12348
                mock_popen.return_value = mock_process

                result = serve.start(args)

        assert result == 0
        out, err = capsys.readouterr()
        # Should use tensor parallel = device count for multi-device
        assert 'tensor-parallel-size: 4' in out


class TestStopCommand:
    """Test stopping running servers."""

    def test_stop_running_server(self, tmp_path, capsys):
        """Test stopping a running server."""
        # Create mock PID file
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)
        pid_file = pid_dir / "qwen3-0.6b.pid"
        import json
        pid_file.write_text(json.dumps({'pid': 12345, 'port': 8000, 'model': 'Qwen3-0.6B'}))

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            pid_dir=str(pid_dir)
        )

        with patch('os.kill') as mock_kill:
            # Mock process stops after SIGTERM (raise on subsequent checks)
            def kill_side_effect(pid, sig):
                if sig == signal.SIGTERM:
                    # Mark that SIGTERM was sent, next check should fail
                    kill_side_effect.sigterm_sent = True
                elif sig == 0 and getattr(kill_side_effect, 'sigterm_sent', False):
                    # Process stopped after SIGTERM
                    raise ProcessLookupError()
                # Otherwise process exists (no exception)

            mock_kill.side_effect = kill_side_effect
            with patch('os.path.exists', return_value=True):
                result = serve.stop(args)

        assert result == 0
        # Verify it tried to kill the process
        assert any(call[0][1] == signal.SIGTERM for call in mock_kill.call_args_list)
        out, err = capsys.readouterr()
        assert 'Stopped' in out

    def test_stop_not_running(self, tmp_path, capsys):
        """Test stopping server that's not running."""
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            pid_dir=str(pid_dir)
        )

        result = serve.stop(args)

        assert result == 1
        out, err = capsys.readouterr()
        assert 'not running' in out.lower()

    def test_stop_process_not_found(self, tmp_path, capsys):
        """Test stopping server when process no longer exists."""
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)
        pid_file = pid_dir / "qwen3-0.6b.pid"
        import json
        pid_file.write_text(json.dumps({'pid': 99999, 'port': 8000, 'model': 'Qwen3-0.6B'}))  # Non-existent PID

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            pid_dir=str(pid_dir)
        )

        with patch('os.kill', side_effect=ProcessLookupError):
            result = serve.stop(args)

        # Should clean up PID file even if process not found
        assert result == 0
        out, err = capsys.readouterr()
        assert 'not running' in out.lower() or 'cleaned up' in out.lower()


class TestStatusCommand:
    """Test checking server status."""

    def test_status_running_servers(self, tmp_path, capsys):
        """Test showing status of running servers."""
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        # Create mock PID files
        import json
        (pid_dir / "qwen3-0.6b.pid").write_text(json.dumps({'pid': 12345, 'port': 8000, 'model': 'Qwen3-0.6B'}))
        (pid_dir / "llama-3.1-8b.pid").write_text(json.dumps({'pid': 12346, 'port': 8001, 'model': 'Llama-3.1-8B'}))

        args = argparse.Namespace(
            json=False,
            pid_dir=str(pid_dir)
        )

        with patch('os.kill') as mock_kill:
            # Don't raise exception for process check
            mock_kill.return_value = None
            with patch('os.path.exists', return_value=True):
                with patch('psutil.Process') as mock_process:
                    mock_proc = Mock()
                    mock_proc.is_running.return_value = True
                    mock_proc.cpu_percent.return_value = 25.5
                    mock_proc.memory_info.return_value = Mock(rss=1024*1024*1024)
                    mock_process.return_value = mock_proc

                    result = serve.status(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'Running Servers' in out
        assert '12345' in out
        assert '12346' in out

    def test_status_no_servers(self, tmp_path, capsys):
        """Test status when no servers running."""
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        args = argparse.Namespace(
            json=False,
            pid_dir=str(pid_dir)
        )

        result = serve.status(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'No servers running' in out

    def test_status_json_output(self, tmp_path, capsys):
        """Test status with JSON output."""
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)
        import json as jsonlib
        (pid_dir / "qwen3-0.6b.pid").write_text(jsonlib.dumps({'pid': 12345, 'port': 8000, 'model': 'Qwen3-0.6B'}))

        args = argparse.Namespace(
            json=True,
            pid_dir=str(pid_dir)
        )

        with patch('os.kill') as mock_kill:
            # Don't raise exception for process check
            mock_kill.return_value = None
            with patch('os.path.exists', return_value=True):
                with patch('psutil.Process') as mock_process:
                    mock_proc = Mock()
                    mock_proc.is_running.return_value = True
                    mock_proc.cpu_percent.return_value = 25.5
                    mock_proc.memory_info.return_value = Mock(rss=1024*1024*1024)
                    mock_process.return_value = mock_proc

                    result = serve.status(args)

        assert result == 0
        out, err = capsys.readouterr()
        data = json.loads(out)
        assert 'servers' in data
        assert len(data['servers']) == 1


class TestServeCLIParsing:
    """Test CLI argument parsing for serve commands."""

    def test_serve_status_command_parsing(self, tmp_path):
        """Test that 'tt serve status' parses correctly."""
        parser = cli.create_parser()

        # Test: tt serve status
        args = parser.parse_args(['serve', 'status'])

        assert hasattr(args, 'func')
        assert args.func == serve.status

    def test_serve_start_command_parsing(self, tmp_path):
        """Test that 'tt serve start <model>' parses correctly."""
        parser = cli.create_parser()

        # Test: tt serve start Qwen3-0.6B
        args = parser.parse_args(['serve', 'start', 'Qwen3-0.6B'])

        assert hasattr(args, 'func')
        assert args.func == serve.start
        assert args.model == 'Qwen3-0.6B'
        assert args.port == 8000  # default

    def test_serve_start_with_options(self, tmp_path):
        """Test that 'tt serve start <model> --port X' parses correctly."""
        parser = cli.create_parser()

        # Test: tt serve start Qwen3-0.6B --port 9000 --detach
        args = parser.parse_args(['serve', 'start', 'Qwen3-0.6B', '--port', '9000', '--detach'])

        assert hasattr(args, 'func')
        assert args.func == serve.start
        assert args.model == 'Qwen3-0.6B'
        assert args.port == 9000
        assert args.detach is True
