# SPDX-License-Identifier: GPL-3.0-or-later
import os
import subprocess
import sys
from pathlib import Path

_DIALOG_SCRIPT = Path(__file__).parent / "_sudo_dialog.py"
_PASSWORDLESS_SENTINEL = "__PASSWORDLESS__"


def has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def get_sudo_password(username: str, hostname: str) -> str | None:
    """
    Show a GTK4 dialog to obtain the sudo password interactively.

    The dialog runs as a subprocess so GTK owns the main thread of that
    process, avoiding display-initialisation failures when called from
    an asyncio thread-pool worker.

    Returns the entered password string, or None if the user chose
    passwordless sudo.  Raises RuntimeError on cancel or when a
    graphical display / GTK4 is unavailable.
    """
    if not has_display():
        raise RuntimeError(
            "Sudo password required but no graphical display found. "
            "Set DISPLAY or WAYLAND_DISPLAY, or configure passwordless sudo."
        )

    result = subprocess.run(
        [sys.executable, str(_DIALOG_SCRIPT), username, hostname],
        capture_output=True,
        text=True,
    )

    if result.returncode == 3:
        detail = result.stderr.strip()
        msg = (
            "GTK4 unavailable. Install python3-gobject, or configure passwordless sudo."
        )
        raise RuntimeError(f"{msg}\nDetail: {detail}" if detail else msg)
    if result.returncode != 0:
        detail = result.stderr.strip()
        if detail:
            raise RuntimeError(f"Sudo authentication cancelled or failed: {detail}")
        raise RuntimeError("Sudo authentication cancelled by user")

    output = result.stdout.strip()
    if output == _PASSWORDLESS_SENTINEL:
        return None
    return output
