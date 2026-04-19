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


def test_login_no_username_no_display_raises():
    from freeipa_mcp.tools.login import _login_blocking
    with (
        patch("freeipa_mcp.tools.login._detect_realm", return_value="EXAMPLE.COM"),
        patch("freeipa_mcp.tools.login.has_display", return_value=False),
    ):
        with pytest.raises(RuntimeError, match="No graphical display"):
            _login_blocking(None, None, "7d", None)


def test_login_with_username_no_display_raises():
    from freeipa_mcp.tools.login import _login_blocking
    with (
        patch("freeipa_mcp.tools.login._detect_realm", return_value="EXAMPLE.COM"),
        patch("freeipa_mcp.tools.login.has_display", return_value=False),
    ):
        with pytest.raises(RuntimeError, match="No graphical display"):
            _login_blocking("admin", None, "7d", None)


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
        result = await execute(username="admin", realm="EXAMPLE.COM")
    assert "Authentication successful" in result


def test_login_with_gui_success():
    from freeipa_mcp.tools.login import _login_blocking
    mock_result_klist_a = MagicMock()
    mock_result_klist_a.returncode = 1  # No cached tickets
    mock_result_klist_a.stdout = ""

    mock_result_kinit = MagicMock()
    mock_result_kinit.returncode = 0

    mock_result_klist = MagicMock()
    mock_result_klist.returncode = 0
    mock_result_klist.stdout = (
        "Default principal: admin@EXAMPLE.COM\n"
        "Valid starting       Expires              Service principal\n"
        "04/19/26 12:00:00  04/19/26 22:00:00  krbtgt/EXAMPLE.COM@EXAMPLE.COM\n"
        "\trenew until 04/26/26 12:00:00"
    )

    with (
        patch("freeipa_mcp.tools.login._detect_realm", return_value="EXAMPLE.COM"),
        patch("freeipa_mcp.tools.login.has_display", return_value=True),
        patch("freeipa_mcp.tools.login.get_login_credentials", return_value=("admin", "secret")),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = [mock_result_klist_a, mock_result_kinit, mock_result_klist]
        result = _login_blocking("admin", None, "7d", None)
    assert "Authentication successful" in result
    assert "admin@EXAMPLE.COM" in result


def test_get_available_principals_parses_klist():
    from freeipa_mcp.tools.login import _get_available_principals
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = (
        "Ticket cache: FILE:/tmp/krb5cc_1000\n"
        "Default principal: admin@EXAMPLE.COM\n"
        "Valid starting       Expires              Service principal\n"
        "04/19/26 12:00:00  04/19/26 22:00:00  krbtgt/EXAMPLE.COM@EXAMPLE.COM\n"
        "\trenew until 04/26/26 12:00:00\n"
        "Ticket cache: FILE:/tmp/krb5cc_1000_other\n"
        "Default principal: user@OTHER.COM\n"
        "Valid starting       Expires              Service principal\n"
        "04/19/26 12:00:00  04/19/26 22:00:00  krbtgt/OTHER.COM@OTHER.COM\n"
    )

    with patch("subprocess.run", return_value=mock_result):
        principals = _get_available_principals()

    assert len(principals) == 2
    assert principals[0]["principal"] == "admin@EXAMPLE.COM"
    assert principals[0]["renewable"] is True
    assert principals[1]["principal"] == "user@OTHER.COM"
    assert principals[1]["renewable"] is False


def test_try_renew_ticket_success():
    from freeipa_mcp.tools.login import _try_renew_ticket
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result):
        assert _try_renew_ticket("admin@EXAMPLE.COM") is True


def test_try_renew_ticket_failure():
    from freeipa_mcp.tools.login import _try_renew_ticket
    mock_result = MagicMock()
    mock_result.returncode = 1

    with patch("subprocess.run", return_value=mock_result):
        assert _try_renew_ticket("admin@EXAMPLE.COM") is False


def test_login_with_renewable_ticket_renews():
    from freeipa_mcp.tools.login import _login_blocking
    mock_result_klist_a = MagicMock()
    mock_result_klist_a.returncode = 0
    mock_result_klist_a.stdout = (
        "Ticket cache: FILE:/tmp/krb5cc_1000\n"
        "Default principal: admin@EXAMPLE.COM\n"
        "Valid starting       Expires              Service principal\n"
        "04/19/26 12:00:00  04/19/26 22:00:00  krbtgt/EXAMPLE.COM@EXAMPLE.COM\n"
        "\trenew until 04/26/26 12:00:00\n"
    )

    mock_result_renew = MagicMock()
    mock_result_renew.returncode = 0

    mock_result_klist = MagicMock()
    mock_result_klist.returncode = 0
    mock_result_klist.stdout = (
        "Default principal: admin@EXAMPLE.COM\n"
        "Valid starting       Expires              Service principal\n"
        "04/19/26 13:00:00  04/19/26 23:00:00  krbtgt/EXAMPLE.COM@EXAMPLE.COM\n"
        "\trenew until 04/26/26 12:00:00"
    )

    with (
        patch("freeipa_mcp.tools.login._detect_realm", return_value="EXAMPLE.COM"),
        patch("freeipa_mcp.tools.login.has_display", return_value=True),
        patch("freeipa_mcp.tools.login.get_login_credentials", return_value=("admin", "secret")),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = [mock_result_klist_a, mock_result_renew, mock_result_klist]
        result = _login_blocking("admin", None, "7d", None)

    assert "ticket renewed" in result
    assert "admin@EXAMPLE.COM" in result
