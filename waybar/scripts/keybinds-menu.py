#!/usr/bin/env python3
"""Native GTK4 Layer-Shell Keyboard Shortcuts Viewer & Editor for Waybar."""

import os
import signal
import sys

PID_FILE = "/tmp/waybar-keybinds-panel.pid"
OTHER_PID_FILES = ("/tmp/waybar-wifi-panel.pid", "/tmp/waybar-bt-panel.pid")

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

import re
import subprocess
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell
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
    padding: 4px 10px;
    font-size: 11.5px;
    font-weight: 600;
}

.pill-btn:hover {
    background-color: @primary;
    color: @on_primary;
}

.primary-btn {
    background-color: @primary;
    color: @on_primary;
    border-radius: 8px;
    padding: 5px 11px;
    font-size: 12px;
    font-weight: 700;
}

.primary-btn:hover {
    opacity: 0.9;
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
    font-size: 12px;
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
        if "menu" in inner or "rofi" in inner:
            return "App Launcher"
        if "wlogout" in inner:
            return "Power Menu"
        if "swaync-client" in inner:
            return "Toggle Notifications"
        if "waybar" in inner and ";" in inner:
            return "Reload Waybar"
        if "waybar" in inner:
            return "Toggle Waybar"
        if "hyprshot --freeze -m region" in inner:
            return "Screenshot (Region)"
        if "hyprshot" in inner:
            return "Screenshot (Full Screen)"
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
        return inner[:38]
    return raw[:38]


def extract_hl_bind_calls(text: str) -> list[str]:
    calls = []
    idx = 0
    while True:
        pos = text.find("hl.bind(", idx)
        if pos == -1:
            break
        start = pos + len("hl.bind(")
        depth = 1
        in_str = None
        i = start
        while i < len(text) and depth > 0:
            ch = text[i]
            if in_str:
                if ch == "\\" and i + 1 < len(text):
                    i += 2
                    continue
                if ch == in_str:
                    in_str = None
            else:
                if ch in ('"', "'"):
                    in_str = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
            i += 1
        calls.append(text[start : i - 1])
        idx = i
    return calls


def split_top_level_args(arg_str: str) -> list[str]:
    args = []
    depth = 0
    in_str = None
    start = 0
    i = 0
    while i < len(arg_str):
        ch = arg_str[i]
        if in_str:
            if ch == "\\" and i + 1 < len(arg_str):
                i += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ('"', "'"):
                in_str = ch
            elif ch in ("(", "{", "["):
                depth += 1
            elif ch in (")", "}", "]"):
                depth -= 1
            elif ch == "," and depth == 0:
                args.append(arg_str[start:i].strip())
                start = i + 1
        i += 1
    tail = arg_str[start:].strip()
    if tail:
        args.append(tail)
    return args


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

    for call_body in extract_hl_bind_calls(text):
        args = split_top_level_args(call_body)
        if len(args) < 2:
            continue
        key_expr, action_expr = args[0], re.sub(r'\s+', ' ', args[1])

        if "key" in key_expr and "mainMod" in key_expr:
            continue

        key_str = key_expr.replace('mainMod .. "', main_mod).replace('"', "").strip()
        key_str = re.sub(r'\s*\.\.\s*', '', key_str)
        key_str = re.sub(r'\s+', ' ', key_str)

        if key_str in seen:
            continue
        seen.add(key_str)
        entries.append({"orig_key": key_str, "desc": describe_action(action_expr)})

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


def lua_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def load_custom_data() -> tuple[dict[str, str], list[dict]]:
    if not os.path.isfile(CUSTOM_LUA):
        return {}, []
    with open(CUSTOM_LUA, "r", encoding="utf-8") as f:
        text = f.read()

    overrides: dict[str, str] = {}
    custom_binds: list[dict] = []

    ov_match = re.search(r'overrides\s*=\s*\{(.*?)\}', text, re.DOTALL)
    if ov_match:
        for m in re.finditer(r'\[\s*"([^"]+)"\s*\]\s*=\s*"([^"]+)"', ov_match.group(1)):
            overrides[m.group(1)] = m.group(2)
    else:
        for m in re.finditer(r'\[\s*"([^"]+)"\s*\]\s*=\s*"([^"]+)"', text):
            overrides[m.group(1)] = m.group(2)

    cb_match = re.search(r'custom_binds\s*=\s*\{(.*?)\n\s*\}', text, re.DOTALL)
    if cb_match:
        for item_m in re.finditer(r'\{([^\}]+)\}', cb_match.group(1)):
            block = item_m.group(1)
            n_m = re.search(r'name\s*=\s*"((?:\\.|[^"])*)"', block)
            k_m = re.search(r'key\s*=\s*"((?:\\.|[^"])*)"', block)
            c_m = re.search(r'command\s*=\s*"((?:\\.|[^"])*)"', block)
            if n_m and k_m and c_m:
                custom_binds.append({
                    "name": n_m.group(1).replace('\\"', '"').replace("\\\\", "\\"),
                    "key": k_m.group(1).replace('\\"', '"').replace("\\\\", "\\"),
                    "command": c_m.group(1).replace('\\"', '"').replace("\\\\", "\\"),
                })

    return overrides, custom_binds


def save_custom_data(overrides: dict[str, str], custom_binds: list[dict]) -> None:
    os.makedirs(os.path.dirname(CUSTOM_LUA), exist_ok=True)
    lines = [
        "-- Custom keyboard shortcuts & overrides (auto-managed by Waybar Keybinds menu)",
        "return {",
        "    overrides = {",
    ]
    for orig_key, new_key in sorted(overrides.items()):
        lines.append(f'        ["{lua_escape(orig_key)}"] = "{lua_escape(new_key)}",')
    lines.append("    },")
    lines.append("    custom_binds = {")
    for item in custom_binds:
        lines.append(
            f'        {{ name = "{lua_escape(item["name"])}", key = "{lua_escape(item["key"])}", command = "{lua_escape(item["command"])}" }},'
        )
    lines.append("    },")
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


def hide_other():
    for op in OTHER_PID_FILES:
        if os.path.exists(op):
            try:
                with open(op) as f:
                    os.kill(int(f.read().strip()), signal.SIGUSR1)
            except Exception:
                pass


def toggle_existing() -> bool:
    hide_other()
    if os.path.isfile(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGUSR2)
            return True
        except Exception:
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
    return False


class KeybindsPanel(Gtk.Application):
    def __init__(self, start_hidden: bool = False):
        super().__init__(application_id="dev.ashborn.waybar.keybinds")
        self.start_hidden = start_hidden
        self.win = None
        self.card = None
        self.provider = None
        self.binds = []
        self.overrides = {}
        self.custom_binds = []
        self.edit_mode = None  # "override" | "add" | "edit_custom"
        self.editing_orig_key = None
        self.editing_custom_idx = None
        self.capturing = False

    def _reload_css(self):
        if self.provider is None:
            self.provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        css_text = CSS.replace("__COLORS_CSS__", COLORS_CSS if os.path.isfile(COLORS_CSS) else "/dev/null")
        self.provider.load_from_data(css_text.encode("utf-8"))

    def do_activate(self):
        if self.win is not None:
            self.toggle_panel()
            return

        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))

        self._reload_css()

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_decorated(False)
        self.win.add_css_class("panel-root")

        Gtk4LayerShell.init_for_window(self.win)
        Gtk4LayerShell.set_layer(self.win, Gtk4LayerShell.Layer.TOP)
        Gtk4LayerShell.set_namespace(self.win, "waybar-keybinds-dropdown")
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.RIGHT, True)
        Gtk4LayerShell.set_keyboard_mode(self.win, Gtk4LayerShell.KeyboardMode.ON_DEMAND)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self.on_key_pressed)
        self.win.add_controller(key_ctrl)

        backdrop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        backdrop.set_hexpand(True)
        backdrop.set_vexpand(True)
        self.win.set_child(backdrop)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.card = card
        card.add_css_class("panel-card")
        card.set_size_request(470, 560)
        card.set_halign(Gtk.Align.END)
        card.set_valign(Gtk.Align.START)
        card.set_margin_top(8)
        card.set_margin_end(14)
        backdrop.append(card)

        click_ctrl = Gtk.GestureClick()
        click_ctrl.connect("pressed", self.on_backdrop_click)
        self.win.add_controller(click_ctrl)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title_box.set_hexpand(True)
        title = Gtk.Label(label="󰌌  Keyboard Shortcuts")
        title.set_xalign(0)
        title.add_css_class("header-title")
        self.sub_lbl = Gtk.Label(label="")
        self.sub_lbl.set_xalign(0)
        self.sub_lbl.add_css_class("sub-label")
        title_box.append(title)
        title_box.append(self.sub_lbl)

        add_btn = Gtk.Button(label="+ Add")
        add_btn.add_css_class("primary-btn")
        add_btn.connect("clicked", lambda _: self.open_add_form())

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class("icon-btn")
        close_btn.connect("clicked", lambda _: self.hide_panel())
        header.append(title_box)
        header.append(add_btn)
        header.append(close_btn)
        card.append(header)

        # Search
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search shortcut or action...")
        self.search_entry.add_css_class("search-entry")
        self.search_entry.connect("changed", lambda _: self.render_list())
        card.append(self.search_entry)

        # Inline editor / add revealer
        self.edit_rev = Gtk.Revealer()
        self.edit_rev.set_reveal_child(False)
        edit_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        edit_box.add_css_class("edit-box")

        self.edit_title = Gtk.Label(label="")
        self.edit_title.set_xalign(0)
        self.edit_title.add_css_class("action-label")
        edit_box.append(self.edit_title)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Shortcut Name (e.g. Open Obsidian)")
        self.name_entry.add_css_class("search-entry")
        edit_box.append(self.name_entry)

        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.set_placeholder_text("Command (e.g. obsidian)")
        self.cmd_entry.add_css_class("search-entry")
        edit_box.append(self.cmd_entry)

        row_edit = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.new_key_entry = Gtk.Entry()
        self.new_key_entry.set_hexpand(True)
        self.new_key_entry.add_css_class("search-entry")
        self.new_key_entry.set_placeholder_text("Shortcut Key (e.g. SUPER + O)")

        self.cap_btn = Gtk.Button(label="Press Keys...")
        self.cap_btn.add_css_class("capture-btn")
        self.cap_btn.connect("clicked", self.on_toggle_capture)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("primary-btn")
        save_btn.connect("clicked", self.on_save_edit)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.add_css_class("pill-btn")
        cancel_btn.connect("clicked", lambda _: self.close_editor())

        row_edit.append(self.new_key_entry)
        row_edit.append(self.cap_btn)
        row_edit.append(save_btn)
        row_edit.append(cancel_btn)
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
        self.reload_data()
        self.win.present()

    def hide_panel(self):
        self.close_editor()
        if self.win is not None:
            self.win.set_visible(False)

    def toggle_panel(self):
        if self.win is not None and self.win.is_visible():
            self.hide_panel()
        else:
            self.show_panel()

    def on_backdrop_click(self, _gesture, _n_press, x, y):
        if not self.card:
            return
        alloc = self.card.get_allocation()
        if not (alloc.x <= x <= alloc.x + alloc.width and alloc.y <= y <= alloc.y + alloc.height):
            self.hide_panel()

    def reload_data(self):
        self.binds = parse_binds()
        self.overrides, self.custom_binds = load_custom_data()
        total = len(self.binds) + len(self.custom_binds)
        custom_count = len(self.overrides) + len(self.custom_binds)
        self.sub_lbl.set_text(
            f"{total} shortcuts · {custom_count} in customShortcut.lua"
        )
        self.render_list()

    def render_list(self):
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)

        q = self.search_entry.get_text().strip().lower()

        # Custom added shortcuts first
        for idx, cb in enumerate(self.custom_binds):
            name, key, cmd = cb["name"], cb["key"], cb["command"]
            if q and q not in name.lower() and q not in key.lower() and q not in cmd.lower():
                continue

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.add_css_class("shortcut-row-custom")

            lbl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            lbl_box.set_hexpand(True)
            desc_lbl = Gtk.Label(label=name)
            desc_lbl.set_xalign(0)
            desc_lbl.add_css_class("action-label")
            lbl_box.append(desc_lbl)

            key_lbl = Gtk.Label(label=key)
            key_lbl.add_css_class("key-badge-custom")

            edit_btn = Gtk.Button(label="Edit")
            edit_btn.add_css_class("pill-btn")
            edit_btn.connect("clicked", lambda _, i=idx: self.open_edit_custom(i))

            del_btn = Gtk.Button(label="✕")
            del_btn.set_tooltip_text("Delete custom shortcut")
            del_btn.add_css_class("pill-btn")
            del_btn.add_css_class("danger-btn")
            del_btn.connect("clicked", lambda _, i=idx: self.on_delete_custom(i))

            row.append(lbl_box)
            row.append(key_lbl)
            row.append(edit_btn)
            row.append(del_btn)
            self.list_box.append(row)

        # Built-in binds from binds.lua
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
            edit_btn.connect("clicked", lambda _, ok=orig_key, ak=active_key, d=desc: self.open_override_editor(ok, ak, d))

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

    def open_override_editor(self, orig_key: str, active_key: str, desc: str):
        self.edit_mode = "override"
        self.editing_orig_key = orig_key
        self.editing_custom_idx = None
        self.capturing = False
        self.cap_btn.set_label("Press Keys...")
        self.edit_title.set_text(f"Edit Shortcut: {desc}")
        self.name_entry.set_visible(False)
        self.cmd_entry.set_visible(False)
        self.new_key_entry.set_text(active_key)
        self.edit_rev.set_reveal_child(True)
        self.new_key_entry.grab_focus()

    def open_add_form(self):
        self.edit_mode = "add"
        self.editing_orig_key = None
        self.editing_custom_idx = None
        self.capturing = False
        self.cap_btn.set_label("Press Keys...")
        self.edit_title.set_text("Add New Shortcut (customShortcut.lua)")
        self.name_entry.set_text("")
        self.cmd_entry.set_text("")
        self.new_key_entry.set_text("")
        self.name_entry.set_visible(True)
        self.cmd_entry.set_visible(True)
        self.edit_rev.set_reveal_child(True)
        self.name_entry.grab_focus()

    def open_edit_custom(self, idx: int):
        cb = self.custom_binds[idx]
        self.edit_mode = "edit_custom"
        self.editing_orig_key = None
        self.editing_custom_idx = idx
        self.capturing = False
        self.cap_btn.set_label("Press Keys...")
        self.edit_title.set_text(f"Edit Custom Shortcut: {cb['name']}")
        self.name_entry.set_text(cb["name"])
        self.cmd_entry.set_text(cb["command"])
        self.new_key_entry.set_text(cb["key"])
        self.name_entry.set_visible(True)
        self.cmd_entry.set_visible(True)
        self.edit_rev.set_reveal_child(True)
        self.name_entry.grab_focus()

    def close_editor(self):
        self.capturing = False
        self.edit_mode = None
        self.editing_orig_key = None
        self.editing_custom_idx = None
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
                self.hide_panel()
            return True
        return False

    def on_save_edit(self, _):
        new_key = self.new_key_entry.get_text().strip()
        if not new_key:
            return

        if self.edit_mode == "override" and self.editing_orig_key:
            if new_key == self.editing_orig_key:
                self.overrides.pop(self.editing_orig_key, None)
            else:
                self.overrides[self.editing_orig_key] = new_key
        elif self.edit_mode == "add":
            name = self.name_entry.get_text().strip()
            cmd = self.cmd_entry.get_text().strip()
            if not name or not cmd:
                return
            self.custom_binds.append({"name": name, "key": new_key, "command": cmd})
        elif self.edit_mode == "edit_custom" and self.editing_custom_idx is not None:
            name = self.name_entry.get_text().strip()
            cmd = self.cmd_entry.get_text().strip()
            if not name or not cmd:
                return
            self.custom_binds[self.editing_custom_idx] = {"name": name, "key": new_key, "command": cmd}

        save_custom_data(self.overrides, self.custom_binds)
        self.close_editor()
        self.reload_data()

    def on_reset_key(self, orig_key: str):
        if orig_key in self.overrides:
            self.overrides.pop(orig_key, None)
            save_custom_data(self.overrides, self.custom_binds)
            self.reload_data()

    def on_delete_custom(self, idx: int):
        if 0 <= idx < len(self.custom_binds):
            self.custom_binds.pop(idx)
            save_custom_data(self.overrides, self.custom_binds)
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
    start_hidden = "--daemon" in sys.argv
    if toggle_existing():
        raise SystemExit(0)
    try:
        app = KeybindsPanel(start_hidden=start_hidden)
        app.run(None)
    finally:
        cleanup_pid()
