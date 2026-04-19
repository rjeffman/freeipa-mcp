# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from unittest.mock import patch, MagicMock


def test_validate_fqdn_valid():
    from freeipa_mcp.tools.create_ipaconf import validate_fqdn
    validate_fqdn("ipa.example.com")
    validate_fqdn("ipa.demo1.freeipa.org")


def test_validate_fqdn_too_long():
    from freeipa_mcp.tools.create_ipaconf import validate_fqdn
    with pytest.raises(ValueError, match="too long"):
        validate_fqdn("a" * 254)


def test_validate_fqdn_single_label():
    from freeipa_mcp.tools.create_ipaconf import validate_fqdn
    with pytest.raises(ValueError, match="at least 2 labels"):
        validate_fqdn("localhost")


def test_validate_fqdn_invalid_chars():
    from freeipa_mcp.tools.create_ipaconf import validate_fqdn
    with pytest.raises(ValueError, match="Invalid hostname label"):
        validate_fqdn("ipa.exa_mple.com")


def test_validate_fqdn_leading_hyphen():
    from freeipa_mcp.tools.create_ipaconf import validate_fqdn
    with pytest.raises(ValueError, match="Invalid hostname label"):
        validate_fqdn("ipa.-example.com")


async def test_execute_saves_config_and_pings():
    mock_client = MagicMock()
    mock_client.ping.return_value = {
        "summary": "IPA server version 4.9.8. API version 2.251"
    }
    with patch("freeipa_mcp.tools.create_ipaconf.save_server_config") as mock_save, \
         patch("freeipa_mcp.tools.create_ipaconf.get_client", return_value=mock_client):
        from freeipa_mcp.tools.create_ipaconf import execute
        result = await execute(server_hostname="ipa.example.com")
    mock_save.assert_called_once_with("ipa.example.com")
    mock_client.ping.assert_called_once()
    assert "ipa.example.com" in result
    assert "4.9.8" in result


async def test_execute_invalid_fqdn_raises():
    from freeipa_mcp.tools.create_ipaconf import execute
    with pytest.raises(ValueError, match="at least 2 labels"):
        await execute(server_hostname="localhost")
