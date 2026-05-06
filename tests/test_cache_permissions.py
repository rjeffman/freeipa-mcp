# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for secure cache file permissions."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestCacheFilePermissions:
    """Test that cache files are created with secure permissions (0600/0700)."""

    def test_ipaclient_ca_cert_cache_permissions(self, tmp_path):
        """Verify CA certificate cache files are created with mode 0600."""
        from freeipa_mcp.ipaclient import IPAThinClient

        cache_dir = tmp_path / "cache" / "ipa.example.com"

        # Mock successful CA cert download
        mock_response = Mock()
        mock_response.text = (
            "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"
        )
        mock_response.raise_for_status = Mock()

        client = IPAThinClient("ipa.example.com")

        with (
            patch.object(client, "get_cache_dir", return_value=cache_dir),
            patch("requests.get", return_value=mock_response),
        ):
            result_path = client._get_ca_cert()

        # Result path tells us where the file was actually created
        result_path = Path(result_path)

        # Verify file permissions (0600 = rw-------)
        # This is the critical security check - files contain sensitive data
        assert result_path.exists()
        file_mode = result_path.stat().st_mode & 0o777
        assert file_mode == 0o600, f"Expected 0600, got {oct(file_mode)}"

    def test_vault_cache_permissions(self, tmp_path):
        """Verify vault cache files are created with mode 0600."""
        from freeipa_mcp.vault_cache import KRAConfigCache

        cache_dir = tmp_path / ".cache" / "freeipa-mcp-py" / "ipa.example.com"
        cache_file = cache_dir / "kra-config.json"

        mock_client = Mock()
        mock_client.get_cache_dir.return_value = cache_dir

        cache = KRAConfigCache(mock_client)
        cache.save(cert_der=b"test_cert_data", algo="aes-128-cbc")

        # Verify directory permissions (0700)
        assert cache_dir.exists()
        dir_mode = cache_dir.stat().st_mode & 0o777
        assert dir_mode == 0o700, f"Expected 0700, got {oct(dir_mode)}"

        # Verify file permissions (0600)
        assert cache_file.exists()
        file_mode = cache_file.stat().st_mode & 0o777
        assert file_mode == 0o600, f"Expected 0600, got {oct(file_mode)}"

    def test_server_config_permissions(self, tmp_path):
        """Verify server config files are created with mode 0600."""
        from freeipa_mcp.tools.common import save_server_config

        with patch("freeipa_mcp.tools.common.get_cache_dir", return_value=tmp_path):
            save_server_config("ipa.example.com")

        config_dir = tmp_path / "config"
        config_file = config_dir / "server"

        # Verify directory permissions (0700)
        assert config_dir.exists()
        dir_mode = config_dir.stat().st_mode & 0o777
        assert dir_mode == 0o700, f"Expected 0700, got {oct(dir_mode)}"

        # Verify file permissions (0600)
        assert config_file.exists()
        file_mode = config_file.stat().st_mode & 0o777
        assert file_mode == 0o600, f"Expected 0600, got {oct(file_mode)}"

    def test_umask_restoration_on_exception(self, tmp_path):
        """Verify umask is restored even if file creation fails."""
        from freeipa_mcp.tools.common import save_server_config

        # Save original umask
        original_umask = os.umask(0)
        os.umask(original_umask)

        # Force a failure during file write
        with (
            patch("freeipa_mcp.tools.common.get_cache_dir", return_value=tmp_path),
            patch("pathlib.Path.write_text", side_effect=PermissionError("Test error")),
            pytest.raises(PermissionError),
        ):
            save_server_config("ipa.example.com")

        # Verify umask was restored
        current_umask = os.umask(0)
        os.umask(current_umask)
        assert current_umask == original_umask, "umask was not restored after exception"
