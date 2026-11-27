#!/usr/bin/env python3
"""Minimal, pixel-clean macOS Spotlight-style GTK4 App Launcher."""

import os
import signal
import sys

PID_FILE = "/tmp/waybar-app-launcher.pid"
OTHER_PID_FILES = (
    "/tmp/waybar-wifi-panel.pid",
    "/tmp/waybar-bt-panel.pid",
    "/tmp/waybar-keybinds-panel.pid",
)

# Instant ~10ms toggle before loading GTK4/LayerShell
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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Gtk4LayerShell

COLORS_CSS = os.path.expanduser("~/.config/waybar/colors.css")

CSS = """
@import url("file://__COLORS_CSS__");

window, .launcher-root {
    background-color: transparent;
}

.spotlight-shell {
    background-color: alpha(@background, 0.92);
    border: 1px solid alpha(@on_surface, 0.14);
    border-radius: 20px;
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.55);
    color: @on_surface;
    font-family: "Inter", "SF Pro Display", "Noto Sans", sans-serif;
}

.spotlight-search-bar {
    padding: 15px 20px;
}

.search-glyph {
    color: @primary;
    font-size: 19px;
    font-family: "JetBrainsMono Nerd Font Propo", "FiraCode Nerd Font", sans-serif;
}

entry.spotlight-input {
    all: unset;
    color: @on_surface;
    font-size: 17px;
    font-weight: 400;
    caret-color: @primary;
    min-height: 26px;
}

.esc-pill {
    background-color: alpha(@surface_variant, 0.55);
    color: alpha(@on_surface_variant, 0.85);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 10.5px;
    font-weight: 600;
}

button.all-apps-btn {
    all: unset;
    background-color: alpha(@surface_variant, 0.55);
    color: @on_surface;
    border-radius: 7px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
    font-family: "JetBrainsMono Nerd Font Propo", "Inter", sans-serif;
}

button.all-apps-btn:hover {
    background-color: alpha(@primary, 0.28);
    color: @primary;
}

button.all-apps-btn-active {
    all: unset;
    background-color: @primary;
    color: @on_primary;
    border-radius: 7px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    font-family: "JetBrainsMono Nerd Font Propo", "Inter", sans-serif;
}

.spotlight-divider {
    background-color: alpha(@on_surface, 0.08);
    min-height: 1px;
}

.results-wrap {
    padding: 10px 12px 12px 12px;
}

.section-header {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.7px;
    color: alpha(@on_surface_variant, 0.7);
    padding: 2px 10px 6px 10px;
}

button.spot-row {
    all: unset;
    border-radius: 12px;
    padding: 9px 12px;
    margin: 1px 0;
}

button.spot-row:hover {
    background-color: alpha(@surface_variant, 0.38);
}

button.spot-row-selected {
    all: unset;
    background-color: alpha(@primary, 0.22);
    border: 1px solid alpha(@primary, 0.45);
    border-radius: 12px;
    padding: 8px 11px;
    margin: 1px 0;
}

.spot-row-name {
    font-size: 13.5px;
    font-weight: 600;
    color: @on_surface;
}

.spot-row-desc {
    font-size: 11px;
    color: alpha(@on_surface_variant, 0.82);
}

.return-badge {
    background-color: alpha(@primary, 0.24);
    color: @primary;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

.footer-bar {
    background-color: alpha(@surface, 0.45);
    border-top: 1px solid alpha(@on_surface, 0.07);
    border-bottom-left-radius: 20px;
    border-bottom-right-radius: 20px;
    padding: 8px 20px;
}

.footer-hint {
    font-size: 11px;
    color: alpha(@on_surface_variant, 0.72);
}

.empty-label {
    font-size: 13px;
    color: @on_surface_variant;
    padding: 24px 0;
}
"""


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


def load_apps() -> list[dict]:
    apps = []
    for info in Gio.AppInfo.get_all():
        if not info.should_show():
            continue
        name = (info.get_display_name() or info.get_name() or "").strip()
        if not name:
            continue
        desc = (info.get_description() or "").strip()
        exe = (info.get_executable() or "").strip()
        icon = info.get_icon()
        apps.append({
            "info": info,
            "name": name,
            "desc": desc,
            "icon": icon,
            "search": f"{name} {desc} {exe}".lower(),
        })
    apps.sort(key=lambda a: a["name"].lower())
    return apps


class SpotlightLauncher(Gtk.Application):
    def __init__(self, start_hidden: bool = False):
        super().__init__(application_id="dev.ashborn.waybar.applauncher")
        self.start_hidden = start_hidden
        self.win = None
        self.card = None
        self.provider = None
        self.css_mtime = 0.0
        self.search_entry = None
        self.all_btn = None
        self.body_revealer = None
        self.list_box = None
        self.scroll = None
        self.apps: list[dict] = []
        self.filtered: list[dict] = []
        self.row_widgets: list[Gtk.Button] = []
        self.selected_idx = 0

    def _reload_css_if_needed(self):
        mtime = os.path.getmtime(COLORS_CSS) if os.path.isfile(COLORS_CSS) else 0.0
        if self.provider is not None and mtime == self.css_mtime:
            return
        self.css_mtime = mtime
        if self.provider is None:
            self.provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        css_text = CSS.replace("__COLORS_CSS__", COLORS_CSS if mtime else "/dev/null")
        self.provider.load_from_data(css_text.encode("utf-8"))

    def do_activate(self):
        if self.win is not None:
            self.toggle_panel()
            return

        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))

        self._reload_css_if_needed()

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_decorated(False)
        self.win.add_css_class("launcher-root")

        Gtk4LayerShell.init_for_window(self.win)
        Gtk4LayerShell.set_layer(self.win, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_namespace(self.win, "waybar-app-launcher")
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.RIGHT, True)
        Gtk4LayerShell.set_keyboard_mode(self.win, Gtk4LayerShell.KeyboardMode.ON_DEMAND)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self.on_key_pressed)
        self.win.add_controller(key_ctrl)

        backdrop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        backdrop.set_hexpand(True)
        backdrop.set_vexpand(True)
        self.win.set_child(backdrop)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.card = card
        card.add_css_class("spotlight-shell")
        card.set_size_request(580, -1)
        card.set_halign(Gtk.Align.CENTER)
        card.set_valign(Gtk.Align.START)
        card.set_margin_top(150)
        backdrop.append(card)

        click_ctrl = Gtk.GestureClick()
        click_ctrl.connect("pressed", self.on_backdrop_click)
        self.win.add_controller(click_ctrl)

        # Search Bar
        search_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        search_bar.add_css_class("spotlight-search-bar")
        s_icon = Gtk.Label(label="󰍉")
        s_icon.add_css_class("search-glyph")

        self.search_entry = Gtk.Entry()
        self.search_entry.set_hexpand(True)
        self.search_entry.set_placeholder_text("Ashborn Search...")
        self.search_entry.add_css_class("spotlight-input")
        self.search_entry.connect("changed", self.on_search_changed)
        self.search_entry.connect("activate", lambda _: self.launch_selected())

        self.all_btn = Gtk.Button(label="󰀻 All")
        self.all_btn.set_tooltip_text("Show all applications")
        self.all_btn.add_css_class("all-apps-btn")
        self.all_btn.connect("clicked", lambda _: self.toggle_all_apps())

        esc_pill = Gtk.Label(label="ESC")
        esc_pill.add_css_class("esc-pill")

        search_bar.append(s_icon)
        search_bar.append(self.search_entry)
        search_bar.append(self.all_btn)
        search_bar.append(esc_pill)
        card.append(search_bar)

        # Expandable Results Area
        self.body_revealer = Gtk.Revealer()
        self.body_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.body_revealer.set_transition_duration(80)
        self.body_revealer.set_reveal_child(False)

        body_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        div = Gtk.Box()
        div.add_css_class("spotlight-divider")
        body_wrap.append(div)

        results_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        results_wrap.add_css_class("results-wrap")

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_propagate_natural_height(True)
        self.scroll.set_max_content_height(350)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.scroll.set_child(self.list_box)
        results_wrap.append(self.scroll)
        body_wrap.append(results_wrap)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        footer.add_css_class("footer-bar")
        hint = Gtk.Label(label="↑↓  Navigate    ·    ↵  Open App    ·    Esc  Close")
        hint.add_css_class("footer-hint")
        hint.set_hexpand(True)
        hint.set_xalign(0)
        footer.append(hint)
        body_wrap.append(footer)

        self.body_revealer.set_child(body_wrap)
        card.append(self.body_revealer)

        self.apps = load_apps()
        self.filtered = self.apps[:24]
        self.render_rows()

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

    def _sync_all_btn(self, active: bool):
        if self.all_btn is None:
            return
        self.all_btn.remove_css_class("all-apps-btn-active" if not active else "all-apps-btn")
        self.all_btn.add_css_class("all-apps-btn-active" if active else "all-apps-btn")

    def toggle_all_apps(self):
        if self.body_revealer.get_reveal_child() and not self.search_entry.get_text().strip():
            self.body_revealer.set_reveal_child(False)
            self._sync_all_btn(False)
            self.search_entry.grab_focus()
            return
        if self.search_entry.get_text():
            self.search_entry.set_text("")
        self.filtered = list(self.apps)
        self.selected_idx = 0
        self.render_rows()
        self.body_revealer.set_reveal_child(True)
        self._sync_all_btn(True)
        self.search_entry.grab_focus()

    def show_panel(self):
        hide_other()
        self.win.present()
        self.search_entry.grab_focus()
        if self.search_entry.get_text():
            self.search_entry.set_text("")
        self.body_revealer.set_reveal_child(False)
        self._sync_all_btn(False)
        GLib.idle_add(self._post_show_refresh)

    def _post_show_refresh(self):
        self._reload_css_if_needed()
        return False

    def hide_panel(self):
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

    def on_search_changed(self, _entry):
        q = self.search_entry.get_text().strip().lower()
        if not q:
            self.body_revealer.set_reveal_child(False)
            self._sync_all_btn(False)
            self.filtered = self.apps[:24]
            self.selected_idx = 0
            return

        self._sync_all_btn(False)
        starts = [a for a in self.apps if a["name"].lower().startswith(q)]
        contains = [a for a in self.apps if q in a["search"] and a not in starts]
        self.filtered = (starts + contains)[:24]
        self.selected_idx = 0
        self.render_rows()
        self.body_revealer.set_reveal_child(True)

    def render_rows(self):
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)
        self.row_widgets = []

        if not self.filtered:
            lbl = Gtk.Label(label="No matching applications")
            lbl.add_css_class("empty-label")
            self.list_box.append(lbl)
            return

        hdr = Gtk.Label(label="TOP HIT" if self.search_entry.get_text().strip() else "APPLICATIONS")
        hdr.set_xalign(0)
        hdr.add_css_class("section-header")
        self.list_box.append(hdr)

        for idx, app in enumerate(self.filtered):
            btn = Gtk.Button()
            btn.add_css_class("spot-row-selected" if idx == self.selected_idx else "spot-row")
            btn.connect("clicked", lambda _, a=app: self.launch_app(a))

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            if app["icon"] is not None:
                img = Gtk.Image.new_from_gicon(app["icon"])
            else:
                img = Gtk.Image.new_from_icon_name("application-x-executable")
            img.set_pixel_size(28)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.set_hexpand(True)
            name_lbl = Gtk.Label(label=app["name"])
            name_lbl.set_xalign(0)
            name_lbl.set_ellipsize(3)
            name_lbl.add_css_class("spot-row-name")
            vbox.append(name_lbl)

            if app["desc"]:
                desc_lbl = Gtk.Label(label=app["desc"])
                desc_lbl.set_xalign(0)
                desc_lbl.set_ellipsize(3)
                desc_lbl.add_css_class("spot-row-desc")
                vbox.append(desc_lbl)

            hbox.append(img)
            hbox.append(vbox)

            if idx == self.selected_idx:
                ret = Gtk.Label(label="↵")
                ret.add_css_class("return-badge")
                hbox.append(ret)

            btn.set_child(hbox)
            self.list_box.append(btn)
            self.row_widgets.append(btn)

    def update_selection(self, new_idx: int):
        if not self.row_widgets:
            return
        new_idx = max(0, min(new_idx, len(self.row_widgets) - 1))
        if new_idx == self.selected_idx:
            return
        self.selected_idx = new_idx
        self.render_rows()

        adj = self.scroll.get_vadjustment()
        btn = self.row_widgets[self.selected_idx]
        alloc = btn.get_allocation()
        page_top = adj.get_value()
        page_bot = page_top + adj.get_page_size()
        if alloc.y < page_top:
            adj.set_value(alloc.y)
        elif alloc.y + alloc.height > page_bot:
            adj.set_value(alloc.y + alloc.height - adj.get_page_size())

    def on_key_pressed(self, _ctrl, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            self.hide_panel()
            return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Tab):
            if not self.body_revealer.get_reveal_child():
                self.render_rows()
                self.body_revealer.set_reveal_child(True)
            else:
                self.update_selection(self.selected_idx + 1)
            return True
        if keyval in (Gdk.KEY_Up, Gdk.KEY_ISO_Left_Tab):
            if self.body_revealer.get_reveal_child():
                self.update_selection(self.selected_idx - 1)
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.launch_selected()
            return True
        return False

    def launch_selected(self):
        if 0 <= self.selected_idx < len(self.filtered):
            self.launch_app(self.filtered[self.selected_idx])

    def launch_app(self, app: dict):
        self.hide_panel()
        try:
            app["info"].launch([], None)
        except Exception:
            pass


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
        app = SpotlightLauncher(start_hidden=start_hidden)
        app.run(None)
    finally:
        cleanup_pid()
