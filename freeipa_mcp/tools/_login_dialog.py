# SPDX-License-Identifier: GPL-3.0-or-later
"""
Standalone GTK4 FreeIPA login dialog.

Spawned as a subprocess by login_gui.get_login_credentials() so that the GTK
main loop runs as the main thread of this process. Uses Gtk.init() +
GLib.MainLoop instead of Gtk.Application to avoid D-Bus registration,
which silently fails (on_activate never fires) in server/daemon contexts
where no session bus is accessible.

Exit codes:
  0  — username and password printed to stdout (username\npassword)
  1  — user cancelled / window closed without choosing
  2  — invalid arguments
  3  — GTK4 / python3-gobject not available or display cannot be opened
"""

import json
import sys


def main() -> None:
    if len(sys.argv) < 1 or len(sys.argv) > 4:
        print(
            "Usage: _login_dialog.py [username] [realm] [principals_json]",
            file=sys.stderr,
        )
        sys.exit(2)

    username = sys.argv[1] if len(sys.argv) >= 2 else ""
    # realm argument is for future use
    # realm = sys.argv[2] if len(sys.argv) >= 3 else ""
    principals_json = sys.argv[3] if len(sys.argv) >= 4 else "[]"

    try:
        available_principals = json.loads(principals_json)
    except json.JSONDecodeError:
        available_principals = []

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
    outcome: dict = {"state": "unset", "username": None, "password": None}

    window = Gtk.Window(title="FreeIPA Login Required", default_width=450)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    vbox.set_margin_top(20)
    vbox.set_margin_bottom(20)
    vbox.set_margin_start(20)
    vbox.set_margin_end(20)

    # Context label
    context_text = "FreeIPA authentication required"
    context = Gtk.Label(label=context_text)
    context.set_halign(Gtk.Align.START)
    vbox.append(context)

    # Principal selection - use dropdown if we have cached principals
    principal_label = Gtk.Label(label="Principal:")
    principal_label.set_halign(Gtk.Align.START)
    principal_label.set_margin_top(12)
    vbox.append(principal_label)

    username_entry = None
    principal_dropdown = None

    if available_principals:
        # Create dropdown with cached principals + "Other..." option
        principal_list = Gtk.StringList()
        for p in available_principals:
            principal = p["principal"]
            suffix = " (renewable)" if p.get("renewable") else ""
            principal_list.append(f"{principal}{suffix}")
        principal_list.append("Other...")

        principal_dropdown = Gtk.DropDown(model=principal_list)

        # Pre-select matching principal if username provided
        if username:
            for i, p in enumerate(available_principals):
                if username in p["principal"] or p["principal"].startswith(username):
                    principal_dropdown.set_selected(i)
                    break

        vbox.append(principal_dropdown)

        # Manual entry field (hidden initially)
        username_entry = Gtk.Entry(placeholder_text="Enter principal")
        username_entry.set_visible(False)
        if username:
            username_entry.set_text(username)
        vbox.append(username_entry)

        def on_dropdown_changed(_dropdown, _param):
            # Show manual entry if "Other..." is selected
            selected = principal_dropdown.get_selected()
            is_other = selected == len(available_principals)
            username_entry.set_visible(is_other)
            if is_other:
                username_entry.grab_focus()

        principal_dropdown.connect("notify::selected", on_dropdown_changed)
    else:
        # No cached principals - use text entry
        username_entry = Gtk.Entry(placeholder_text="Enter principal or username")
        if username:
            username_entry.set_text(username)
        vbox.append(username_entry)

    # Password field
    pwd_label = Gtk.Label(label="Password:")
    pwd_label.set_halign(Gtk.Align.START)
    pwd_label.set_margin_top(12)
    vbox.append(pwd_label)

    password_entry = Gtk.PasswordEntry(
        placeholder_text="Enter password", show_peek_icon=True
    )
    vbox.append(password_entry)

    # Info label for renewable tickets
    info_label = Gtk.Label()
    info_label.set_halign(Gtk.Align.START)
    info_label.set_margin_top(6)
    info_label.add_css_class("dim-label")
    info_label.set_wrap(True)
    info_label.set_visible(False)
    vbox.append(info_label)

    def update_info_label():
        if not principal_dropdown:
            return
        selected = principal_dropdown.get_selected()
        if selected < len(available_principals):
            p = available_principals[selected]
            if p.get("renewable"):
                info_label.set_text(
                    "This ticket is renewable. "
                    "Password will only be used if renewal fails."
                )
                info_label.set_visible(True)
            else:
                info_label.set_visible(False)
        else:
            info_label.set_visible(False)

    if principal_dropdown:
        principal_dropdown.connect("notify::selected", lambda *_: update_info_label())
        update_info_label()

    # Button box
    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    btn_box.set_halign(Gtk.Align.END)
    btn_box.set_margin_top(12)

    def quit_with(state: str, user: str | None = None, pwd: str | None = None) -> None:
        outcome["state"] = state
        outcome["username"] = user
        outcome["password"] = pwd
        loop.quit()

    # Cancel button
    cancel_btn = Gtk.Button(label="Cancel")
    cancel_btn.connect("clicked", lambda _: quit_with("cancelled"))
    btn_box.append(cancel_btn)

    # Login button
    login_btn = Gtk.Button(label="Login")
    login_btn.add_css_class("suggested-action")

    def on_login(_: Gtk.Button | None) -> None:
        # Get username from dropdown or entry
        if principal_dropdown:
            selected = principal_dropdown.get_selected()
            if selected < len(available_principals):
                # Extract principal name (remove " (renewable)" suffix)
                user = available_principals[selected]["principal"]
            elif username_entry and username_entry.get_visible():
                user = username_entry.get_text()
            else:
                return
        elif username_entry:
            user = username_entry.get_text()
        else:
            return

        pwd = password_entry.get_text()
        if user and pwd:
            quit_with("login", user, pwd)

    login_btn.connect("clicked", on_login)
    btn_box.append(login_btn)

    vbox.append(btn_box)
    window.set_child(vbox)
    window.set_default_widget(login_btn)

    # Focus password entry by default (since we likely have a selected principal)
    password_entry.grab_focus()

    # Enter key activates login
    if username_entry:
        username_entry.connect("activate", lambda _: password_entry.grab_focus())
    password_entry.connect("activate", lambda _: on_login(None))

    def on_close_request(_: Gtk.Window) -> bool:
        if outcome["state"] == "unset":
            quit_with("cancelled")
        return False

    window.connect("close-request", on_close_request)
    window.present()
    loop.run()

    state = outcome.get("state", "unset")
    if state == "login":
        print(outcome["username"])
        print(outcome["password"])
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
