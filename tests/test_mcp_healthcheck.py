# SPDX-License-Identifier: GPL-3.0-or-later
import json
from unittest.mock import MagicMock, patch

import pytest

SAMPLE_HEALTHCHECK_JSON = json.dumps([
    {"source": "ipahealthcheck.ipa.certs", "check": "IPADogtagCertsMatchCheck",
     "result": "SUCCESS", "uuid": "abc", "kw": {}},
    {"source": "ipahealthcheck.ipa.certs", "check": "IPACertExpiration",
     "result": "ERROR", "uuid": "def",
     "kw": {"key": "caSigningCert", "days": 30}},
])


def test_get_kerberos_principal_parses_klist():
    from freeipa_mcp.tools.healthcheck import _get_kerberos_principal
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = (
        "Ticket cache: FILE:/tmp/krb5cc_1000\n"
        "Default principal: admin@EXAMPLE.COM\n\n"
        "Valid starting     Expires            Service principal\n"
    )
    with patch("subprocess.run", return_value=mock_result):
        assert _get_kerberos_principal() == "admin"


def test_get_kerberos_principal_no_ticket_raises():
    from freeipa_mcp.tools.healthcheck import _get_kerberos_principal
    mock_result = MagicMock()
    mock_result.returncode = 1
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="No Kerberos ticket"):
            _get_kerberos_principal()


def test_format_as_markdown_sections_and_counts():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown
    md = _format_as_markdown(SAMPLE_HEALTHCHECK_JSON)
    assert "# IPA Healthcheck Results" in md
    assert "## Summary" in md
    assert "Total Checks:** 2" in md
    assert "Errors:** 1" in md
    assert "Success:** 1" in md
    assert "## ERROR Results" in md
    assert "## SUCCESS Results" in md
    assert "ipahealthcheck.ipa.certs - IPACertExpiration" in md
    assert "## Recommendations" in md


def test_format_as_markdown_kw_snake_to_title():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown
    data = json.dumps([{
        "source": "src", "check": "chk", "result": "ERROR",
        "kw": {"msg": "bad cert", "expiration_date": "2025-01-01", "ca": "ipa"},
    }])
    md = _format_as_markdown(data)
    assert "**Message:**" in md
    assert "**Expiration Date:**" in md
    assert "**CA:**" in md


def test_format_as_markdown_empty_returns_no_results():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown
    md = _format_as_markdown("[]")
    assert "No healthcheck results found" in md


def test_format_as_markdown_all_success_no_recommendations():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown
    data = json.dumps([
        {"source": "s", "check": "c", "result": "SUCCESS", "kw": {}},
    ])
    md = _format_as_markdown(data)
    assert "All checks passed" in md
    assert "Recommendations" not in md


def test_format_as_markdown_invalid_json_returns_raw():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown
    assert _format_as_markdown("not json") == "not json"


def test_snake_to_title():
    from freeipa_mcp.tools.healthcheck import _snake_to_title
    assert _snake_to_title("config_file") == "Config File"
    assert _snake_to_title("expiration_date") == "Expiration Date"
    assert _snake_to_title("msg") == "Message"
    assert _snake_to_title("ca") == "CA"
    assert _snake_to_title("ocsp_signing_cert") == "Ocsp Signing Cert"


async def test_execute_passwordless_skips_gui():
    principal_path = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    ssh_path = "freeipa_mcp.tools.healthcheck._exec_ssh"
    gui_path = "freeipa_mcp.tools.sudo_gui.get_sudo_password"
    with (
        patch(principal_path, return_value="admin"),
        patch(ssh_path, return_value=SAMPLE_HEALTHCHECK_JSON),
        patch(gui_path) as mock_gui,
    ):
        from freeipa_mcp.tools.healthcheck import execute
        result = await execute(
            server_hostname="ipa.example.com", mode="live", passwordless=True
        )
    mock_gui.assert_not_called()
    assert "Healthcheck" in result or "ERROR" in result


async def test_execute_non_passwordless_shows_gui():
    principal_path = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    ssh_path = "freeipa_mcp.tools.healthcheck._exec_ssh"
    gui_path = "freeipa_mcp.tools.sudo_gui.get_sudo_password"
    with (
        patch(principal_path, return_value="admin"),
        patch(ssh_path, return_value=SAMPLE_HEALTHCHECK_JSON),
        patch(gui_path, return_value="s3cr3t") as mock_gui,
    ):
        from freeipa_mcp.tools.healthcheck import execute
        result = await execute(
            server_hostname="ipa.example.com", mode="live", passwordless=False
        )
    mock_gui.assert_called_once_with("admin", "ipa.example.com")
    assert "Healthcheck" in result or "ERROR" in result


async def test_execute_gui_cancel_raises():
    principal_path = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    gui_path = "freeipa_mcp.tools.sudo_gui.get_sudo_password"
    with (
        patch(principal_path, return_value="admin"),
        patch(gui_path, side_effect=RuntimeError("Sudo authentication cancelled")),
    ):
        from freeipa_mcp.tools.healthcheck import execute
        with pytest.raises(RuntimeError, match="cancelled"):
            await execute(server_hostname="ipa.example.com", passwordless=False)


async def test_exec_ssh_uses_sudo_with_password():
    from freeipa_mcp.tools.healthcheck import _exec_ssh
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "output line\n0\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        _exec_ssh("host", "user", "ipa-healthcheck", password="secret")
    call_args = mock_run.call_args[0][0]
    remote_cmd = call_args[-1]
    assert "sudo --stdin" in remote_cmd
    assert "secret" in remote_cmd


async def test_exec_ssh_uses_sudo_without_password():
    from freeipa_mcp.tools.healthcheck import _exec_ssh
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "output line\n0\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        _exec_ssh("host", "user", "ipa-healthcheck", password=None)
    call_args = mock_run.call_args[0][0]
    remote_cmd = call_args[-1]
    assert "sudo --stdin" not in remote_cmd
    assert "sudo" in remote_cmd
