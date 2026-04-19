# SPDX-License-Identifier: GPL-3.0-or-later
import os
import subprocess
import sys
from pathlib import Path

_DIALOG_SCRIPT = Path(__file__).parent / "_login_dialog.py"


def has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def get_login_credentials(
    username: str | None = None,
    realm: str | None = None,
    available_principals: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    """
    Show a GTK4 dialog to obtain FreeIPA login credentials interactively.

    The dialog runs as a subprocess so GTK owns the main thread of that
    process, avoiding display-initialisation failures when called from
    an asyncio thread-pool worker.

    Args:
        username: Optional username to pre-fill
        realm: Optional realm to display
        available_principals: List of cached principals from klist

    Returns a tuple of (username, password).
    Raises RuntimeError on cancel or when a graphical display / GTK4 is unavailable.
    """
    if not has_display():
        raise RuntimeError(
            "Interactive login required but no graphical display found. "
            "Set DISPLAY or WAYLAND_DISPLAY."
        )

    import json
    args = [sys.executable, str(_DIALOG_SCRIPT)]
    if username:
        args.append(username)
    if realm:
        args.append(realm)
    if available_principals:
        args.append(json.dumps(available_principals))

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
    )

    if result.returncode == 3:
        detail = result.stderr.strip()
        msg = "GTK4 unavailable. Install python3-gobject."
        raise RuntimeError(f"{msg}\nDetail: {detail}" if detail else msg)
    if result.returncode != 0:
        detail = result.stderr.strip()
        if detail:
            raise RuntimeError(f"Login cancelled or failed: {detail}")
        raise RuntimeError("Login cancelled by user")

    output = result.stdout.strip()
    if "\n" not in output:
        raise RuntimeError("Invalid response from login dialog")

    username_out, password = output.split("\n", 1)
    return username_out, password
