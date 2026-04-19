# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
import os
import re
import subprocess
from pathlib import Path

from .common import load_server_config


def _read_realm_from_config(confdir: str | None) -> str | None:
    if not confdir:
        return None
    conf_file = Path(confdir) / "default.conf"
    if not conf_file.exists():
        return None
    for line in conf_file.read_text().splitlines():
        m = re.match(r"^\s*realm\s*=\s*(.+)", line)
        if m:
            return m.group(1).strip()
    return None


def _detect_realm(ipa_confdir: str | None) -> str:
    realm = _read_realm_from_config(ipa_confdir)
    if realm:
        return realm
    realm = _read_realm_from_config(os.environ.get("IPA_CONFDIR"))
    if realm:
        return realm
    hostname = load_server_config()
    if hostname and "." in hostname:
        domain = ".".join(hostname.split(".")[1:])
        return domain.upper()
    raise ValueError(
        "Cannot detect Kerberos realm. "
        "Run create_ipaconf first or provide realm explicitly."
    )


def _build_principal(username: str, realm: str) -> str:
    if "@" in username:
        return username
    return f"{username}@{realm}"


def _kinit(principal: str, password: str, renewable_lifetime: str) -> None:
    result = subprocess.run(
        ["kinit", "-r", renewable_lifetime, principal],
        input=password,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"kinit failed: {result.stderr.strip() or 'authentication failed'}"
        )


def _validate_tgt(principal: str) -> dict[str, str]:
    result = subprocess.run(
        ["klist"], capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        raise RuntimeError("No valid Kerberos ticket found after kinit")
    info: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.startswith("Default principal:"):
            info["principal"] = line.split(":", 1)[1].strip()
        if "renew until" in line.lower():
            info["renew_until"] = line.split("renew until", 1)[1].strip()
    return info


def _login_blocking(
    username: str | None,
    password: str | None,
    realm: str | None,
    renewable_lifetime: str,
    ipa_confdir: str | None,
) -> str:
    detected_realm = realm or _detect_realm(ipa_confdir)
    if not username or not password:
        raise ValueError(
            "username and password are required for authentication. "
            "Run kinit manually for interactive authentication."
        )
    principal = _build_principal(username, detected_realm)
    _kinit(principal, password, renewable_lifetime)
    info = _validate_tgt(principal)
    return (
        f"Authentication successful\n"
        f"Principal: {info.get('principal', principal)}\n"
        f"Renew until: {info.get('renew_until', renewable_lifetime)}"
    )


async def execute(
    username: str | None = None,
    password: str | None = None,
    realm: str | None = None,
    renewable_lifetime: str = "7d",
    ipa_confdir: str | None = None,
) -> str:
    return await asyncio.to_thread(
        _login_blocking, username, password, realm, renewable_lifetime, ipa_confdir
    )
