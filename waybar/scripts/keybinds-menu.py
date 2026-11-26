#!/usr/bin/env python3
"""Native GTK4 Layer-Shell Keyboard Shortcuts Viewer & Editor for Waybar."""

import ctypes
ctypes.CDLL("libgtk4-layer-shell.so", mode=ctypes.RTLD_GLOBAL)

import os
import re
import signal
import subprocess
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell

PID_FILE = "/tmp/waybar-keybinds-panel.pid"
COLORS_CSS = os.path.expanduser("~/.config/waybar/colors.css")
BINDS_LUA = os.path.expanduser("~/.config/hypr/modules/binds.lua")
CUSTOM_LUA = os.path.expanduser("~/.config/hypr/modules/customShortcut.lua")

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

.search-entry {
    background-color: alpha(@surface_variant, 0.4);
    color: @on_surface;
    border: 1px solid alpha(@primary, 0.3);
    border-radius: 10px;
    padding: 6px 10px;
    font-size: 12.5px;
}

.search-entry:focus {
    border-color: @primary;
}

.shortcut-row {
    background-color: alpha(@surface_variant, 0.28);
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 8px 12px;
}

.shortcut-row:hover {
    background-color: alpha(@surface_variant, 0.48);
    border-color: alpha(@primary, 0.28);
}

.shortcut-row-custom {
    background-color: alpha(@primary_container, 0.28);
    border: 1px solid alpha(@primary, 0.45);
    border-radius: 10px;
    padding: 8px 12px;
}

.action-label {
    font-size: 12.5px;
    font-weight: 600;
    color: @on_surface;
}

.key-badge {
    background-color: alpha(@surface, 0.85);
    color: @primary;
    border: 1px solid alpha(@primary, 0.4);
    border-radius: 7px;
    padding: 3px 8px;
    font-size: 11.5px;
    font-weight: 700;
}

.key-badge-custom {
    background-color: @primary;
    color: @on_primary;
    border: 1px solid @primary;
    border-radius: 7px;
    padding: 3px 8px;
    font-size: 11.5px;
    font-weight: 700;
}

.pill-btn {
    background-color: alpha(@surface_variant, 0.7);
    color: @on_surface;
    border-radius: 8px;
    padding: 4px 9px;
    font-size: 11.5px;
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

.edit-box {
    background-color: alpha(@primary_container, 0.35);
    border: 1px solid alpha(@primary, 0.55);
    border-radius: 12px;
    padding: 10px 12px;
}

.capture-btn {
    background-color: alpha(@surface, 0.9);
    color: @primary;
    border: 1.5px dashed @primary;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12.5px;
    font-weight: 700;
}
"""

FRIENDLY_ACTIONS = {
    "terminal": "Open Terminal",
    "fileManager": "Open File Manager",
    "menu": "App Launcher",
    "browser": "Open Browser",
    "browserAlt": "Open Secondary Browser",
    "editor": "Open Code Editor",
    "editorAlt": "Open Secondary Editor",
    "hl.dsp.window.close()": "Close Active Window",
    'hl.dsp.window.float({ action = "toggle" })': "Toggle Floating Window",
    'hl.dsp.window.fullscreen({ action = "toggle" })': "Toggle Fullscreen",
    "hl.dsp.window.pseudo()": "Toggle Pseudo Tiling",
    'hl.dsp.layout("togglesplit")': "Toggle Split Layout",
    'hl.dsp.focus({ direction = "left" })': "Focus Left Window",
    'hl.dsp.focus({ direction = "right" })': "Focus Right Window",
    'hl.dsp.focus({ direction = "up" })': "Focus Up Window",
    'hl.dsp.focus({ direction = "down" })': "Focus Down Window",
    'hl.dsp.window.swap({ direction = "left" })': "Swap Window Left",
    'hl.dsp.window.swap({ direction = "right" })': "Swap Window Right",
    'hl.dsp.window.swap({ direction = "up" })': "Swap Window Up",
    'hl.dsp.window.swap({ direction = "down" })': "Swap Window Down",
    'hl.dsp.workspace.toggle_special("magic")': "Toggle Scratchpad",
    'hl.dsp.window.move({ workspace = "special:magic" })': "Move to Scratchpad",
    'hl.dsp.focus({ workspace = "e+1" })': "Next Workspace (Scroll)",
    'hl.dsp.focus({ workspace = "e-1" })': "Previous Workspace (Scroll)",
    "hl.dsp.window.drag()": "Drag Window (Mouse)",
    "hl.dsp.window.resize()": "Resize Window (Mouse)",
}


def describe_action(raw: str) -> str:
    raw = raw.strip()
    if raw in FRIENDLY_ACTIONS:
        return FRIENDLY_ACTIONS[raw]
    m = re.match(r'^hl\.dsp\.exec_cmd\((.+)\)$', raw)
    if m:
        inner = m.group(1).strip()
        if inner in FRIENDLY_ACTIONS:
            return FRIENDLY_ACTIONS[inner]
        inner = inner.strip('"\'')
        if "wlogout" in inner:
            return "Power Menu (wlogout)"
        if "swaync-client" in inner:
            return "Toggle Notifications"
        if "waybar" in inner and "pkill" in inner:
            return "Reload / Toggle Waybar"
        if "hyprshot --freeze -m region" in inner:
            return "Screenshot (Region)"
        if "hyprshot" in inner:
            return "Screenshot (Active Output)"
        if "hyprlock" in inner:
            return "Lock Screen"
        if "wallpaper.sh" in inner:
            return "Wallpaper Picker"
        if "clipboard.py" in inner:
            return "Clipboard History"
        if "wpctl set-volume" in inner and "+" in inner:
            return "Volume Up"
        if "wpctl set-volume" in inner and "-" in inner:
            return "Volume Down"
        if "DEFAULT_AUDIO_SINK" in inner and "toggle" in inner:
            return "Mute Audio"
        if "DEFAULT_AUDIO_SOURCE" in inner and "toggle" in inner:
            return "Mute Microphone"
        if "brightnessctl" in inner and "+" in inner:
            return "Brightness Up"
        if "brightnessctl" in inner and "-" in inner:
            return "Brightness Down"
        if "playerctl next" in inner:
            return "Media Next"
        if "playerctl play-pause" in inner:
            return "Media Play / Pause"
        if "playerctl previous" in inner:
            return "Media Previous"
        return inner[:42]
    return raw[:42]


def parse_binds() -> list[dict]:
    if not os.path.isfile(BINDS_LUA):
        return []
    with open(BINDS_LUA, "r", encoding="utf-8") as f:
        text = f.read()

    main_mod = "SUPER"
    m_mod = re.search(r'local\s+mainMod\s*=\s*"([^"]+)"', text)
    if m_mod:
        main_mod = m_mod.group(1)

    entries: list[dict] = []
    seen: set[str] = set()

    # Single-line and multiline hl.bind(...) calls
    pattern = re.compile(r'hl\.bind\(\s*(.*?)\s*,\s*(hl\.dsp\.[^\n]+?)(?:\s*,\s*\{[^}]*\})?\s*\)', re.DOTALL)
    for m in pattern.finditer(text):
        key_expr = m.group(1).strip()
        action_expr = re.sub(r'\s+', ' ', m.group(2).strip())

        if "mainMod .." in key_expr and "key" in key_expr and "for i = 1, 10" in text:
            continue

        key_str = key_expr.replace('mainMod .. "', main_mod).replace('"', "").strip()
        key_str = re.sub(r'\s*\.\.\s*', '', key_str)
        key_str = re.sub(r'\s+', ' ', key_str)

        if key_str in seen:
            continue
        seen.add(key_str)
        entries.append({"orig_key": key_str, "desc": describe_action(action_expr)})

    # Workspace binds from loop
    if "for i = 1, 10 do" in text:
        for i in range(1, 11):
            k = str(i % 10)
            k1 = f"{main_mod} + {k}"
            k2 = f"{main_mod} + SHIFT + {k}"
            if k1 not in seen:
                entries.append({"orig_key": k1, "desc": f"Switch to Workspace {i}"})
            if k2 not in seen:
                entries.append({"orig_key": k2, "desc": f"Move Window to Workspace {i}"})

    return entries


def load_custom_shortcuts() -> dict[str, str]:
    if not os.path.isfile(CUSTOM_LUA):
        return {}
    with open(CUSTOM_LUA, "r", encoding="utf-8") as f:
        text = f.read()
    overrides: dict[str, str] = {}
    for m in re.finditer(r'\[\s*"([^"]+)"\s*\]\s*=\s*"([^"]+)"', text):
        overrides[m.group(1)] = m.group(2)
    return overrides


def save_custom_shortcuts(overrides: dict[str, str]) -> None:
    os.makedirs(os.path.dirname(CUSTOM_LUA), exist_ok=True)
    lines = [
        "-- Custom keyboard shortcut overrides (auto-managed by Waybar Keybinds menu)",
        '-- Format: ["ORIGINAL_KEY_FROM_BINDS_LUA"] = "NEW_KEY"',
        "return {",
    ]
    for orig_key, new_key in sorted(overrides.items()):
        lines.append(f'    ["{orig_key}"] = "{new_key}",')
    lines.append("}")
    lines.append("")
    with open(CUSTOM_LUA, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    subprocess.run(["hyprctl", "reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def gdk_event_to_hypr(keyval: int, state: Gdk.ModifierType) -> str | None:
    key_name = Gdk.keyval_name(keyval)
    if not key_name:
        return None
    if key_name in (
        "Super_L", "Super_R", "Control_L", "Control_R",
        "Alt_L", "Alt_R", "Shift_L", "Shift_R", "Meta_L", "Meta_R",
    ):
        return None

    mods = []
    if state & Gdk.ModifierType.SUPER_MASK:
        mods.append("SUPER")
    if state & Gdk.ModifierType.CONTROL_MASK:
        mods.append("CTRL")
    if state & Gdk.ModifierType.ALT_MASK:
        mods.append("ALT")
    if state & Gdk.ModifierType.SHIFT_MASK:
        mods.append("SHIFT")

    special_map = {
        "Return": "return",
        "KP_Enter": "return",
        "space": "space",
        "Left": "left",
        "Right": "right",
        "Up": "up",
        "Down": "down",
        "Tab": "tab",
        "BackSpace": "backspace",
        "Escape": "escape",
    }
    if key_name in special_map:
        k = special_map[key_name]
    elif len(key_name) == 1:
        k = key_name.upper()
    else:
        k = key_name

    return " + ".join(mods + [k]) if mods else k


def toggle_existing() -> bool:
    if not os.path.isfile(PID_FILE):
        return False
    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        return True
    except Exception:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        return False


class KeybindsPanel(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="dev.ashborn.waybar.keybinds")
        self.win = None
        self.binds = []
        self.overrides = {}
        self.editing_orig_key = None
        self.capturing = False

    def do_activate(self):
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))

        css_text = CSS.replace("__COLORS_CSS__", COLORS_CSS if os.path.isfile(COLORS_CSS) else "/dev/null")
        provider = Gtk.CssProvider()
        provider.load_from_data(css_text.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_decorated(False)
        self.win.add_css_class("panel-root")

        Gtk4LayerShell.init_for_window(self.win)
        Gtk4LayerShell.set_layer(self.win, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.RIGHT, True)
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.TOP, 8)
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.RIGHT, 14)
        Gtk4LayerShell.set_keyboard_mode(self.win, Gtk4LayerShell.KeyboardMode.ON_DEMAND)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self.on_key_pressed)
        self.win.add_controller(key_ctrl)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("panel-card")
        card.set_size_request(470, 540)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title_box.set_hexpand(True)
        title = Gtk.Label(label="󰌌  Keyboard Shortcuts")
        title.set_xalign(0)
        title.add_css_class("header-title")
        self.sub_lbl = Gtk.Label(label="Saves overrides to customShortcut.lua")
        self.sub_lbl.set_xalign(0)
        self.sub_lbl.add_css_class("sub-label")
        title_box.append(title)
        title_box.append(self.sub_lbl)

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class("icon-btn")
        close_btn.connect("clicked", lambda _: self.quit())
        header.append(title_box)
        header.append(close_btn)
        card.append(header)

        # Search
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search shortcut or action...")
        self.search_entry.add_css_class("search-entry")
        self.search_entry.connect("changed", lambda _: self.render_list())
        card.append(self.search_entry)

        # Inline editor revealer
        self.edit_rev = Gtk.Revealer()
        self.edit_rev.set_reveal_child(False)
        edit_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        edit_box.add_css_class("edit-box")

        self.edit_title = Gtk.Label(label="")
        self.edit_title.set_xalign(0)
        self.edit_title.add_css_class("action-label")

        row_edit = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.new_key_entry = Gtk.Entry()
        self.new_key_entry.set_hexpand(True)
        self.new_key_entry.add_css_class("search-entry")
        self.new_key_entry.set_placeholder_text("e.g. SUPER + T")

        self.cap_btn = Gtk.Button(label="Press Keys...")
        self.cap_btn.add_css_class("capture-btn")
        self.cap_btn.connect("clicked", self.on_toggle_capture)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("pill-btn")
        save_btn.connect("clicked", self.on_save_edit)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.add_css_class("pill-btn")
        cancel_btn.connect("clicked", lambda _: self.close_editor())

        row_edit.append(self.new_key_entry)
        row_edit.append(self.cap_btn)
        row_edit.append(save_btn)
        row_edit.append(cancel_btn)

        edit_box.append(self.edit_title)
        edit_box.append(row_edit)
        self.edit_rev.set_child(edit_box)
        card.append(self.edit_rev)

        # Scrollable list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        scroll.set_child(self.list_box)
        card.append(scroll)

        self.win.set_child(card)
        self.reload_data()
        self.win.present()

    def reload_data(self):
        self.binds = parse_binds()
        self.overrides = load_custom_shortcuts()
        count = len(self.overrides)
        self.sub_lbl.set_text(
            f"{len(self.binds)} shortcuts · {count} custom override{'s' if count != 1 else ''} in customShortcut.lua"
        )
        self.render_list()

    def render_list(self):
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)

        q = self.search_entry.get_text().strip().lower()
        for item in self.binds:
            orig_key = item["orig_key"]
            active_key = self.overrides.get(orig_key, orig_key)
            is_custom = orig_key in self.overrides
            desc = item["desc"]

            if q and q not in desc.lower() and q not in active_key.lower() and q not in orig_key.lower():
                continue

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.add_css_class("shortcut-row-custom" if is_custom else "shortcut-row")

            lbl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            lbl_box.set_hexpand(True)
            desc_lbl = Gtk.Label(label=desc)
            desc_lbl.set_xalign(0)
            desc_lbl.add_css_class("action-label")
            lbl_box.append(desc_lbl)
            if is_custom:
                orig_lbl = Gtk.Label(label=f"Default: {orig_key}")
                orig_lbl.set_xalign(0)
                orig_lbl.add_css_class("sub-label")
                lbl_box.append(orig_lbl)

            key_lbl = Gtk.Label(label=active_key)
            key_lbl.add_css_class("key-badge-custom" if is_custom else "key-badge")

            edit_btn = Gtk.Button(label="Edit")
            edit_btn.add_css_class("pill-btn")
            edit_btn.connect("clicked", lambda _, ok=orig_key, ak=active_key, d=desc: self.open_editor(ok, ak, d))

            row.append(lbl_box)
            row.append(key_lbl)
            row.append(edit_btn)

            if is_custom:
                reset_btn = Gtk.Button(label="↺")
                reset_btn.set_tooltip_text("Reset to default")
                reset_btn.add_css_class("pill-btn")
                reset_btn.add_css_class("danger-btn")
                reset_btn.connect("clicked", lambda _, ok=orig_key: self.on_reset_key(ok))
                row.append(reset_btn)

            self.list_box.append(row)

    def open_editor(self, orig_key: str, active_key: str, desc: str):
        self.editing_orig_key = orig_key
        self.capturing = False
        self.cap_btn.set_label("Press Keys...")
        self.edit_title.set_text(f"Edit: {desc} (default: {orig_key})")
        self.new_key_entry.set_text(active_key)
        self.edit_rev.set_reveal_child(True)
        self.new_key_entry.grab_focus()

    def close_editor(self):
        self.capturing = False
        self.editing_orig_key = None
        self.edit_rev.set_reveal_child(False)

    def on_toggle_capture(self, _):
        self.capturing = not self.capturing
        self.cap_btn.set_label("Listening..." if self.capturing else "Press Keys...")

    def on_key_pressed(self, _ctrl, keyval, _keycode, state):
        if self.capturing:
            combo = gdk_event_to_hypr(keyval, state)
            if combo:
                self.new_key_entry.set_text(combo)
                self.capturing = False
                self.cap_btn.set_label("Press Keys...")
            return True
        if keyval == Gdk.KEY_Escape:
            if self.edit_rev.get_reveal_child():
                self.close_editor()
            else:
                self.quit()
            return True
        return False

    def on_save_edit(self, _):
        if not self.editing_orig_key:
            return
        new_key = self.new_key_entry.get_text().strip()
        if not new_key:
            return
        if new_key == self.editing_orig_key:
            self.overrides.pop(self.editing_orig_key, None)
        else:
            self.overrides[self.editing_orig_key] = new_key
        save_custom_shortcuts(self.overrides)
        self.close_editor()
        self.reload_data()

    def on_reset_key(self, orig_key: str):
        if orig_key in self.overrides:
            self.overrides.pop(orig_key, None)
            save_custom_shortcuts(self.overrides)
            self.reload_data()


def cleanup_pid():
    try:
        if os.path.isfile(PID_FILE):
            with open(PID_FILE, "r", encoding="utf-8") as f:
                if int(f.read().strip()) == os.getpid():
                    os.remove(PID_FILE)
    except Exception:
        pass


if __name__ == "__main__":
    if toggle_existing():
        raise SystemExit(0)
    try:
        app = KeybindsPanel()
        app.run(None)
    finally:
        cleanup_pid()
