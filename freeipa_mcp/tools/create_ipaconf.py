# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
import re

from .common import get_client, save_server_config


def validate_fqdn(hostname: str) -> None:
    if len(hostname) > 253:
        raise ValueError(f"Hostname too long: {hostname!r}")
    labels = hostname.rstrip(".").split(".")
    if len(labels) < 2:
        raise ValueError(f"Hostname must have at least 2 labels: {hostname!r}")
    label_re = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$")
    for label in labels:
        if not label_re.match(label):
            raise ValueError(f"Invalid hostname label: {label!r}")


def _configure_blocking(server_hostname: str) -> str:
    validate_fqdn(server_hostname)
    save_server_config(server_hostname)
    client = get_client()
    result = client.ping()
    summary = result.get("summary", "connected")
    return (
        f"FreeIPA server configured: {server_hostname}\n"
        f"Connection test: {summary}\n"
        "CA certificate cached and ready."
    )


async def execute(
    server_hostname: str,
    realm: str | None = None,
    domain: str | None = None,
) -> str:
    return await asyncio.to_thread(_configure_blocking, server_hostname)
