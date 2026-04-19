# SPDX-License-Identifier: GPL-3.0-or-later
import json
from unittest.mock import MagicMock, patch

import pytest

SAMPLE_HEALTHCHECK_JSON = json.dumps([
    {"source": "ipahealthcheck.ipa.certs", "check": "IPADogtagCertsMatchCheck",
     "result": "SUCCESS", "uuid": "abc", "severity": "SUCCESS", "kw": {}},
    {"source": "ipahealthcheck.ipa.certs", "check": "IPACertExpiration",
     "result": "ERROR", "uuid": "def", "severity": "ERROR",
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


def test_format_as_markdown_counts_severities():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown
    md = _format_as_markdown(SAMPLE_HEALTHCHECK_JSON)
    assert "ERROR" in md
    assert "SUCCESS" in md
    assert "IPACertExpiration" in md


def test_format_as_markdown_invalid_json_returns_raw():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown
    assert _format_as_markdown("not json") == "not json"


async def test_execute_live_passwordless():
    principal_path = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    ssh_path = "freeipa_mcp.tools.healthcheck._exec_ssh"
    with (
        patch(principal_path, return_value="admin"),
        patch(ssh_path, return_value=SAMPLE_HEALTHCHECK_JSON),
    ):
        from freeipa_mcp.tools.healthcheck import execute
        result = await execute(
            server_hostname="ipa.example.com", mode="live", passwordless=True
        )
    assert "Healthcheck" in result or "ERROR" in result


async def test_execute_non_passwordless_raises():
    from freeipa_mcp.tools.healthcheck import execute
    target = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    with patch(target, return_value="admin"):
        with pytest.raises(ValueError, match="passwordless"):
            await execute(
                server_hostname="ipa.example.com", mode="live", passwordless=False
            )
