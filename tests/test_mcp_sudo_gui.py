# SPDX-License-Identifier: GPL-3.0-or-later
import os
from unittest.mock import MagicMock, patch

import pytest


def test_has_display_with_x11():
    from freeipa_mcp.tools.sudo_gui import has_display

    with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
        assert has_display() is True


def test_has_display_with_wayland():
    from freeipa_mcp.tools.sudo_gui import has_display

    with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False):
        assert has_display() is True


def test_has_display_without_any_display():
    from freeipa_mcp.tools.sudo_gui import has_display

    filtered = {
        k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")
    }
    with patch.dict(os.environ, filtered, clear=True):
        assert has_display() is False


def test_get_sudo_password_no_display_raises():
    from freeipa_mcp.tools.sudo_gui import get_sudo_password

    with patch("freeipa_mcp.tools.sudo_gui.has_display", return_value=False):
        with pytest.raises(RuntimeError, match="display"):
            get_sudo_password("admin", "ipa.example.com")


def _mock_proc(returncode: int, stdout: str) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def test_get_sudo_password_returns_password():
    from freeipa_mcp.tools.sudo_gui import get_sudo_password

    with (
        patch("freeipa_mcp.tools.sudo_gui.has_display", return_value=True),
        patch("subprocess.run", return_value=_mock_proc(0, "mysecretpassword\n")),
    ):
        assert get_sudo_password("admin", "ipa.example.com") == "mysecretpassword"


def test_get_sudo_password_returns_none_for_passwordless():
    from freeipa_mcp.tools.sudo_gui import get_sudo_password

    with (
        patch("freeipa_mcp.tools.sudo_gui.has_display", return_value=True),
        patch("subprocess.run", return_value=_mock_proc(0, "__PASSWORDLESS__\n")),
    ):
        assert get_sudo_password("admin", "ipa.example.com") is None


def test_get_sudo_password_cancel_raises():
    from freeipa_mcp.tools.sudo_gui import get_sudo_password

    with (
        patch("freeipa_mcp.tools.sudo_gui.has_display", return_value=True),
        patch("subprocess.run", return_value=_mock_proc(1, "")),
    ):
        with pytest.raises(RuntimeError, match="cancelled"):
            get_sudo_password("admin", "ipa.example.com")


def test_get_sudo_password_no_gtk_raises():
    from freeipa_mcp.tools.sudo_gui import get_sudo_password

    with (
        patch("freeipa_mcp.tools.sudo_gui.has_display", return_value=True),
        patch("subprocess.run", return_value=_mock_proc(3, "")),
    ):
        with pytest.raises(RuntimeError, match="GTK4"):
            get_sudo_password("admin", "ipa.example.com")
