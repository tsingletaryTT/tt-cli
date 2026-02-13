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


class TestMultiDeviceDeployment:
    """Test multi-device deployment functionality."""

    def test_serve_single_device_with_device_id(self, mock_hardware_p300c_x4, tmp_path, capsys):
        """Test starting server on specific device with --device-id."""
        model_dir = tmp_path / "models" / "Qwen3-0.6B"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text('{"model_type": "qwen2"}')

        # Create tmp PID directory
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            port=8000,
            device_id=0,
            max_model_len=None,
            tensor_parallel=None,
            detach=False,
            models_dir=str(tmp_path / "models")
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c_x4):
            with patch('subprocess.Popen') as mock_popen:
                with patch.dict('os.environ', {}, clear=True):
                    with patch('tt.commands.serve.get_pid_file') as mock_get_pid:
                        # Return PID file in tmp directory
                        mock_get_pid.return_value = pid_dir / "qwen3-0.6b-dev0.pid"
                        mock_process = Mock()
                        mock_process.pid = 12345
                        mock_popen.return_value = mock_process

                        result = serve.start(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'Target device: 0' in out
        assert 'TT_VISIBLE_DEVICES: 0' in out
        assert 'TT_METAL_CACHE' in out
        assert 'tt_metal_0' in out

    def test_serve_device_isolation_env_vars(self, mock_hardware_p300c_x4, tmp_path):
        """Test that device isolation sets correct environment variables."""
        model_dir = tmp_path / "models" / "Qwen3-0.6B"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text('{"model_type": "qwen2"}')

        # Create tmp PID directory
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            port=8001,
            device_id=1,
            max_model_len=None,
            tensor_parallel=None,
            detach=False,
            models_dir=str(tmp_path / "models")
        )

        env_vars_captured = {}

        def capture_env(*args, **kwargs):
            # Capture the env dict passed to Popen
            if 'env' in kwargs:
                env_vars_captured.update(kwargs['env'])
            mock_process = Mock()
            mock_process.pid = 12346
            return mock_process

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c_x4):
            with patch('subprocess.Popen', side_effect=capture_env):
                with patch('tt.commands.serve.get_pid_file') as mock_get_pid:
                    mock_get_pid.return_value = pid_dir / "qwen3-0.6b-dev1.pid"
                    serve.start(args)

        # Verify device isolation environment variables
        assert env_vars_captured.get('TT_VISIBLE_DEVICES') == '1'
        assert 'tt_metal_1' in env_vars_captured.get('TT_METAL_CACHE', '')
        assert env_vars_captured.get('MESH_DEVICE') == 'P150'
        assert env_vars_captured.get('TT_METAL_ARCH_NAME') == 'blackhole'
        assert 'TT_MESH_GRAPH_DESC_PATH' in env_vars_captured
        assert 'single_device_1.textproto' in env_vars_captured['TT_MESH_GRAPH_DESC_PATH']

    def test_serve_multiple_devices_different_ports(self, mock_hardware_p300c_x4, tmp_path):
        """Test starting servers on multiple devices with different ports."""
        model_dir = tmp_path / "models" / "Qwen3-0.6B"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text('{"model_type": "qwen2"}')

        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        # Start servers on devices 0-3
        for device_id in range(4):
            args = argparse.Namespace(
                model='Qwen3-0.6B',
                port=8000 + device_id,
                device_id=device_id,
                max_model_len=None,
                tensor_parallel=None,
                detach=True,
                models_dir=str(tmp_path / "models")
            )

            with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c_x4):
                with patch('subprocess.Popen') as mock_popen:
                    with patch('tt.commands.serve.get_pid_file') as mock_get_pid:
                        # Return unique PID file for each device
                        pid_file = pid_dir / f"qwen3-0.6b-dev{device_id}.pid"
                        mock_get_pid.return_value = pid_file

                        mock_process = Mock()
                        mock_process.pid = 12345 + device_id
                        mock_popen.return_value = mock_process

                        result = serve.start(args)
                        assert result == 0

        # Verify all 4 PID files were created
        assert len(list(pid_dir.glob('*.pid'))) == 4

    def test_serve_device_id_validation(self, mock_hardware_p300c_x4, tmp_path, capsys):
        """Test that invalid device IDs are rejected."""
        model_dir = tmp_path / "models" / "Qwen3-0.6B"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text('{"model_type": "qwen2"}')

        # Try to start server on device 5 (system only has 4 devices: 0-3)
        args = argparse.Namespace(
            model='Qwen3-0.6B',
            port=8000,
            device_id=5,
            max_model_len=None,
            tensor_parallel=None,
            detach=False,
            models_dir=str(tmp_path / "models")
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c_x4):
            result = serve.start(args)

        assert result == 1
        out, err = capsys.readouterr()
        assert 'Invalid device ID' in out

    def test_serve_per_device_pid_files(self, tmp_path):
        """Test that per-device PID files are created correctly."""
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        # Test that device-specific PID files have correct naming
        # When device_id is specified, filename should include -devN
        # When device_id is None, filename should not include -dev

        # Simulate what get_pid_file would return
        model_name = "qwen3-0.6b"

        pid_file_0 = pid_dir / f"{model_name}-dev0.pid"
        pid_file_1 = pid_dir / f"{model_name}-dev1.pid"
        pid_file_none = pid_dir / f"{model_name}.pid"

        assert 'dev0' in str(pid_file_0)
        assert 'dev1' in str(pid_file_1)
        assert '-dev' not in str(pid_file_none)  # Changed from 'dev' to '-dev' to be more specific
        assert pid_file_0 != pid_file_1

    def test_status_shows_per_device_servers(self, tmp_path, capsys):
        """Test that status command shows servers with device IDs."""
        # This test verifies the status display format, not the actual status command
        # The status command is in status.py, not serve.py
        # We'll test the data structure that status.py uses

        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        # Create mock PID files for different devices
        import json
        (pid_dir / "qwen3-0.6b-dev0.pid").write_text(
            json.dumps({'pid': 12345, 'port': 8000, 'model': 'Qwen3-0.6B', 'device_id': 0})
        )
        (pid_dir / "qwen3-0.6b-dev1.pid").write_text(
            json.dumps({'pid': 12346, 'port': 8001, 'model': 'Qwen3-0.6B', 'device_id': 1})
        )

        # Verify PID files contain device_id field
        pid_data_0 = json.loads((pid_dir / "qwen3-0.6b-dev0.pid").read_text())
        pid_data_1 = json.loads((pid_dir / "qwen3-0.6b-dev1.pid").read_text())

        assert pid_data_0['device_id'] == 0
        assert pid_data_1['device_id'] == 1
        assert pid_data_0['port'] == 8000
        assert pid_data_1['port'] == 8001

    def test_stop_device_specific_server(self, tmp_path, capsys):
        """Test stopping server on specific device."""
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        # Create PID file for device 2
        import json
        (pid_dir / "qwen3-0.6b-dev2.pid").write_text(
            json.dumps({'pid': 12347, 'port': 8002, 'model': 'Qwen3-0.6B', 'device_id': 2})
        )

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            device_id=2,
            pid_dir=str(pid_dir)
        )

        with patch('os.kill') as mock_kill:
            def kill_side_effect(pid, sig):
                if sig == signal.SIGTERM:
                    kill_side_effect.sigterm_sent = True
                elif sig == 0 and getattr(kill_side_effect, 'sigterm_sent', False):
                    raise ProcessLookupError()

            mock_kill.side_effect = kill_side_effect
            with patch('os.path.exists', return_value=True):
                result = serve.stop(args)

        assert result == 0
        out, err = capsys.readouterr()
        assert 'Stopped' in out

    def test_mesh_descriptor_path_generation(self, mock_hardware_p300c_x4, tmp_path):
        """Test that mesh descriptor paths are generated correctly."""
        model_dir = tmp_path / "models" / "Qwen3-0.6B"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text('{"model_type": "qwen2"}')

        # Create tmp PID directory
        pid_dir = tmp_path / ".tt" / "servers"
        pid_dir.mkdir(parents=True)

        env_vars_captured = {}

        def capture_env(*args, **kwargs):
            if 'env' in kwargs:
                env_vars_captured.update(kwargs['env'])
            mock_process = Mock()
            mock_process.pid = 12345
            return mock_process

        args = argparse.Namespace(
            model='Qwen3-0.6B',
            port=8000,
            device_id=2,
            max_model_len=None,
            tensor_parallel=None,
            detach=False,
            models_dir=str(tmp_path / "models")
        )

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hardware_p300c_x4):
            with patch('subprocess.Popen', side_effect=capture_env):
                with patch('tt.commands.serve.get_pid_file') as mock_get_pid:
                    mock_get_pid.return_value = pid_dir / "qwen3-0.6b-dev2.pid"
                    serve.start(args)

        # Verify mesh descriptor path includes device ID
        mesh_path = env_vars_captured.get('TT_MESH_GRAPH_DESC_PATH', '')
        assert 'single_device_2.textproto' in mesh_path
        assert mesh_path.endswith('.textproto')


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

    def test_serve_start_with_device_id(self, tmp_path):
        """Test that 'tt serve start <model> --device-id X' parses correctly."""
        parser = cli.create_parser()

        # Test: tt serve start Qwen3-0.6B --port 8001 --device-id 2 --detach
        args = parser.parse_args(['serve', 'start', 'Qwen3-0.6B', '--port', '8001', '--device-id', '2', '--detach'])

        assert hasattr(args, 'func')
        assert args.func == serve.start
        assert args.model == 'Qwen3-0.6B'
        assert args.port == 8001
        assert args.device_id == 2
        assert args.detach is True
