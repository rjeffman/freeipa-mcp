# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
import os
import re
import subprocess
from pathlib import Path

from .common import load_server_config
from .login_gui import get_login_credentials, has_display


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


def _get_available_principals() -> list[dict[str, str | bool]]:
    """
    Get list of cached Kerberos principals with renewal info.

    Returns list of dicts with 'principal' and 'renewable' keys.
    """
    result = subprocess.run(["klist", "-A"], capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        return []

    principals = []
    current_principal = None
    is_renewable = False

    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Default principal:"):
            current_principal = line.split(":", 1)[1].strip()
        elif "renew until" in line.lower():
            is_renewable = True
        elif line.startswith("Ticket cache:") and current_principal:
            principals.append(
                {
                    "principal": current_principal,
                    "renewable": is_renewable,
                }
            )
            current_principal = None
            is_renewable = False

    # Handle last principal if file ends
    if current_principal:
        principals.append(
            {
                "principal": current_principal,
                "renewable": is_renewable,
            }
        )

    return principals


def _try_renew_ticket(principal: str) -> bool:
    """
    Attempt to renew an existing Kerberos ticket.

    Returns True if renewal succeeded, False otherwise.
    """
    result = subprocess.run(
        ["kinit", "-R", principal],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode == 0


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
    result = subprocess.run(["klist"], capture_output=True, text=True, timeout=10)
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
    realm: str | None,
    renewable_lifetime: str,
    ipa_confdir: str | None,
) -> str:
    detected_realm = realm or _detect_realm(ipa_confdir)

    if not has_display():
        raise RuntimeError(
            "No graphical display available for authentication. "
            "Set DISPLAY/WAYLAND_DISPLAY or run kinit manually."
        )

    # Get available principals and check for renewable tickets
    available_principals = _get_available_principals()

    # Try to get credentials via GUI
    username, password = get_login_credentials(
        username, detected_realm, available_principals
    )

    principal = _build_principal(username, detected_realm)

    # Check if we can renew instead of using password
    for p in available_principals:
        if p["principal"] == principal and p["renewable"]:
            if _try_renew_ticket(principal):
                info = _validate_tgt(principal)
                return (
                    f"Authentication successful (ticket renewed)\n"
                    f"Principal: {info.get('principal', principal)}\n"
                    f"Renew until: {info.get('renew_until', renewable_lifetime)}"
                )
            # Renewal failed, fall through to password auth
            break

    # Use password for new ticket or if renewal failed
    _kinit(principal, password, renewable_lifetime)
    info = _validate_tgt(principal)
    return (
        f"Authentication successful\n"
        f"Principal: {info.get('principal', principal)}\n"
        f"Renew until: {info.get('renew_until', renewable_lifetime)}"
    )


async def execute(
    username: str | None = None,
    realm: str | None = None,
    renewable_lifetime: str = "7d",
    ipa_confdir: str | None = None,
) -> str:
    """
    Authenticate to FreeIPA using Kerberos.

    Opens a secure GTK4 dialog to obtain credentials. Password is never
    passed as a parameter for security reasons.

    Args:
        username: Optional username (dialog will pre-fill if provided)
        realm: Optional Kerberos realm (auto-detected if not provided)
        renewable_lifetime: Ticket renewable lifetime (default: 7d)
        ipa_confdir: Optional IPA config directory path

    Returns:
        Authentication success message with principal and expiry info
    """
    return await asyncio.to_thread(
        _login_blocking, username, realm, renewable_lifetime, ipa_confdir
    )
