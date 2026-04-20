# SPDX-License-Identifier: GPL-3.0-or-later
import os
from unittest.mock import MagicMock, patch

import pytest


def test_has_display_with_x11():
    from freeipa_mcp.tools.login_gui import has_display

    with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
        assert has_display() is True


def test_has_display_with_wayland():
    from freeipa_mcp.tools.login_gui import has_display

    with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False):
        assert has_display() is True


def test_has_display_without_any_display():
    from freeipa_mcp.tools.login_gui import has_display

    filtered = {
        k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")
    }
    with patch.dict(os.environ, filtered, clear=True):
        assert has_display() is False


def test_get_login_credentials_no_display_raises():
    from freeipa_mcp.tools.login_gui import get_login_credentials

    with patch("freeipa_mcp.tools.login_gui.has_display", return_value=False):
        with pytest.raises(RuntimeError, match="display"):
            get_login_credentials()


def _mock_proc(returncode: int, stdout: str, stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_get_login_credentials_returns_username_and_password():
    from freeipa_mcp.tools.login_gui import get_login_credentials

    with (
        patch("freeipa_mcp.tools.login_gui.has_display", return_value=True),
        patch(
            "subprocess.run", return_value=_mock_proc(0, "admin\nmysecretpassword\n")
        ),
    ):
        username, password = get_login_credentials()
        assert username == "admin"
        assert password == "mysecretpassword"


def test_get_login_credentials_with_prefilled_username():
    from freeipa_mcp.tools.login_gui import get_login_credentials

    with (
        patch("freeipa_mcp.tools.login_gui.has_display", return_value=True),
        patch(
            "subprocess.run", return_value=_mock_proc(0, "admin\nmysecretpassword\n")
        ) as mock_run,
    ):
        get_login_credentials(username="admin", realm="EXAMPLE.COM")
        # Verify the subprocess was called with the right arguments
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "admin" in args
        assert "EXAMPLE.COM" in args


def test_get_login_credentials_with_available_principals():
    from freeipa_mcp.tools.login_gui import get_login_credentials

    principals = [
        {"principal": "admin@EXAMPLE.COM", "renewable": True},
        {"principal": "user@EXAMPLE.COM", "renewable": False},
    ]
    with (
        patch("freeipa_mcp.tools.login_gui.has_display", return_value=True),
        patch(
            "subprocess.run",
            return_value=_mock_proc(0, "admin@EXAMPLE.COM\nmysecretpassword\n"),
        ) as mock_run,
    ):
        username, password = get_login_credentials(available_principals=principals)
        assert username == "admin@EXAMPLE.COM"
        assert password == "mysecretpassword"
        # Verify principals were passed as JSON
        args = mock_run.call_args[0][0]
        import json

        assert json.dumps(principals) in args


def test_get_login_credentials_cancel_raises():
    from freeipa_mcp.tools.login_gui import get_login_credentials

    with (
        patch("freeipa_mcp.tools.login_gui.has_display", return_value=True),
        patch("subprocess.run", return_value=_mock_proc(1, "", "User cancelled")),
    ):
        with pytest.raises(RuntimeError, match="cancelled"):
            get_login_credentials()


def test_get_login_credentials_no_gtk_raises():
    from freeipa_mcp.tools.login_gui import get_login_credentials

    with (
        patch("freeipa_mcp.tools.login_gui.has_display", return_value=True),
        patch("subprocess.run", return_value=_mock_proc(3, "", "GTK4 not available")),
    ):
        with pytest.raises(RuntimeError, match="GTK4"):
            get_login_credentials()


def test_get_login_credentials_invalid_response_raises():
    from freeipa_mcp.tools.login_gui import get_login_credentials

    with (
        patch("freeipa_mcp.tools.login_gui.has_display", return_value=True),
        patch("subprocess.run", return_value=_mock_proc(0, "onlyusername")),
    ):
        with pytest.raises(RuntimeError, match="Invalid response"):
            get_login_credentials()
