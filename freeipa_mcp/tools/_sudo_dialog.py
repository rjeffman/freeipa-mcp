# SPDX-License-Identifier: GPL-3.0-or-later
"""
Standalone GTK4 sudo password dialog.

Spawned as a subprocess by sudo_gui.get_sudo_password() so that the GTK
main loop runs as the main thread of this process.  Uses Gtk.init() +
GLib.MainLoop instead of Gtk.Application to avoid D-Bus registration,
which silently fails (on_activate never fires) in server/daemon contexts
where no session bus is accessible.

Exit codes:
  0  — password printed to stdout, or "__PASSWORDLESS__" for no-password choice
  1  — user cancelled / window closed without choosing
  2  — wrong number of arguments
  3  — GTK4 / python3-gobject not available or display cannot be opened
"""

import sys

_PASSWORDLESS_SENTINEL = "__PASSWORDLESS__"


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: _sudo_dialog.py <username> <hostname>", file=sys.stderr)
        sys.exit(2)

    username, hostname = sys.argv[1], sys.argv[2]

    try:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("GLib", "2.0")
        from gi.repository import GLib, Gtk
    except (ImportError, ValueError) as exc:
        print(f"GTK4 unavailable: {exc}", file=sys.stderr)
        sys.exit(3)

    GLib.set_prgname("freeipa-mcp")

    # PyGObject auto-inits GTK on import; probe the default display explicitly
    # so we get a clear error rather than a silent hang.
    try:
        display = Gtk.init_check()
        if not display:
            raise RuntimeError("Gtk.init_check() returned False")
    except Exception as exc:
        print(f"Cannot open display: {exc}", file=sys.stderr)
        sys.exit(3)

    loop = GLib.MainLoop()
    outcome: dict = {"state": "unset", "value": None}

    window = Gtk.Window(title="Sudo Authentication Required", default_width=400)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    vbox.set_margin_top(20)
    vbox.set_margin_bottom(20)
    vbox.set_margin_start(20)
    vbox.set_margin_end(20)

    context = Gtk.Label(label=f"Sudo access required for:\n{username}@{hostname}")
    context.set_halign(Gtk.Align.START)
    vbox.append(context)

    pwd_label = Gtk.Label(label="Password:")
    pwd_label.set_halign(Gtk.Align.START)
    pwd_label.set_margin_top(12)
    vbox.append(pwd_label)

    entry = Gtk.PasswordEntry(
        placeholder_text="Enter sudo password", show_peek_icon=True
    )
    vbox.append(entry)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    btn_box.set_halign(Gtk.Align.END)
    btn_box.set_margin_top(12)

    def quit_with(state: str, value: str | None = None) -> None:
        outcome["state"] = state
        outcome["value"] = value
        loop.quit()

    cancel_btn = Gtk.Button(label="Cancel")
    cancel_btn.connect("clicked", lambda _: quit_with("cancelled"))
    btn_box.append(cancel_btn)

    nopwd_btn = Gtk.Button(label="Passwordless")
    nopwd_btn.connect("clicked", lambda _: quit_with("passwordless"))
    btn_box.append(nopwd_btn)

    auth_btn = Gtk.Button(label="Authenticate")
    auth_btn.add_css_class("suggested-action")

    def on_authenticate(_: Gtk.Button) -> None:
        pwd = entry.get_text()
        if pwd:
            quit_with("password", pwd)

    auth_btn.connect("clicked", on_authenticate)
    btn_box.append(auth_btn)

    vbox.append(btn_box)
    window.set_child(vbox)
    window.set_default_widget(auth_btn)
    entry.grab_focus()
    entry.connect("activate", lambda _: on_authenticate(None))

    def on_close_request(_: Gtk.Window) -> bool:
        if outcome["state"] == "unset":
            quit_with("cancelled")
        return False

    window.connect("close-request", on_close_request)
    window.present()
    loop.run()

    state = outcome.get("state", "unset")
    if state == "password":
        print(outcome["value"])
        sys.exit(0)
    if state == "passwordless":
        print(_PASSWORDLESS_SENTINEL)
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
