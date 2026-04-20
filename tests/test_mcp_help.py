# SPDX-License-Identifier: GPL-3.0-or-later
from unittest.mock import MagicMock, patch

_DEFAULT_CONTENT = (
    "# Help\n\nSome content here for caching purposes — "
    "long enough to exceed fifty bytes."
)


def _make_client(markdown_content=_DEFAULT_CONTENT):
    mock_client = MagicMock()
    mock_client.ping.return_value = {
        "summary": "IPA server version 4.9.8. API version 2.251"
    }
    mock_client.help_markdown.return_value = markdown_content
    return mock_client


async def test_execute_topics_calls_help_markdown_no_arg(tmp_path):
    mock_client = _make_client()
    with (
        patch("freeipa_mcp.tools.help.get_client", return_value=mock_client),
        patch("freeipa_mcp.tools.help.get_cache_dir", return_value=tmp_path),
    ):
        from freeipa_mcp.tools.help import execute

        result = await execute(subject="topics")
    mock_client.help_markdown.assert_called_once_with()
    assert "Help" in result


async def test_execute_commands_calls_help_markdown_commands(tmp_path):
    mock_client = _make_client()
    with (
        patch("freeipa_mcp.tools.help.get_client", return_value=mock_client),
        patch("freeipa_mcp.tools.help.get_cache_dir", return_value=tmp_path),
    ):
        from freeipa_mcp.tools.help import execute

        await execute(subject="commands")
    mock_client.help_markdown.assert_called_once_with("commands")


async def test_execute_uses_disk_cache(tmp_path):
    mock_client = _make_client()
    with (
        patch("freeipa_mcp.tools.help.get_client", return_value=mock_client),
        patch("freeipa_mcp.tools.help.get_cache_dir", return_value=tmp_path),
    ):
        from freeipa_mcp.tools.help import execute

        await execute(subject="topics")
        await execute(subject="topics")
    assert mock_client.help_markdown.call_count == 1


async def test_force_refresh_bypasses_cache(tmp_path):
    mock_client = _make_client()
    with (
        patch("freeipa_mcp.tools.help.get_client", return_value=mock_client),
        patch("freeipa_mcp.tools.help.get_cache_dir", return_value=tmp_path),
    ):
        from freeipa_mcp.tools.help import execute

        await execute(subject="topics")
        await execute(subject="topics", force_refresh=True)
    assert mock_client.help_markdown.call_count == 2


async def test_execute_converts_cli_name_to_api_name(tmp_path):
    mock_client = _make_client()
    with (
        patch("freeipa_mcp.tools.help.get_client", return_value=mock_client),
        patch("freeipa_mcp.tools.help.get_cache_dir", return_value=tmp_path),
    ):
        from freeipa_mcp.tools.help import execute

        await execute(subject="user-show")
    mock_client.help_markdown.assert_called_once_with("user_show")
