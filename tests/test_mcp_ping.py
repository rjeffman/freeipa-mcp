# SPDX-License-Identifier: GPL-3.0-or-later
from unittest.mock import MagicMock, patch

import pytest


async def test_ping_returns_formatted_summary():
    mock_client = MagicMock()
    mock_client.ping.return_value = {
        "summary": "IPA server version 4.9.8. API version 2.251"
    }
    with patch("freeipa_mcp.tools.ping.get_client", return_value=mock_client):
        from freeipa_mcp.tools.ping import execute

        result = await execute()
    assert "IPA server version 4.9.8" in result
    assert result.startswith("---")
    assert result.endswith("---")


async def test_ping_ipa_confdir_ignored():
    mock_client = MagicMock()
    mock_client.ping.return_value = {"summary": "pong"}
    with patch("freeipa_mcp.tools.ping.get_client", return_value=mock_client):
        from freeipa_mcp.tools.ping import execute

        result = await execute(ipa_confdir="/some/path")
    assert "pong" in result


async def test_ping_no_server_raises():
    with patch(
        "freeipa_mcp.tools.ping.get_client",
        side_effect=RuntimeError("No FreeIPA server configured"),
    ):
        from freeipa_mcp.tools.ping import execute

        with pytest.raises(RuntimeError, match="No FreeIPA server configured"):
            await execute()
