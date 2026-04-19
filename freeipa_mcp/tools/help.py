# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
import re
from pathlib import Path

from .common import get_cache_dir, get_client, to_api_name


def _parse_versions(summary: str) -> tuple[str, str]:
    m = re.search(r"IPA server version ([\d.]+)", summary)
    server_ver = m.group(1).rstrip(".") if m else "unknown"
    m = re.search(r"API version ([\d.]+)", summary)
    api_ver = m.group(1).rstrip(".") if m else "unknown"
    return server_ver, api_ver


def _get_cache_path(server_ver: str, api_ver: str, subject: str) -> Path:
    safe = subject.replace("/", "_").replace("\\", "_").replace(" ", "_")
    return get_cache_dir() / "doc" / server_ver / api_ver / f"{safe}.md"


def _help_blocking(subject: str, force_refresh: bool) -> str:
    client = get_client()
    ping_result = client.ping()
    server_ver, api_ver = _parse_versions(ping_result.get("summary", ""))
    cache_path = _get_cache_path(server_ver, api_ver, subject)

    if not force_refresh and cache_path.exists() and cache_path.stat().st_size >= 50:
        return cache_path.read_text()

    if subject == "topics":
        content = client.help_markdown()
    elif subject == "commands":
        content = client.help_markdown("commands")
    else:
        api_name = to_api_name(subject)
        try:
            content = client.help_markdown(api_name)
        except Exception:
            content = client.help_markdown(subject)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(content)
    return content


async def execute(
    subject: str,
    ipa_confdir: str | None = None,
    force_refresh: bool = False,
) -> str:
    return await asyncio.to_thread(_help_blocking, subject, force_refresh)
