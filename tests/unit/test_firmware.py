"""
Unit tests for firmware management utilities.
"""

import pytest
import json
import subprocess
import urllib.error
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path

from tt.utils import firmware


class TestParseFirmwareVersion:
    """Test firmware version parsing from hex."""

    def test_parse_standard_version(self):
        """Test parsing standard firmware version."""
        # 0x13040200 = 19.4.2.0
        result = firmware.parse_firmware_version(0x13040200)
        assert result == "19.4.2.0"

    def test_parse_different_version(self):
        """Test parsing different firmware version."""
        # 0x13040100 = 19.4.1.0
        result = firmware.parse_firmware_version(0x13040100)
        assert result == "19.4.1.0"

    def test_parse_version_with_build(self):
        """Test parsing version with non-zero build number."""
        # 0x13040205 = 19.4.2.5
        result = firmware.parse_firmware_version(0x13040205)
        assert result == "19.4.2.5"

    def test_parse_older_version(self):
        """Test parsing older major version."""
        # 0x12000000 = 18.0.0.0
        result = firmware.parse_firmware_version(0x12000000)
        assert result == "18.0.0.0"


class TestFormatFirmwareVersion:
    """Test firmware version formatting."""

    def test_format_strips_trailing_zero(self):
        """Test formatting strips trailing .0."""
        result = firmware.format_firmware_version("19.4.2.0")
        assert result == "19.4.2"

    def test_format_keeps_non_zero_build(self):
        """Test formatting keeps non-zero build number."""
        result = firmware.format_firmware_version("19.4.2.5")
        assert result == "19.4.2.5"

    def test_format_strips_multiple_trailing_zeros(self):
        """Test formatting strips multiple trailing zeros."""
        result = firmware.format_firmware_version("19.0.0.0")
        assert result == "19"

    def test_format_single_component(self):
        """Test formatting single component version."""
        result = firmware.format_firmware_version("19")
        assert result == "19"


class TestGetCurrentFirmware:
    """Test current firmware detection."""

    def test_get_current_firmware_no_hardware(self):
        """Test when no hardware detected."""
        with patch('tt.utils.hardware.detect_hardware', return_value=None):
            result = firmware.get_current_firmware()
            assert result is None

    def test_get_current_firmware_single_device(self):
        """Test getting firmware from single device."""
        mock_hw = {
            'devices': [
                {
                    'index': 0,
                    'type': 'P300C',
                    'firmware': 0x13040200,  # 19.4.2.0
                },
            ],
        }

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            result = firmware.get_current_firmware()

            assert result is not None
            assert result['primary_version'] == "19.4.2"
            assert len(result['devices']) == 1

            dev = result['devices'][0]
            assert dev['index'] == 0
            assert dev['type'] == 'P300C'
            assert dev['firmware_hex'] == "0x13040200"
            assert dev['firmware_version'] == "19.4.2.0"
            assert dev['firmware_display'] == "19.4.2"

    def test_get_current_firmware_multi_device(self):
        """Test getting firmware from multiple devices."""
        mock_hw = {
            'devices': [
                {
                    'index': 0,
                    'type': 'P300C',
                    'firmware': 0x13040200,
                },
                {
                    'index': 1,
                    'type': 'P300C',
                    'firmware': 0x13040200,
                },
            ],
        }

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            result = firmware.get_current_firmware()

            assert result is not None
            assert result['primary_version'] == "19.4.2"
            assert len(result['devices']) == 2

    def test_get_current_firmware_hex_string(self):
        """Test parsing firmware from hex string."""
        mock_hw = {
            'devices': [
                {
                    'index': 0,
                    'type': 'N150',
                    'firmware': '0x13040200',  # String format
                },
            ],
        }

        with patch('tt.utils.hardware.detect_hardware', return_value=mock_hw):
            result = firmware.get_current_firmware()

            assert result is not None
            assert result['primary_version'] == "19.4.2"


class TestListAvailableFirmware:
    """Test listing available firmware from GitHub."""

    def test_list_available_firmware_success(self):
        """Test successful firmware list from GitHub API."""
        mock_releases = [
            {
                'tag_name': 'v19.4.2',
                'published_at': '2026-01-05T12:34:56Z',
                'assets': [
                    {
                        'name': 'fw_pack-80.140.41.0.fwbundle',
                        'browser_download_url': 'https://github.com/.../fw_pack-80.140.41.0.fwbundle',
                    },
                ],
            },
            {
                'tag_name': 'v19.4.1',
                'published_at': '2025-12-19T10:20:30Z',
                'assets': [
                    {
                        'name': 'fw_pack-80.140.40.0.fwbundle',
                        'browser_download_url': 'https://github.com/.../fw_pack-80.140.40.0.fwbundle',
                    },
                ],
            },
        ]

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_releases).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = firmware.list_available_firmware()

            assert len(result) == 2
            assert result[0]['version'] == '19.4.2'  # Sorted newest first
            assert result[0]['tag'] == 'v19.4.2'
            assert result[0]['date'] == '2026-01-05'
            assert 'url' in result[0]

    def test_list_available_firmware_network_error(self):
        """Test network error when fetching firmware list."""
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('Network error')):
            with pytest.raises(urllib.error.URLError):
                firmware.list_available_firmware()

    def test_list_available_firmware_filters_invalid(self):
        """Test that invalid releases are filtered out."""
        mock_releases = [
            {
                'tag_name': 'v19.4.2',
                'published_at': '2026-01-05T12:34:56Z',
                'assets': [
                    {
                        'name': 'fw_pack-80.140.41.0.fwbundle',
                        'browser_download_url': 'https://github.com/.../fw_pack.fwbundle',
                    },
                ],
            },
            {
                'tag_name': 'invalid-tag',  # No 'v' prefix
                'published_at': '2025-12-19T10:20:30Z',
                'assets': [],
            },
            {
                'tag_name': 'v19.4.1',
                'published_at': '2025-12-18T10:20:30Z',
                'assets': [
                    {
                        'name': 'some-other-file.txt',  # No .fwbundle
                        'browser_download_url': 'https://github.com/.../file.txt',
                    },
                ],
            },
        ]

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_releases).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = firmware.list_available_firmware()

            # Only the first valid release should be included
            assert len(result) == 1
            assert result[0]['version'] == '19.4.2'


class TestGetLatestFirmware:
    """Test getting latest firmware version."""

    def test_get_latest_firmware_success(self):
        """Test getting latest firmware."""
        mock_list = [
            {'tag': 'v19.4.2', 'version': '19.4.2', 'date': '2026-01-05'},
            {'tag': 'v19.4.1', 'version': '19.4.1', 'date': '2025-12-19'},
        ]

        with patch('tt.utils.firmware.list_available_firmware', return_value=mock_list):
            result = firmware.get_latest_firmware()

            assert result is not None
            assert result['version'] == '19.4.2'

    def test_get_latest_firmware_empty_list(self):
        """Test getting latest when no firmware available."""
        with patch('tt.utils.firmware.list_available_firmware', return_value=[]):
            result = firmware.get_latest_firmware()
            assert result is None


class TestCompareVersions:
    """Test version comparison."""

    def test_compare_versions_greater(self):
        """Test v1 > v2."""
        assert firmware.compare_versions("19.4.2", "19.4.1") == 1

    def test_compare_versions_less(self):
        """Test v1 < v2."""
        assert firmware.compare_versions("19.4.1", "19.4.2") == -1

    def test_compare_versions_equal(self):
        """Test v1 == v2."""
        assert firmware.compare_versions("19.4.2", "19.4.2") == 0

    def test_compare_versions_major_difference(self):
        """Test major version difference."""
        assert firmware.compare_versions("20.0.0", "19.4.2") == 1
        assert firmware.compare_versions("19.4.2", "20.0.0") == -1

    def test_compare_versions_with_v_prefix(self):
        """Test comparison with 'v' prefix."""
        assert firmware.compare_versions("v19.4.2", "v19.4.1") == 1

    def test_compare_versions_different_lengths(self):
        """Test comparison with different version lengths."""
        assert firmware.compare_versions("19.4", "19.4.0") == 0
        assert firmware.compare_versions("19.4.1", "19.4") == 1


class TestGetFirmwareCompatibility:
    """Test firmware compatibility checks."""

    def test_compatibility_blackhole_compatible(self):
        """Test compatible firmware for Blackhole hardware."""
        result = firmware.get_firmware_compatibility("19.4.2", "P300C")

        assert result['compatible'] is True
        assert result['arch'] == 'blackhole'
        assert result['warning'] is None

    def test_compatibility_blackhole_incompatible(self):
        """Test incompatible firmware for Blackhole hardware."""
        result = firmware.get_firmware_compatibility("19.2.0", "P300C")

        assert result['compatible'] is False
        assert result['arch'] == 'blackhole'
        assert result['warning'] is not None
        assert "19.2.0" in result['warning']
        assert "19.4.0" in result['warning']

    def test_compatibility_wormhole_compatible(self):
        """Test compatible firmware for Wormhole hardware."""
        result = firmware.get_firmware_compatibility("19.4.0", "N150")

        assert result['compatible'] is True
        assert result['arch'] == 'wormhole'
        assert result['warning'] is None

    def test_compatibility_unknown_hardware(self):
        """Test compatibility for unknown hardware type."""
        result = firmware.get_firmware_compatibility("19.4.2", "UNKNOWN")

        assert result['compatible'] is True  # Assume compatible
        assert result['arch'] == 'unknown'
        assert result['warning'] is None


class TestGetRecommendedFirmware:
    """Test getting recommended firmware for hardware."""

    def test_get_recommended_firmware_blackhole(self):
        """Test getting recommended firmware for Blackhole."""
        mock_list = [
            {'tag': 'v19.4.2', 'version': '19.4.2', 'date': '2026-01-05'},
            {'tag': 'v19.4.0', 'version': '19.4.0', 'date': '2025-12-16'},
            {'tag': 'v19.2.0', 'version': '19.2.0', 'date': '2025-12-01'},  # Too old
        ]

        with patch('tt.utils.firmware.list_available_firmware', return_value=mock_list):
            result = firmware.get_recommended_firmware("P300C")

            # Should only include 19.4.x versions
            assert len(result) == 2
            assert result[0]['version'] == '19.4.2'
            assert result[1]['version'] == '19.4.0'

    def test_get_recommended_firmware_wormhole(self):
        """Test getting recommended firmware for Wormhole."""
        mock_list = [
            {'tag': 'v19.4.2', 'version': '19.4.2', 'date': '2026-01-05'},
            {'tag': 'v19.0.0', 'version': '19.0.0', 'date': '2025-11-01'},
            {'tag': 'v18.9.0', 'version': '18.9.0', 'date': '2025-10-01'},  # Too old
        ]

        with patch('tt.utils.firmware.list_available_firmware', return_value=mock_list):
            result = firmware.get_recommended_firmware("N150")

            # Should include all 19.x versions
            assert len(result) == 2
            assert result[0]['version'] == '19.4.2'
            assert result[1]['version'] == '19.0.0'


class TestDownloadFirmware:
    """Test firmware download."""

    def test_download_firmware_success(self, tmp_path):
        """Test successful firmware download."""
        mock_list = [
            {
                'tag': 'v19.4.2',
                'version': '19.4.2',
                'name': 'fw_pack-80.140.41.0.fwbundle',
                'url': 'https://github.com/.../fw_pack.fwbundle',
            },
        ]

        with patch('tt.utils.firmware.list_available_firmware', return_value=mock_list):
            with patch('urllib.request.urlretrieve') as mock_retrieve:
                # Mock successful download
                def mock_download(url, path, reporthook=None):
                    # Create the temp file
                    Path(path).write_text("firmware data")

                mock_retrieve.side_effect = mock_download

                result = firmware.download_firmware("19.4.2", cache_dir=tmp_path, show_progress=False)

                assert result.exists()
                assert result.name == 'fw_pack-80.140.41.0.fwbundle'
                mock_retrieve.assert_called_once()

    def test_download_firmware_already_cached(self, tmp_path):
        """Test download when firmware already cached."""
        # Create cached file
        cached_file = tmp_path / "fw_pack-80.140.41.0.fwbundle"
        cached_file.write_text("existing firmware")

        mock_list = [
            {
                'tag': 'v19.4.2',
                'version': '19.4.2',
                'name': 'fw_pack-80.140.41.0.fwbundle',
                'url': 'https://github.com/.../fw_pack.fwbundle',
            },
        ]

        with patch('tt.utils.firmware.list_available_firmware', return_value=mock_list):
            with patch('urllib.request.urlretrieve') as mock_retrieve:
                result = firmware.download_firmware("19.4.2", cache_dir=tmp_path, show_progress=False)

                assert result == cached_file
                mock_retrieve.assert_not_called()  # Should not download

    def test_download_firmware_version_not_found(self, tmp_path):
        """Test download with invalid version."""
        with patch('tt.utils.firmware.list_available_firmware', return_value=[]):
            with pytest.raises(ValueError, match="not found"):
                firmware.download_firmware("99.99.99", cache_dir=tmp_path, show_progress=False)

    def test_download_firmware_network_error(self, tmp_path):
        """Test download with network error."""
        mock_list = [
            {
                'tag': 'v19.4.2',
                'version': '19.4.2',
                'name': 'fw_pack-80.140.41.0.fwbundle',
                'url': 'https://github.com/.../fw_pack.fwbundle',
            },
        ]

        with patch('tt.utils.firmware.list_available_firmware', return_value=mock_list):
            with patch('urllib.request.urlretrieve', side_effect=urllib.error.URLError('Network error')):
                with pytest.raises(urllib.error.URLError):
                    firmware.download_firmware("19.4.2", cache_dir=tmp_path, show_progress=False)


class TestHasTtFlash:
    """Test tt-flash availability detection."""

    def test_has_tt_flash_available(self):
        """Test when tt-flash is available."""
        with patch('shutil.which', return_value='/usr/bin/tt-flash'):
            assert firmware.has_tt_flash() is True

    def test_has_tt_flash_unavailable(self):
        """Test when tt-flash is not available."""
        with patch('shutil.which', return_value=None):
            assert firmware.has_tt_flash() is False


class TestFlashFirmware:
    """Test firmware flashing."""

    def test_flash_firmware_success(self, tmp_path):
        """Test successful firmware flash."""
        bundle_path = tmp_path / "firmware.fwbundle"
        bundle_path.write_text("firmware data")

        with patch('tt.utils.firmware.has_tt_flash', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)

                result = firmware.flash_firmware(bundle_path)

                assert result == 0
                mock_run.assert_called_once()

                # Check command includes bundle path
                cmd = mock_run.call_args[0][0]
                assert 'tt-flash' in cmd
                assert 'flash' in cmd
                assert str(bundle_path) in cmd

    def test_flash_firmware_with_flags(self, tmp_path):
        """Test firmware flash with optional flags."""
        bundle_path = tmp_path / "firmware.fwbundle"
        bundle_path.write_text("firmware data")

        with patch('tt.utils.firmware.has_tt_flash', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)

                result = firmware.flash_firmware(
                    bundle_path,
                    force=True,
                    no_reset=True,
                    allow_downgrades=True,
                )

                assert result == 0

                # Check flags are included
                cmd = mock_run.call_args[0][0]
                assert '--force' in cmd
                assert '--no-reset' in cmd
                assert '--allow-downgrades' in cmd

    def test_flash_firmware_no_tt_flash(self, tmp_path):
        """Test flash when tt-flash not available."""
        bundle_path = tmp_path / "firmware.fwbundle"
        bundle_path.write_text("firmware data")

        with patch('tt.utils.firmware.has_tt_flash', return_value=False):
            with pytest.raises(FileNotFoundError, match="tt-flash"):
                firmware.flash_firmware(bundle_path)

    def test_flash_firmware_bundle_not_found(self, tmp_path):
        """Test flash when bundle doesn't exist."""
        bundle_path = tmp_path / "nonexistent.fwbundle"

        with patch('tt.utils.firmware.has_tt_flash', return_value=True):
            with pytest.raises(FileNotFoundError, match="bundle not found"):
                firmware.flash_firmware(bundle_path)


class TestVerifyFirmware:
    """Test firmware verification."""

    def test_verify_firmware_success(self, tmp_path):
        """Test successful firmware verification."""
        bundle_path = tmp_path / "firmware.fwbundle"
        bundle_path.write_text("firmware data")

        with patch('tt.utils.firmware.has_tt_flash', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)

                result = firmware.verify_firmware(bundle_path)

                assert result == 0
                mock_run.assert_called_once()

                # Check command
                cmd = mock_run.call_args[0][0]
                assert 'tt-flash' in cmd
                assert 'verify' in cmd
                assert str(bundle_path) in cmd

    def test_verify_firmware_no_bundle(self):
        """Test verification without bundle (verify current)."""
        with patch('tt.utils.firmware.has_tt_flash', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)

                result = firmware.verify_firmware(None)

                assert result == 0

                # Check command doesn't include bundle path
                cmd = mock_run.call_args[0][0]
                assert 'tt-flash' in cmd
                assert 'verify' in cmd
                assert len(cmd) == 2  # Only ['tt-flash', 'verify']

    def test_verify_firmware_no_tt_flash(self, tmp_path):
        """Test verify when tt-flash not available."""
        bundle_path = tmp_path / "firmware.fwbundle"
        bundle_path.write_text("firmware data")

        with patch('tt.utils.firmware.has_tt_flash', return_value=False):
            with pytest.raises(FileNotFoundError, match="tt-flash"):
                firmware.verify_firmware(bundle_path)
