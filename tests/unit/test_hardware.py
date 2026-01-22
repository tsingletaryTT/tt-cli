"""
Unit tests for hardware detection utilities
"""

import pytest
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from tt.utils import hardware


class TestHasTtSmi:
    """Test tt-smi availability detection."""

    def test_has_tt_smi_available(self, mock_tt_smi_available):
        """Test when tt-smi is available."""
        assert hardware.has_tt_smi() is True

    def test_has_tt_smi_unavailable(self, mock_tt_smi_unavailable):
        """Test when tt-smi is not available."""
        assert hardware.has_tt_smi() is False


class TestDetectHardware:
    """Test hardware detection."""

    def test_detect_hardware_no_tt_smi(self, mock_tt_smi_unavailable):
        """Test when tt-smi is not available."""
        result = hardware.detect_hardware()
        assert result is None

    def test_detect_hardware_single_device(self, mock_tt_smi_available):
        """Test detection of single device."""
        mock_output = {
            'devices': [{
                'board_type': 'n150',
                'index': 0,
                'telemetry': {
                    'ASIC_TEMPERATURE': 35.5,
                    'ASIC_POWER': 45.2,
                },
                'pci_bus': '0000:01:00.0',
                'fw_bundle_version': 'v1.2.3',
            }]
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(mock_output)
            )

            result = hardware.detect_hardware()

            assert result is not None
            assert result['count'] == 1
            assert result['primary_type'] == 'N150'
            assert len(result['devices']) == 1

            device = result['devices'][0]
            assert device['type'] == 'N150'
            assert device['index'] == 0
            assert device['temperature'] == 35.5
            assert device['power'] == 45.2

    def test_detect_hardware_multi_device(self, mock_tt_smi_available):
        """Test detection of multiple devices."""
        mock_output = {
            'devices': [
                {
                    'board_type': 'p300',
                    'index': i,
                    'telemetry': {
                        'ASIC_TEMPERATURE': 30.0 + i,
                        'ASIC_POWER': 50.0 + i * 5,
                    },
                    'pci_bus': f'0000:0{i}:00.0',
                    'fw_bundle_version': 'v2.0.0',
                }
                for i in range(4)
            ]
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(mock_output)
            )

            result = hardware.detect_hardware()

            assert result is not None
            assert result['count'] == 4
            assert result['primary_type'] == 'P300'
            assert len(result['devices']) == 4

    def test_detect_hardware_timeout(self, mock_tt_smi_available):
        """Test timeout handling."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('tt-smi', 5)

            result = hardware.detect_hardware()
            assert result is None

    def test_detect_hardware_invalid_json(self, mock_tt_smi_available):
        """Test invalid JSON handling."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='invalid json'
            )

            result = hardware.detect_hardware()
            assert result is None


class TestGetMeshDevice:
    """Test MESH_DEVICE determination."""

    def test_get_mesh_device_n150(self):
        """Test MESH_DEVICE for single N150."""
        mock_hw = {
            'primary_type': 'N150',
            'count': 1,
            'devices': [{'type': 'N150', 'index': 0}],
        }

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            result = hardware.get_mesh_device()
            assert result == 'N150'

    def test_get_mesh_device_n300(self):
        """Test MESH_DEVICE for N300 (2x N150)."""
        mock_hw = {
            'primary_type': 'N150',
            'count': 2,
            'devices': [
                {'type': 'N150', 'index': 0},
                {'type': 'N150', 'index': 1},
            ],
        }

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            result = hardware.get_mesh_device()
            assert result == 'N300'

    def test_get_mesh_device_t3k(self):
        """Test MESH_DEVICE for T3K (8x N150)."""
        mock_hw = {
            'primary_type': 'N150',
            'count': 8,
            'devices': [{'type': 'N150', 'index': i} for i in range(8)],
        }

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            result = hardware.get_mesh_device()
            assert result == 'T3K'

    def test_get_mesh_device_p100(self):
        """Test MESH_DEVICE for P100 (Blackhole)."""
        mock_hw = {
            'primary_type': 'P100',
            'count': 1,
            'devices': [{'type': 'P100', 'index': 0}],
        }

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            result = hardware.get_mesh_device()
            assert result == 'P100'

    def test_get_mesh_device_no_hardware(self):
        """Test when no hardware detected."""
        with patch('tt.utils.hardware.detect_hardware', return_value=None):
            result = hardware.get_mesh_device()
            assert result is None


class TestGetArchName:
    """Test architecture name determination."""

    def test_get_arch_name_blackhole(self):
        """Test TT_METAL_ARCH_NAME for Blackhole."""
        mock_hw = {
            'primary_type': 'P100',
            'count': 1,
            'devices': [{'type': 'P100', 'index': 0}],
        }

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            result = hardware.get_arch_name()
            assert result == 'blackhole'

    def test_get_arch_name_wormhole(self):
        """Test TT_METAL_ARCH_NAME for Wormhole (auto-detected)."""
        mock_hw = {
            'primary_type': 'N150',
            'count': 1,
            'devices': [{'type': 'N150', 'index': 0}],
        }

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            result = hardware.get_arch_name()
            assert result is None  # Wormhole auto-detects


class TestArchitectureChecks:
    """Test architecture type checks."""

    def test_is_blackhole_true(self):
        """Test is_blackhole for P100."""
        mock_hw = {'primary_type': 'P100', 'count': 1, 'devices': []}

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            assert hardware.is_blackhole() is True

    def test_is_blackhole_false(self):
        """Test is_blackhole for N150."""
        mock_hw = {'primary_type': 'N150', 'count': 1, 'devices': []}

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            assert hardware.is_blackhole() is False

    def test_is_wormhole_true(self):
        """Test is_wormhole for N150."""
        mock_hw = {'primary_type': 'N150', 'count': 1, 'devices': []}

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            assert hardware.is_wormhole() is True

    def test_is_wormhole_false(self):
        """Test is_wormhole for P100."""
        mock_hw = {'primary_type': 'P100', 'count': 1, 'devices': []}

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            assert hardware.is_wormhole() is False


class TestFormatHardwareSummary:
    """Test hardware summary formatting."""

    def test_format_no_hardware(self):
        """Test formatting when no hardware."""
        result = hardware.format_hardware_summary(None)
        assert "No hardware detected" in result

    def test_format_single_device(self):
        """Test formatting for single device."""
        mock_hw = {
            'primary_type': 'N150',
            'count': 1,
            'devices': [{
                'type': 'N150',
                'firmware': 'v1.2.3',
                'temperature': 35.0,
            }],
        }

        result = hardware.format_hardware_summary(mock_hw)
        assert 'N150' in result
        assert 'v1.2.3' in result

    def test_format_multi_device(self):
        """Test formatting for multiple devices."""
        mock_hw = {
            'primary_type': 'P300',
            'count': 4,
            'devices': [
                {'type': 'P300', 'temperature': 30.0 + i}
                for i in range(4)
            ],
        }

        result = hardware.format_hardware_summary(mock_hw)
        assert '4x P300' in result
        assert '30-33°C' in result
