#!/usr/bin/env python3
"""Native GTK4 Layer-Shell Wi-Fi Dropdown Panel for Waybar."""

import os
import signal
import sys

PID_FILE = "/tmp/waybar-wifi-panel.pid"
OTHER_PID_FILES = ("/tmp/waybar-bt-panel.pid", "/tmp/waybar-keybinds-panel.pid")

# Fast-path toggle before importing GTK4/LayerShell (~10ms response)
if "--daemon" not in sys.argv and os.path.exists(PID_FILE):
    try:
        for _op in OTHER_PID_FILES:
            if os.path.exists(_op):
                try:
                    with open(_op) as _f:
                        os.kill(int(_f.read().strip()), signal.SIGUSR1)
                except Exception:
                    pass
        with open(PID_FILE) as _f:
            os.kill(int(_f.read().strip()), signal.SIGUSR2)
        sys.exit(0)
    except Exception:
        pass

import ctypes
ctypes.CDLL("libgtk4-layer-shell.so", mode=ctypes.RTLD_GLOBAL)

import subprocess
import threading
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Gtk4LayerShell

OTHER_PID_FILE = "/tmp/waybar-bt-panel.pid"

COLORS_CSS = os.path.expanduser("~/.config/waybar/colors.css")

CSS = """
@import url("file://__COLORS_CSS__");

window, .panel-root {
    background-color: transparent;
}

.panel-card {
    background-color: alpha(@background, 0.96);
    border: 1.5px solid alpha(@primary, 0.45);
    border-radius: 16px;
    padding: 14px;
    color: @on_surface;
    font-family: "JetBrainsMono Nerd Font Propo", "FiraCode Nerd Font", sans-serif;
}

.header-title {
    font-size: 15px;
    font-weight: 700;
    color: @primary;
}

.sub-label {
    font-size: 11.5px;
    color: @on_surface_variant;
}

.icon-btn {
    background-color: alpha(@surface_variant, 0.5);
    color: @on_surface;
    border-radius: 999px;
    padding: 6px 10px;
    min-width: 28px;
    min-height: 28px;
}

.icon-btn:hover {
    background-color: @primary_container;
    color: @on_primary_container;
}

.connected-card {
    background-color: alpha(@primary_container, 0.45);
    border: 1px solid alpha(@primary, 0.55);
    border-radius: 12px;
    padding: 10px 12px;
}

.connected-ssid {
    font-size: 13.5px;
    font-weight: 700;
    color: @on_surface;
}

.pill-btn {
    background-color: alpha(@surface_variant, 0.7);
    color: @on_surface;
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 600;
}

.pill-btn:hover {
    background-color: @primary;
    color: @on_primary;
}

.danger-btn:hover {
    background-color: @error;
    color: @on_error;
}

.net-row {
    background-color: alpha(@surface_variant, 0.28);
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 8px 12px;
    margin: 2px 0;
}

.net-row:hover {
    background-color: alpha(@surface_variant, 0.65);
    border-color: alpha(@primary, 0.45);
}

.net-name {
    font-size: 13px;
    font-weight: 600;
    color: @on_surface;
}

.pw-box {
    background-color: alpha(@surface_variant, 0.45);
    border: 1px solid alpha(@primary, 0.45);
    border-radius: 10px;
    padding: 10px;
}

.pw-entry {
    background-color: @background;
    color: @on_surface;
    border: 1px solid alpha(@surface_variant, 0.9);
    border-radius: 8px;
    padding: 6px 10px;
}

.pw-entry:focus {
    border-color: @primary;
}

switch {
    background-color: @surface_variant;
    border-radius: 999px;
}

switch:checked {
    background-color: @primary;
}

switch slider {
    background-color: @on_surface;
    border-radius: 999px;
}

.status-banner {
    font-size: 12px;
    color: @error;
    padding: 4px 6px;
}
""".replace("__COLORS_CSS__", COLORS_CSS)


def hide_other():
    if os.path.exists(OTHER_PID_FILE):
        try:
            with open(OTHER_PID_FILE) as f:
                os.kill(int(f.read().strip()), signal.SIGUSR1)
        except Exception:
            pass


def toggle_existing():
    hide_other()
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGUSR2)
            return True
        except Exception:
            pass
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    return False


def cleanup_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE) as f:
                if f.read().strip() == str(os.getpid()):
                    os.remove(PID_FILE)
    except Exception:
        pass


def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def wifi_enabled():
    return run_cmd(["nmcli", "radio", "wifi"]).stdout.strip() == "enabled"


def active_wifi():
    r = run_cmd(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"])
    for line in r.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and "wireless" in parts[1]:
            ip = ""
            ir = run_cmd(["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", parts[2]])
            for il in ir.stdout.splitlines():
                if il.startswith("IP4.ADDRESS"):
                    ip = il.split(":", 1)[1].split("/")[0]
                    break
            return parts[0], parts[2], ip
    return None, None, ""


def saved_ssids():
    r = run_cmd(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
    return {
        line.split(":")[0]
        for line in r.stdout.splitlines()
        if ":" in line and "wireless" in line.split(":")[1]
    }


def list_networks(rescan=False):
    if rescan:
        run_cmd(["nmcli", "device", "wifi", "rescan"])
    r = run_cmd(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list"])
    seen = {}
    for line in r.stdout.splitlines():
        parts, cur, esc = [], [], False
        for ch in line:
            if esc:
                cur.append(ch)
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == ":":
                parts.append("".join(cur))
                cur = []
            else:
                cur.append(ch)
        parts.append("".join(cur))
        if len(parts) < 4:
            continue
        in_use, ssid, sig, sec = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        if not ssid:
            continue
        sig_i = int(sig) if sig.isdigit() else 0
        if ssid not in seen or in_use == "*" or sig_i > seen[ssid]["signal"]:
            seen[ssid] = {
                "ssid": ssid,
                "in_use": in_use == "*",
                "signal": sig_i,
                "security": sec,
            }
    nets = list(seen.values())
    nets.sort(key=lambda x: (not x["in_use"], -x["signal"], x["ssid"].lower()))
    return nets


def sig_icon(sig):
    if sig >= 75:
        return "󰤨"
    if sig >= 50:
        return "󰤥"
    if sig >= 25:
        return "󰤢"
    return "󰤟"


class WifiPanel(Gtk.Application):
    def __init__(self, start_hidden=False):
        super().__init__(application_id="dev.ashborn.waybar.wifi", flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.start_hidden = start_hidden
        self.win = None
        self.provider = None
        self._css_mtime = 0
        self.list_box = None
        self.connected_box = None
        self.pw_revealer = None
        self.hidden_revealer = None
        self.status_lbl = None
        self.spinner = None
        self.switch = None
        self.selected_ssid = None
        self._ignore_switch = False

    def _reload_css(self):
        try:
            mtime = os.path.getmtime(COLORS_CSS)
        except OSError:
            mtime = 0
        if self.provider is None or mtime != self._css_mtime:
            self._css_mtime = mtime
            if self.provider is None:
                self.provider = Gtk.CssProvider()
                Gtk.StyleContext.add_provider_for_display(
                    Gdk.Display.get_default(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
                )
            self.provider.load_from_data(CSS.encode())

    def do_activate(self):
        if self.win is not None:
            self.toggle_panel()
            return
        self.hold()
        self._reload_css()

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.add_css_class("panel-root")

        Gtk4LayerShell.init_for_window(self.win)
        Gtk4LayerShell.set_layer(self.win, Gtk4LayerShell.Layer.TOP)
        Gtk4LayerShell.set_namespace(self.win, "waybar-wifi-dropdown")
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.RIGHT, True)
        Gtk4LayerShell.set_keyboard_mode(self.win, Gtk4LayerShell.KeyboardMode.ON_DEMAND)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self.on_key)
        self.win.add_controller(key_ctrl)

        backdrop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        backdrop.set_hexpand(True)
        backdrop.set_vexpand(True)
        self.win.set_child(backdrop)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("panel-card")
        card.set_size_request(365, -1)
        card.set_halign(Gtk.Align.END)
        card.set_valign(Gtk.Align.START)
        card.set_margin_top(8)
        card.set_margin_end(12)
        backdrop.append(card)

        click_ctrl = Gtk.GestureClick()
        click_ctrl.connect("pressed", self.on_backdrop_click, card)
        self.win.add_controller(click_ctrl)

        # Header
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="   Wi-Fi")
        title.add_css_class("header-title")
        title.set_hexpand(True)
        title.set_xalign(0)
        hdr.append(title)

        self.spinner = Gtk.Spinner()
        hdr.append(self.spinner)

        refresh_btn = Gtk.Button(label="󰑓")
        refresh_btn.add_css_class("icon-btn")
        refresh_btn.set_tooltip_text("Rescan Networks")
        refresh_btn.connect("clicked", lambda _: self.refresh_async(rescan=True))
        hdr.append(refresh_btn)

        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.switch.connect("state-set", self.on_switch)
        hdr.append(self.switch)

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class("icon-btn")
        close_btn.connect("clicked", lambda _: self.hide_panel())
        hdr.append(close_btn)
        card.append(hdr)

        # Status error/info banner
        self.status_lbl = Gtk.Label(label="")
        self.status_lbl.add_css_class("status-banner")
        self.status_lbl.set_xalign(0)
        self.status_lbl.set_visible(False)
        card.append(self.status_lbl)

        # Connected card container
        self.connected_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.append(self.connected_box)

        # Inline Password Revealer
        self.pw_revealer = Gtk.Revealer()
        pw_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pw_box.add_css_class("pw-box")
        self.pw_title = Gtk.Label(label="")
        self.pw_title.add_css_class("net-name")
        self.pw_title.set_xalign(0)
        pw_box.append(self.pw_title)

        self.pw_entry = Gtk.PasswordEntry()
        self.pw_entry.add_css_class("pw-entry")
        self.pw_entry.set_show_peek_icon(True)
        self.pw_entry.connect("activate", self.on_pw_submit)
        pw_box.append(self.pw_entry)

        pw_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pw_btns.set_halign(Gtk.Align.END)
        cancel_pw = Gtk.Button(label="Cancel")
        cancel_pw.add_css_class("pill-btn")
        cancel_pw.connect("clicked", lambda _: self.pw_revealer.set_reveal_child(False))
        conn_pw = Gtk.Button(label="Connect")
        conn_pw.add_css_class("pill-btn")
        conn_pw.connect("clicked", self.on_pw_submit)
        pw_btns.append(cancel_pw)
        pw_btns.append(conn_pw)
        pw_box.append(pw_btns)
        self.pw_revealer.set_child(pw_box)
        card.append(self.pw_revealer)

        # Scrollable networks list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(340)
        scroll.set_propagate_natural_height(True)
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll.set_child(self.list_box)
        card.append(scroll)

        # Hidden network revealer
        self.hidden_revealer = Gtk.Revealer()
        hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hbox.add_css_class("pw-box")
        self.h_ssid = Gtk.Entry(placeholder_text="Hidden Network SSID")
        self.h_ssid.add_css_class("pw-entry")
        self.h_pw = Gtk.PasswordEntry()
        self.h_pw.set_property("placeholder-text", "Password (optional)")
        self.h_pw.add_css_class("pw-entry")
        self.h_pw.set_show_peek_icon(True)
        h_btn = Gtk.Button(label="Connect Hidden Network")
        h_btn.add_css_class("pill-btn")
        h_btn.connect("clicked", self.on_hidden_submit)
        hbox.append(self.h_ssid)
        hbox.append(self.h_pw)
        hbox.append(h_btn)
        self.hidden_revealer.set_child(hbox)
        card.append(self.hidden_revealer)

        # Footer actions
        ftr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hidden_btn = Gtk.Button(label="󰇚 Hidden")
        hidden_btn.add_css_class("pill-btn")
        hidden_btn.set_hexpand(True)
        hidden_btn.connect("clicked", lambda _: self.hidden_revealer.set_reveal_child(not self.hidden_revealer.get_reveal_child()))
        adv_btn = Gtk.Button(label="󰒓 Network Settings")
        adv_btn.add_css_class("pill-btn")
        adv_btn.set_hexpand(True)
        adv_btn.connect("clicked", self.on_open_nmtui)
        ftr.append(hidden_btn)
        ftr.append(adv_btn)
        card.append(ftr)

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self._on_sigusr1)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR2, self._on_sigusr2)

        if not self.start_hidden:
            self.show_panel()

    def _on_sigusr1(self):
        self.hide_panel()
        return GLib.SOURCE_CONTINUE

    def _on_sigusr2(self):
        self.toggle_panel()
        return GLib.SOURCE_CONTINUE

    def show_panel(self):
        hide_other()
        self._reload_css()
        self.win.present()
        self.refresh_async(rescan=False)

    def hide_panel(self):
        if self.win is not None:
            self.win.set_visible(False)

    def toggle_panel(self):
        if self.win is not None and self.win.is_visible():
            self.hide_panel()
        else:
            self.show_panel()

    def on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.hide_panel()
            return True
        return False

    def on_backdrop_click(self, gesture, n_press, x, y, card):
        picked = self.win.pick(x, y, Gtk.PickFlags.DEFAULT)
        if picked is None or (picked is not card and not picked.is_ancestor(card)):
            self.hide_panel()

    def on_open_nmtui(self, _):
        subprocess.Popen(["kitty", "--", "nmtui"], start_new_session=True)
        self.hide_panel()

    def set_status(self, msg=""):
        if msg:
            self.status_lbl.set_text(msg)
            self.status_lbl.set_visible(True)
        else:
            self.status_lbl.set_visible(False)

    def on_switch(self, switch, state):
        if self._ignore_switch:
            return False
        self.spinner.start()
        def worker():
            run_cmd(["nmcli", "radio", "wifi", "on" if state else "off"])
            GLib.idle_add(self.refresh_async, state)
        threading.Thread(target=worker, daemon=True).start()
        return False

    def refresh_async(self, rescan=False):
        self.spinner.start()
        def worker():
            enabled = wifi_enabled()
            conn_name, dev, ip = active_wifi() if enabled else (None, None, "")
            nets = list_networks(rescan=rescan) if enabled else []
            saved = saved_ssids() if enabled else set()
            GLib.idle_add(self.update_ui, enabled, conn_name, ip, nets, saved)
        threading.Thread(target=worker, daemon=True).start()

    def update_ui(self, enabled, conn_name, ip, nets, saved):
        self.spinner.stop()
        self._ignore_switch = True
        self.switch.set_active(enabled)
        self._ignore_switch = False

        while child := self.connected_box.get_first_child():
            self.connected_box.remove(child)
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)

        if not enabled:
            self.connected_box.set_visible(False)
            lbl = Gtk.Label(label="Wi-Fi is turned off")
            lbl.add_css_class("sub-label")
            lbl.set_margin_top(12)
            lbl.set_margin_bottom(12)
            self.list_box.append(lbl)
            return

        if conn_name:
            self.connected_box.set_visible(True)
            cc = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            cc.add_css_class("connected-card")
            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            info.set_hexpand(True)
            s_lbl = Gtk.Label(label=f"✓  {conn_name}")
            s_lbl.add_css_class("connected-ssid")
            s_lbl.set_xalign(0)
            ip_lbl = Gtk.Label(label=f"Connected • {ip}" if ip else "Connected")
            ip_lbl.add_css_class("sub-label")
            ip_lbl.set_xalign(0)
            info.append(s_lbl)
            info.append(ip_lbl)
            cc.append(info)

            disc_btn = Gtk.Button(label="Disconnect")
            disc_btn.add_css_class("pill-btn")
            disc_btn.connect("clicked", lambda _, s=conn_name: self.disconnect_net(s))
            forget_btn = Gtk.Button(label="󰆴")
            forget_btn.add_css_class("pill-btn")
            forget_btn.add_css_class("danger-btn")
            forget_btn.set_tooltip_text("Forget Network")
            forget_btn.connect("clicked", lambda _, s=conn_name: self.forget_net(s))
            cc.append(disc_btn)
            cc.append(forget_btn)
            self.connected_box.append(cc)
        else:
            self.connected_box.set_visible(False)

        for n in nets:
            if n["in_use"]:
                continue
            row_btn = Gtk.Button()
            row_btn.add_css_class("net-row")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            ico = Gtk.Label(label=sig_icon(n["signal"]))
            name = Gtk.Label(label=n["ssid"])
            name.add_css_class("net-name")
            name.set_hexpand(True)
            name.set_xalign(0)
            name.set_ellipsize(3)
            lock = " " if n["security"] and n["security"] != "--" else ""
            meta = Gtk.Label(label=f"{lock}{n['signal']}%")
            meta.add_css_class("sub-label")
            row.append(ico)
            row.append(name)
            row.append(meta)
            row_btn.set_child(row)
            row_btn.connect("clicked", lambda _, net=n, is_saved=(n["ssid"] in saved): self.on_net_click(net, is_saved))
            self.list_box.append(row_btn)

    def on_net_click(self, net, is_saved):
        self.set_status("")
        ssid = net["ssid"]
        if is_saved or not (net["security"] and net["security"] != "--"):
            self.pw_revealer.set_reveal_child(False)
            self.connect_net(ssid, None, is_saved)
        else:
            self.selected_ssid = ssid
            self.pw_title.set_text(f"Password for {ssid}")
            self.pw_entry.set_text("")
            self.pw_revealer.set_reveal_child(True)
            self.pw_entry.grab_focus()

    def on_pw_submit(self, _):
        pw = self.pw_entry.get_text()
        if self.selected_ssid and pw:
            self.pw_revealer.set_reveal_child(False)
            self.connect_net(self.selected_ssid, pw, False)

    def on_hidden_submit(self, _):
        ssid = self.h_ssid.get_text().strip()
        pw = self.h_pw.get_text()
        if not ssid:
            return
        self.hidden_revealer.set_reveal_child(False)
        self.spinner.start()
        def worker():
            args = ["nmcli", "device", "wifi", "connect", ssid, "hidden", "yes"]
            if pw:
                args += ["password", pw]
            r = run_cmd(args)
            GLib.idle_add(self.after_action, r, f"Connected to {ssid}")
        threading.Thread(target=worker, daemon=True).start()

    def connect_net(self, ssid, pw, is_saved):
        self.spinner.start()
        def worker():
            if is_saved:
                r = run_cmd(["nmcli", "connection", "up", ssid])
            elif pw:
                r = run_cmd(["nmcli", "device", "wifi", "connect", ssid, "password", pw])
            else:
                r = run_cmd(["nmcli", "device", "wifi", "connect", ssid])
            GLib.idle_add(self.after_action, r, f"Connected to {ssid}")
        threading.Thread(target=worker, daemon=True).start()

    def disconnect_net(self, ssid):
        self.spinner.start()
        def worker():
            run_cmd(["nmcli", "connection", "down", ssid])
            GLib.idle_add(self.refresh_async, False)
        threading.Thread(target=worker, daemon=True).start()

    def forget_net(self, ssid):
        self.spinner.start()
        def worker():
            run_cmd(["nmcli", "connection", "delete", ssid])
            GLib.idle_add(self.refresh_async, False)
        threading.Thread(target=worker, daemon=True).start()

    def after_action(self, res, ok_msg):
        if res.returncode == 0:
            run_cmd(["notify-send", "-a", "Wi-Fi", "Wi-Fi", ok_msg])
            self.refresh_async(rescan=False)
        else:
            self.spinner.stop()
            self.set_status(res.stderr.strip() or "Connection failed")


if __name__ == "__main__":
    start_hidden = "--daemon" in sys.argv
    if toggle_existing():
        raise SystemExit(0)
    try:
        app = WifiPanel(start_hidden=start_hidden)
        app.run(None)
    finally:
        cleanup_pid()
