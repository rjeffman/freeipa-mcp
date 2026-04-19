# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio

from .common import get_client


async def execute(ipa_confdir: str | None = None) -> str:
    def _blocking() -> str:
        client = get_client()
        result = client.ping()
        summary = result.get("summary", "IPA server is up")
        return f"---\n{summary}\n---"

    return await asyncio.to_thread(_blocking)
