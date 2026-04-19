# SPDX-License-Identifier: GPL-3.0-or-later
from unittest.mock import MagicMock, patch

import pytest


def test_build_principal_adds_realm():
    from freeipa_mcp.tools.login import _build_principal
    assert _build_principal("admin", "EXAMPLE.COM") == "admin@EXAMPLE.COM"


def test_build_principal_preserves_full_principal():
    from freeipa_mcp.tools.login import _build_principal
    assert _build_principal("admin@OTHER.COM", "EXAMPLE.COM") == "admin@OTHER.COM"


def test_detect_realm_from_saved_hostname():
    from freeipa_mcp.tools.login import _detect_realm
    with (
        patch(
            "freeipa_mcp.tools.login.load_server_config", return_value="ipa.example.com"
        ),
        patch("freeipa_mcp.tools.login._read_realm_from_config", return_value=None),
    ):
        realm = _detect_realm(None)
    assert realm == "EXAMPLE.COM"


def test_detect_realm_no_config_raises():
    from freeipa_mcp.tools.login import _detect_realm
    with patch("freeipa_mcp.tools.login.load_server_config", return_value=None), \
         patch("freeipa_mcp.tools.login._read_realm_from_config", return_value=None):
        with pytest.raises(ValueError, match="Cannot detect Kerberos realm"):
            _detect_realm(None)


def test_login_missing_credentials_raises():
    from freeipa_mcp.tools.login import _login_blocking
    with patch("freeipa_mcp.tools.login._detect_realm", return_value="EXAMPLE.COM"):
        with pytest.raises(ValueError, match="username and password are required"):
            _login_blocking(None, None, None, "7d", None)


def test_kinit_failure_raises():
    from freeipa_mcp.tools.login import _kinit
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "kinit: Clients credentials have been revoked"
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="kinit failed"):
            _kinit("admin@EXAMPLE.COM", "wrongpass", "7d")


async def test_execute_success():
    with patch(
        "freeipa_mcp.tools.login._login_blocking",
        return_value="Authentication successful\nPrincipal: admin@EXAMPLE.COM",
    ):
        from freeipa_mcp.tools.login import execute
        result = await execute(username="admin", password="secret", realm="EXAMPLE.COM")
    assert "Authentication successful" in result
