#!/usr/bin/env python3
"""Native GTK4 Layer-Shell Bluetooth Dropdown Panel for Waybar."""

import os
import signal
import sys

PID_FILE = "/tmp/waybar-bt-panel.pid"
OTHER_PID_FILES = ("/tmp/waybar-wifi-panel.pid", "/tmp/waybar-keybinds-panel.pid")

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

from concurrent.futures import ThreadPoolExecutor
import subprocess
import threading
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Gtk4LayerShell

OTHER_PID_FILE = "/tmp/waybar-wifi-panel.pid"

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

.dev-row {
    background-color: alpha(@surface_variant, 0.3);
    border: 1px solid transparent;
    border-radius: 12px;
    padding: 9px 12px;
    margin: 2px 0;
}

.dev-row-connected {
    background-color: alpha(@primary_container, 0.45);
    border: 1px solid alpha(@primary, 0.55);
}

.dev-name {
    font-size: 13px;
    font-weight: 600;
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


def bt_powered():
    return "Powered: yes" in run_cmd(["bluetoothctl", "show"]).stdout


def list_devices():
    paired_out = run_cmd(["bluetoothctl", "devices", "Paired"]).stdout
    paired_macs = {
        line.split()[1]
        for line in paired_out.splitlines()
        if line.startswith("Device ") and len(line.split()) >= 2
    }
    all_out = run_cmd(["bluetoothctl", "devices"]).stdout
    raw_devs = []
    for line in all_out.splitlines():
        if not line.startswith("Device "):
            continue
        parts = line.split(" ", 2)
        if len(parts) < 3:
            continue
        raw_devs.append((parts[1], parts[2].strip()))

    def fetch_dev(item):
        mac, name = item
        info = run_cmd(["bluetoothctl", "info", mac]).stdout
        connected = "Connected: yes" in info
        ico = "󰂯"
        if "audio-headset" in info or "audio-headphones" in info:
            ico = "󰋋"
        elif "input-mouse" in info:
            ico = "󰍽"
        elif "input-keyboard" in info:
            ico = "󰌌"
        elif "phone" in info:
            ico = "󰄜"
        bat = ""
        for il in info.splitlines():
            if "Battery Percentage:" in il and "(" in il and ")" in il:
                bat = il.split("(")[-1].split(")")[0] + "%"
                break
        return {
            "mac": mac,
            "name": name,
            "connected": connected,
            "paired": mac in paired_macs,
            "icon": ico,
            "battery": bat,
        }

    with ThreadPoolExecutor(max_workers=6) as pool:
        devices = list(pool.map(fetch_dev, raw_devs))
    devices.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
    return devices


class BluetoothPanel(Gtk.Application):
    def __init__(self, start_hidden=False):
        super().__init__(application_id="dev.ashborn.waybar.bluetooth", flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.start_hidden = start_hidden
        self.win = None
        self.provider = None
        self._css_mtime = 0
        self.list_box = None
        self.spinner = None
        self.switch = None
        self.status_lbl = None
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
        Gtk4LayerShell.set_namespace(self.win, "waybar-bt-dropdown")
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
        title = Gtk.Label(label="   Bluetooth")
        title.add_css_class("header-title")
        title.set_hexpand(True)
        title.set_xalign(0)
        hdr.append(title)

        self.spinner = Gtk.Spinner()
        hdr.append(self.spinner)

        scan_btn = Gtk.Button(label="󰂰")
        scan_btn.add_css_class("icon-btn")
        scan_btn.set_tooltip_text("Scan for Devices (5s)")
        scan_btn.connect("clicked", lambda _: self.scan_async())
        hdr.append(scan_btn)

        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.switch.connect("state-set", self.on_switch)
        hdr.append(self.switch)

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class("icon-btn")
        close_btn.connect("clicked", lambda _: self.hide_panel())
        hdr.append(close_btn)
        card.append(hdr)

        self.status_lbl = Gtk.Label(label="")
        self.status_lbl.add_css_class("status-banner")
        self.status_lbl.set_xalign(0)
        self.status_lbl.set_visible(False)
        card.append(self.status_lbl)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(360)
        scroll.set_propagate_natural_height(True)
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        scroll.set_child(self.list_box)
        card.append(scroll)

        ftr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mgr_btn = Gtk.Button(label="󰒓  Open Blueman Manager")
        mgr_btn.add_css_class("pill-btn")
        mgr_btn.set_hexpand(True)
        mgr_btn.connect("clicked", self.on_open_blueman)
        ftr.append(mgr_btn)
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
        self.refresh_async()

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

    def on_open_blueman(self, _):
        subprocess.Popen(["blueman-manager"], start_new_session=True)
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
            run_cmd(["bluetoothctl", "power", "on" if state else "off"])
            GLib.idle_add(self.refresh_async)
        threading.Thread(target=worker, daemon=True).start()
        return False

    def scan_async(self):
        self.set_status("")
        self.spinner.start()
        def worker():
            run_cmd(["bluetoothctl", "--timeout", "5", "scan", "on"])
            GLib.idle_add(self.refresh_async)
        threading.Thread(target=worker, daemon=True).start()

    def refresh_async(self):
        self.spinner.start()
        def worker():
            powered = bt_powered()
            devs = list_devices() if powered else []
            GLib.idle_add(self.update_ui, powered, devs)
        threading.Thread(target=worker, daemon=True).start()

    def update_ui(self, powered, devs):
        self.spinner.stop()
        self._ignore_switch = True
        self.switch.set_active(powered)
        self._ignore_switch = False

        while child := self.list_box.get_first_child():
            self.list_box.remove(child)

        if not powered:
            lbl = Gtk.Label(label="Bluetooth is turned off")
            lbl.add_css_class("sub-label")
            lbl.set_margin_top(12)
            lbl.set_margin_bottom(12)
            self.list_box.append(lbl)
            return

        if not devs:
            lbl = Gtk.Label(label="No devices found. Click Scan (󰂰).")
            lbl.add_css_class("sub-label")
            lbl.set_margin_top(12)
            lbl.set_margin_bottom(12)
            self.list_box.append(lbl)
            return

        for d in devs:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.add_css_class("dev-row")
            if d["connected"]:
                row.add_css_class("dev-row-connected")

            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            info.set_hexpand(True)
            name = Gtk.Label(label=f"{d['icon']}  {d['name']}")
            name.add_css_class("dev-name")
            name.set_xalign(0)
            name.set_ellipsize(3)
            sub_txt = "Connected" if d["connected"] else ("Paired" if d["paired"] else "Available")
            if d["battery"]:
                sub_txt += f" • {d['battery']}"
            sub = Gtk.Label(label=sub_txt)
            sub.add_css_class("sub-label")
            sub.set_xalign(0)
            info.append(name)
            info.append(sub)
            row.append(info)

            act_btn = Gtk.Button(label="Disconnect" if d["connected"] else "Connect")
            act_btn.add_css_class("pill-btn")
            act_btn.connect("clicked", lambda _, dev=d: self.toggle_device(dev))
            row.append(act_btn)

            if d["paired"]:
                rem_btn = Gtk.Button(label="󰆴")
                rem_btn.add_css_class("pill-btn")
                rem_btn.add_css_class("danger-btn")
                rem_btn.set_tooltip_text("Forget Device")
                rem_btn.connect("clicked", lambda _, dev=d: self.remove_device(dev))
                row.append(rem_btn)

            self.list_box.append(row)

    def toggle_device(self, dev):
        self.set_status("")
        self.spinner.start()
        def worker():
            mac = dev["mac"]
            if dev["connected"]:
                r = run_cmd(["bluetoothctl", "disconnect", mac])
            else:
                if not dev["paired"]:
                    run_cmd(["bluetoothctl", "pair", mac])
                    run_cmd(["bluetoothctl", "trust", mac])
                r = run_cmd(["bluetoothctl", "connect", mac])
            GLib.idle_add(self.after_dev, r, dev["name"], not dev["connected"])
        threading.Thread(target=worker, daemon=True).start()

    def remove_device(self, dev):
        self.set_status("")
        self.spinner.start()
        def worker():
            run_cmd(["bluetoothctl", "remove", dev["mac"]])
            GLib.idle_add(self.refresh_async)
        threading.Thread(target=worker, daemon=True).start()

    def after_dev(self, res, name, connecting):
        if res.returncode == 0:
            msg = f"Connected to {name}" if connecting else f"Disconnected {name}"
            run_cmd(["notify-send", "-a", "Bluetooth", "Bluetooth", msg])
            self.refresh_async()
        else:
            self.spinner.stop()
            self.set_status(f"Failed to connect to {name}")


if __name__ == "__main__":
    start_hidden = "--daemon" in sys.argv
    if toggle_existing():
        raise SystemExit(0)
    try:
        app = BluetoothPanel(start_hidden=start_hidden)
        app.run(None)
    finally:
        cleanup_pid()
