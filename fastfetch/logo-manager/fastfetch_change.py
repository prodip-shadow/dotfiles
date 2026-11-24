#!/usr/bin/env python3
"""Ryoku Interactive Fastfetch Logo Manager (Phase 1)."""

from __future__ import annotations

import curses
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MANAGER_DIR = Path(__file__).resolve().parent
if str(MANAGER_DIR) not in sys.path:
    sys.path.insert(0, str(MANAGER_DIR))

from modules.discovery import DiscoveryResult, LogoItem, discover_all_logos
from modules.preview import AsciiPreviewData, load_ascii_preview, load_pokemon_preview
from modules.renderer import (
    ImageInfo,
    InlineImageCache,
    get_image_info,
    render_fullscreen_image,
)
from modules.settings import (
    DEFAULT_SETTINGS,
    VALID_ASPECT_MODES,
    VALID_ASCII_TYPES,
    VALID_HORIZONTAL_ALIGNMENTS,
    VALID_IMAGE_PROTOCOLS,
    VALID_VERTICAL_POSITIONS,
    LogoSettings,
    load_settings,
    save_settings,
)
from modules.terminal import TerminalCapabilities, detect_capabilities

CATEGORIES = ("ascii", "images", "pokemon")
CATEGORY_LABELS = {"ascii": "ASCII", "images": "IMAGES", "pokemon": "POKEMON"}
PANELS = ("categories", "logos", "settings", "preview")

# UI color pair IDs
PAIR_DEFAULT = 1
PAIR_HEADER = 2
PAIR_ACCENT = 3
PAIR_SELECTED = 4
PAIR_ACTIVE = 5
PAIR_MUTED = 6
PAIR_WARN = 7
PAIR_ERROR = 8
PAIR_OK = 9
PAIR_BORDER_FOCUS = 10
DYNAMIC_PAIR_START = 16


class ColorManager:
    """Manages UI and dynamic 256-color curses pairs safely."""

    def __init__(self) -> None:
        self.has_colors = curses.has_colors()
        self.max_colors = 0
        self.max_pairs = 0
        self._cache: Dict[Tuple[int, int], int] = {}
        self._next_pair = DYNAMIC_PAIR_START

        if self.has_colors:
            try:
                curses.start_color()
                curses.use_default_colors()
            except curses.error:
                self.has_colors = False
                return
            self.max_colors = getattr(curses, "COLORS", 8)
            self.max_pairs = getattr(curses, "COLOR_PAIRS", 64)
            self._init_ui_pairs()

    def _safe_init(self, pair_id: int, fg: int, bg: int) -> None:
        if not self.has_colors or pair_id >= self.max_pairs:
            return
        fg_c = fg if fg < self.max_colors else (fg % max(1, self.max_colors))
        bg_c = bg if bg < self.max_colors else -1
        try:
            curses.init_pair(pair_id, fg_c, bg_c)
        except curses.error:
            pass

    def _init_ui_pairs(self) -> None:
        red = 196 if self.max_colors >= 256 else curses.COLOR_RED
        cream = 230 if self.max_colors >= 256 else curses.COLOR_WHITE
        muted = 244 if self.max_colors >= 256 else curses.COLOR_WHITE
        green = 114 if self.max_colors >= 256 else curses.COLOR_GREEN
        yellow = 214 if self.max_colors >= 256 else curses.COLOR_YELLOW
        dark_bg = 236 if self.max_colors >= 256 else curses.COLOR_BLUE
        sel_bg = 238 if self.max_colors >= 256 else curses.COLOR_CYAN

        self._safe_init(PAIR_DEFAULT, -1, -1)
        self._safe_init(PAIR_HEADER, cream, dark_bg)
        self._safe_init(PAIR_ACCENT, red, -1)
        self._safe_init(PAIR_SELECTED, cream, sel_bg)
        self._safe_init(PAIR_ACTIVE, green, -1)
        self._safe_init(PAIR_MUTED, muted, -1)
        self._safe_init(PAIR_WARN, yellow, -1)
        self._safe_init(PAIR_ERROR, red, -1)
        self._safe_init(PAIR_OK, green, -1)
        self._safe_init(PAIR_BORDER_FOCUS, red, -1)

    def ui(self, pair_id: int) -> int:
        if not self.has_colors:
            return 0
        return curses.color_pair(pair_id)

    def get_dynamic_pair(self, fg: int, bg: int) -> int:
        if not self.has_colors or self.max_pairs <= DYNAMIC_PAIR_START:
            return 0
        fg_c = fg if (fg == -1 or fg < self.max_colors) else (fg % max(1, self.max_colors))
        bg_c = bg if (bg == -1 or bg < self.max_colors) else (bg % max(1, self.max_colors))
        key = (fg_c, bg_c)
        if key in self._cache:
            return curses.color_pair(self._cache[key])
        if self._next_pair < min(self.max_pairs, 4096):
            pid = self._next_pair
            self._next_pair += 1
            try:
                curses.init_pair(pid, fg_c, bg_c)
                self._cache[key] = pid
                return curses.color_pair(pid)
            except curses.error:
                return 0
        return 0


class LogoManagerApp:
    """Interactive curses TUI for managing Ryoku Fastfetch logos."""

    def __init__(self, fastfetch_dir: Path) -> None:
        self.fastfetch_dir = fastfetch_dir
        self.cfg_path = fastfetch_dir / "logo-settings.jsonc"
        self.backup_dir = fastfetch_dir / "backups"
        self.caps: TerminalCapabilities = detect_capabilities()

        self.saved_settings, self.base_raw, load_err = load_settings(self.cfg_path)
        self.working_settings: LogoSettings = self.saved_settings.clone()
        self.discovery: Dict[str, DiscoveryResult] = discover_all_logos(self.fastfetch_dir)

        self.focus_panel: str = "logos"
        mode_to_cat = {"ascii": 0, "images": 1, "pokemon": 2}
        self.cat_index: int = mode_to_cat.get(self.working_settings.mode, 1)
        self.logo_indices: Dict[str, int] = {"ascii": 0, "images": 0, "pokemon": 0}
        self.logo_scroll: Dict[str, int] = {"ascii": 0, "images": 0, "pokemon": 0}
        self.setting_index: int = 0
        self.preview_scroll_y: int = 0
        self.preview_scroll_x: int = 0

        self.show_help: bool = False
        self.status_msg: str = load_err or "Ready. Navigate with arrows, Enter to select, A to apply."
        self.status_level: str = "warn" if load_err else "info"

        self._ascii_cache: Dict[str, AsciiPreviewData] = {}
        self._img_info_cache: Dict[str, ImageInfo] = {}
        self._inline_img_cache = InlineImageCache()

        self._sync_selection_to_active()

    @property
    def active_category(self) -> str:
        return CATEGORIES[self.cat_index]

    @property
    def current_items(self) -> List[LogoItem]:
        return self.discovery[self.active_category].items

    @property
    def selected_logo(self) -> Optional[LogoItem]:
        items = self.current_items
        if not items:
            return None
        idx = max(0, min(len(items) - 1, self.logo_indices[self.active_category]))
        self.logo_indices[self.active_category] = idx
        return items[idx]

    @property
    def has_unsaved_changes(self) -> bool:
        return self.working_settings != self.saved_settings

    def _sync_selection_to_active(self) -> None:
        """Position cursor on the currently configured logo if present."""
        for cat, target_raw in (
            ("ascii", self.working_settings.ascii_source),
            ("images", self.working_settings.image_source),
        ):
            target = Path(os.path.expanduser(target_raw)).resolve(strict=False)
            for idx, item in enumerate(self.discovery[cat].items):
                if item.path.resolve(strict=False) == target:
                    self.logo_indices[cat] = idx
                    break
        for idx, item in enumerate(self.discovery["pokemon"].items):
            if item.name == self.working_settings.pokemon_name:
                self.logo_indices["pokemon"] = idx
                break

    def _is_logo_working_active(self, item: LogoItem) -> bool:
        if item.category == "ascii" and self.working_settings.mode == "ascii":
            cur = Path(os.path.expanduser(self.working_settings.ascii_source)).resolve(strict=False)
            return item.path.resolve(strict=False) == cur
        if item.category == "images" and self.working_settings.mode == "image":
            cur = Path(os.path.expanduser(self.working_settings.image_source)).resolve(strict=False)
            return item.path.resolve(strict=False) == cur
        if item.category == "pokemon" and self.working_settings.mode == "pokemon":
            return item.name == self.working_settings.pokemon_name
        return False

    def _settings_fields(self) -> List[Tuple[str, str, str]]:
        """Return list of (key, label, display_value)."""
        s = self.working_settings
        proto_val = s.ascii_type if self.active_category == "ascii" else s.image_protocol
        proto_label = "ASCII Type" if self.active_category == "ascii" else "Protocol"
        return [
            ("width", "Width", str(s.width)),
            ("height", "Height", str(s.height)),
            ("aspect_mode", "Aspect", s.aspect_mode),
            ("horizontal_alignment", "H-Align", s.horizontal_alignment),
            ("vertical_position", "V-Pos", s.vertical_position),
            ("pad_top", "Pad Top", str(s.padding.top)),
            ("pad_bottom", "Pad Bot", str(s.padding.bottom)),
            ("pad_left", "Pad Left", str(s.padding.left)),
            ("pad_right", "Pad Right", str(s.padding.right)),
            ("protocol", proto_label, proto_val),
        ]

    def _select_current_logo(self) -> None:
        item = self.selected_logo
        if not item:
            self.set_status("No logo selected.", "warn")
            return
        if not item.readable:
            self.set_status(f"Cannot select unreadable file: {item.error}", "error")
            return
        if item.category == "ascii":
            self.working_settings.mode = "ascii"
            self.working_settings.ascii_source = item.display_path
        elif item.category == "pokemon":
            self.working_settings.mode = "pokemon"
            self.working_settings.pokemon_name = item.name
        else:
            self.working_settings.mode = "image"
            self.working_settings.image_source = item.display_path
        self.preview_scroll_y = 0
        self.preview_scroll_x = 0
        self.set_status(f"Selected {item.name} (unsaved — press A to Apply)", "info")

    def set_status(self, msg: str, level: str = "info") -> None:
        self.status_msg = msg
        self.status_level = level

    def refresh_logos(self) -> None:
        prev_name = self.selected_logo.name if self.selected_logo else None
        self.discovery = discover_all_logos(self.fastfetch_dir)
        self._ascii_cache.clear()
        self._img_info_cache.clear()
        if prev_name:
            for idx, item in enumerate(self.current_items):
                if item.name == prev_name:
                    self.logo_indices[self.active_category] = idx
                    break
        total_a = len(self.discovery["ascii"].items)
        total_i = len(self.discovery["images"].items)
        self.set_status(f"Refreshed logos: {total_a} ASCII, {total_i} images.", "ok")

    def apply_changes(self) -> None:
        try:
            backup_path, new_raw = save_settings(
                self.cfg_path,
                self.backup_dir,
                self.working_settings,
                self.base_raw,
            )
            self.base_raw = new_raw
            self.saved_settings = self.working_settings.clone()
            b_msg = f" (backup: {backup_path.name})" if backup_path else ""
            self.set_status(f"Applied to logo-settings.jsonc{b_msg}", "ok")
        except Exception as exc:
            self.set_status(f"Apply failed: {exc}", "error")

    def cancel_changes(self) -> None:
        self.working_settings = self.saved_settings.clone()
        mode_to_cat = {"ascii": 0, "images": 1, "pokemon": 2}
        self.cat_index = mode_to_cat.get(self.working_settings.mode, 1)
        self._sync_selection_to_active()
        self.preview_scroll_y = 0
        self.preview_scroll_x = 0
        self.set_status("Changes discarded. Restored previous configuration.", "info")

    def restore_defaults(self) -> None:
        cur = self.working_settings
        d = DEFAULT_SETTINGS
        cur.width = d.width
        cur.height = d.height
        cur.aspect_mode = d.aspect_mode
        cur.horizontal_alignment = d.horizontal_alignment
        cur.vertical_position = d.vertical_position
        cur.padding = d.padding.__class__(
            top=d.padding.top,
            right=d.padding.right,
            bottom=d.padding.bottom,
            left=d.padding.left,
        )
        cur.image_protocol = d.image_protocol
        cur.ascii_type = d.ascii_type
        cur.transparent_background = d.transparent_background
        cur.print_remaining = d.print_remaining
        cur.sync_derived_fields()
        self.set_status("Restored default logo settings (press A to Apply).", "warn")

    def _adjust_setting(self, key: str, delta: int) -> None:
        s = self.working_settings
        if key == "width":
            s.width = max(1, min(300, s.width + delta))
        elif key == "height":
            s.height = max(1, min(200, s.height + delta))
        elif key == "pad_top":
            s.padding.top = max(-20, min(100, s.padding.top + delta))
        elif key == "pad_bottom":
            s.padding.bottom = max(0, min(100, s.padding.bottom + delta))
        elif key == "pad_left":
            s.padding.left = max(0, min(100, s.padding.left + delta))
        elif key == "pad_right":
            s.padding.right = max(0, min(100, s.padding.right + delta))
        elif key == "aspect_mode":
            idx = VALID_ASPECT_MODES.index(s.aspect_mode)
            s.aspect_mode = VALID_ASPECT_MODES[(idx + delta) % len(VALID_ASPECT_MODES)]
        elif key == "horizontal_alignment":
            idx = VALID_HORIZONTAL_ALIGNMENTS.index(s.horizontal_alignment)
            s.horizontal_alignment = VALID_HORIZONTAL_ALIGNMENTS[
                (idx + delta) % len(VALID_HORIZONTAL_ALIGNMENTS)
            ]
        elif key == "vertical_position":
            idx = VALID_VERTICAL_POSITIONS.index(s.vertical_position)
            s.vertical_position = VALID_VERTICAL_POSITIONS[
                (idx + delta) % len(VALID_VERTICAL_POSITIONS)
            ]
        elif key == "protocol":
            if self.active_category == "ascii":
                idx = VALID_ASCII_TYPES.index(s.ascii_type)
                s.ascii_type = VALID_ASCII_TYPES[(idx + delta) % len(VALID_ASCII_TYPES)]
            else:
                idx = VALID_IMAGE_PROTOCOLS.index(s.image_protocol)
                s.image_protocol = VALID_IMAGE_PROTOCOLS[(idx + delta) % len(VALID_IMAGE_PROTOCOLS)]
        s.sync_derived_fields()

    def _reset_single_setting(self, key: str) -> None:
        s = self.working_settings
        d = DEFAULT_SETTINGS
        if key == "width":
            s.width = d.width
        elif key == "height":
            s.height = d.height
        elif key == "pad_top":
            s.padding.top = d.padding.top
        elif key == "pad_bottom":
            s.padding.bottom = d.padding.bottom
        elif key == "pad_left":
            s.padding.left = d.padding.left
        elif key == "pad_right":
            s.padding.right = d.padding.right
        elif key == "aspect_mode":
            s.aspect_mode = d.aspect_mode
        elif key == "horizontal_alignment":
            s.horizontal_alignment = d.horizontal_alignment
        elif key == "vertical_position":
            s.vertical_position = d.vertical_position
        elif key == "protocol":
            s.ascii_type = d.ascii_type
            s.image_protocol = d.image_protocol
        s.sync_derived_fields()
        self.set_status(f"Reset {key} to default (press A to Apply).", "info")

    def _prompt_numeric_input(self, stdscr: "curses._CursesWindow", label: str, current: int, min_v: int, max_v: int) -> Optional[int]:
        h, w = stdscr.getmaxyx()
        box_w = min(46, max(24, w - 4))
        box_h = 5
        y = max(0, (h - box_h) // 2)
        x = max(0, (w - box_w) // 2)

        win = curses.newwin(box_h, box_w, y, x)
        win.keypad(True)
        win.box()
        self._safe_addstr(win, 1, 2, f"Enter {label} ({min_v}..{max_v}):")
        self._safe_addstr(win, 3, 2, "Enter=OK  Esc=Cancel")
        buf = str(current)
        curses.curs_set(1)
        try:
            while True:
                self._safe_addstr(win, 2, 2, " " * (box_w - 4))
                self._safe_addstr(win, 2, 2, f"> {buf}")
                win.refresh()
                ch = win.getch()
                if ch == 27:  # Esc
                    return None
                if ch in (curses.KEY_ENTER, 10, 13):
                    try:
                        val = int(buf)
                    except ValueError:
                        self.set_status(f"Invalid integer: '{buf}'", "error")
                        return None
                    if not (min_v <= val <= max_v):
                        self.set_status(f"{label} must be between {min_v} and {max_v}", "error")
                        return None
                    return val
                if ch in (curses.KEY_BACKSPACE, 127, 8):
                    buf = buf[:-1]
                elif ch == ord("-") and min_v < 0 and not buf:
                    buf = "-"
                elif 48 <= ch <= 57 and len(buf) < 6:
                    buf += chr(ch)
        finally:
            curses.curs_set(0)

    def _confirm_quit_unsaved(self, stdscr: "curses._CursesWindow") -> str:
        """Ask user what to do with unsaved changes on Quit: 'quit', 'apply', or 'cancel'."""
        h, w = stdscr.getmaxyx()
        box_w = min(56, max(30, w - 4))
        box_h = 6
        y = max(0, (h - box_h) // 2)
        x = max(0, (w - box_w) // 2)
        win = curses.newwin(box_h, box_w, y, x)
        win.keypad(True)
        win.box()
        self._safe_addstr(win, 1, 2, "Unsaved changes detected!")
        self._safe_addstr(win, 2, 2, "[A] Apply & Quit  [Y] Quit without saving")
        self._safe_addstr(win, 3, 2, "[C/Esc] Cancel and stay")
        win.refresh()
        while True:
            ch = win.getch()
            if ch in (ord("a"), ord("A")):
                return "apply"
            if ch in (ord("y"), ord("Y"), ord("q"), ord("Q")):
                return "quit"
            if ch in (ord("c"), ord("C"), 27):
                return "cancel"

    def _launch_fullscreen_preview(self, stdscr: "curses._CursesWindow") -> None:
        item = self.selected_logo
        if not item:
            self.set_status("Nothing selected to preview.", "warn")
            return
        if not item.readable:
            self.set_status(f"Cannot preview unreadable file: {item.error}", "error")
            return

        if item.category == "images":
            info = self._get_image_info_cached(item)
            curses.def_prog_mode()
            curses.endwin()
            try:
                err = render_fullscreen_image(
                    item.path,
                    self.caps,
                    info,
                    self.working_settings.width,
                    self.working_settings.height,
                )
            finally:
                curses.reset_prog_mode()
                stdscr.refresh()
            if err:
                self.set_status(f"Preview notice: {err}", "warn")
            else:
                self.set_status(f"Previewed {item.name}", "info")
        else:
            # Focus preview panel for ASCII and reset scroll to top
            self.focus_panel = "preview"
            self.preview_scroll_y = 0
            self.preview_scroll_x = 0
            self.set_status(f"Previewing {item.name} (use arrows to scroll)", "info")

    def _get_ascii_cached(self, item: LogoItem) -> AsciiPreviewData:
        key = f"{item.category}:{item.path}"
        if key not in self._ascii_cache:
            if item.category == "pokemon":
                self._ascii_cache[key] = load_pokemon_preview(
                    item.name, self.working_settings.pokemon_no_title
                )
            else:
                self._ascii_cache[key] = load_ascii_preview(item.path)
        return self._ascii_cache[key]

    def _get_image_info_cached(self, item: LogoItem) -> ImageInfo:
        key = str(item.path)
        if key not in self._img_info_cache:
            self._img_info_cache[key] = get_image_info(item.path, self.caps.ffprobe_path)
        return self._img_info_cache[key]

    @staticmethod
    def _safe_addstr(win: "curses._CursesWindow", y: int, x: int, text: str, attr: int = 0) -> None:
        h, w = win.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        avail = w - max(0, x)
        if avail <= 0:
            return
        if x < 0:
            text = text[-x:]
            x = 0
            avail = w
        try:
            win.addnstr(y, x, text, avail, attr)
        except curses.error:
            pass

    def _draw_box(
        self,
        win: "curses._CursesWindow",
        y: int,
        x: int,
        h: int,
        w: int,
        title: str,
        focused: bool,
        colors: ColorManager,
    ) -> None:
        if h < 2 or w < 4:
            return
        attr = colors.ui(PAIR_BORDER_FOCUS) | curses.A_BOLD if focused else colors.ui(PAIR_MUTED)
        try:
            win.attron(attr)
            win.hline(y, x + 1, curses.ACS_HLINE, w - 2)
            win.hline(y + h - 1, x + 1, curses.ACS_HLINE, w - 2)
            win.vline(y + 1, x, curses.ACS_VLINE, h - 2)
            win.vline(y + 1, x + w - 1, curses.ACS_VLINE, h - 2)
            win.addch(y, x, curses.ACS_ULCORNER)
            win.addch(y, x + w - 1, curses.ACS_URCORNER)
            win.addch(y + h - 1, x, curses.ACS_LLCORNER)
            win.addch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)
            win.attroff(attr)
        except curses.error:
            pass
        if title and w > 6:
            t_str = f" {title} "
            self._safe_addstr(win, y, x + 2, t_str[: w - 4], attr)

    def render(self, stdscr: "curses._CursesWindow", colors: ColorManager) -> None:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        if max_y < 18 or max_x < 60:
            self._safe_addstr(
                stdscr,
                0,
                0,
                f"Terminal too small ({max_x}x{max_y}). Minimum 60x18 required.",
                colors.ui(PAIR_ERROR) | curses.A_BOLD,
            )
            self._safe_addstr(stdscr, 2, 0, "Resize window or press Q to quit.", colors.ui(PAIR_MUTED))
            stdscr.refresh()
            return

        # Header
        if self.working_settings.mode == "pokemon":
            active_name = self.working_settings.pokemon_name
        elif self.working_settings.mode == "ascii":
            active_name = Path(self.working_settings.ascii_source).name
        else:
            active_name = Path(self.working_settings.image_source).name
        unsaved_tag = " [UNSAVED]" if self.has_unsaved_changes else ""
        header_left = f" RYOKU FASTFETCH MANAGER"
        header_right = f"Active ({self.working_settings.mode.upper()}): {active_name}{unsaved_tag} "
        stdscr.hline(0, 0, " ", max_x, colors.ui(PAIR_HEADER))
        self._safe_addstr(stdscr, 0, 0, header_left, colors.ui(PAIR_HEADER) | curses.A_BOLD)
        if len(header_left) + len(header_right) < max_x:
            self._safe_addstr(
                stdscr,
                0,
                max_x - len(header_right),
                header_right,
                colors.ui(PAIR_WARN if unsaved_tag else PAIR_HEADER) | curses.A_BOLD,
            )

        # Layout heights
        footer_h = 3  # status + actions + keyhints
        settings_h = 7
        main_y = 1
        main_h = max_y - main_y - footer_h - settings_h
        if main_h < 6:
            settings_h = max(4, max_y - main_y - footer_h - 6)
            main_h = max_y - main_y - footer_h - settings_h

        # Column widths
        cat_w = max(16, min(20, max_x // 5))
        list_w = max(22, min(34, (max_x - cat_w) // 2))
        prev_w = max_x - cat_w - list_w

        # 1. Categories Panel
        self._draw_box(stdscr, main_y, 0, main_h, cat_w, "CATEGORIES", self.focus_panel == "categories", colors)
        for idx, cat in enumerate(CATEGORIES):
            count = len(self.discovery[cat].items)
            is_sel = idx == self.cat_index
            prefix = "> " if is_sel else "  "
            label = f"{prefix}{CATEGORY_LABELS[cat]} ({count})"
            attr = colors.ui(PAIR_SELECTED) | curses.A_BOLD if is_sel else colors.ui(PAIR_DEFAULT)
            self._safe_addstr(stdscr, main_y + 2 + idx, 2, label.ljust(cat_w - 4)[: cat_w - 4], attr)

        mode_note = f"Mode: {self.working_settings.mode.upper()}"
        self._safe_addstr(stdscr, main_y + 5, 2, mode_note[: cat_w - 4], colors.ui(PAIR_MUTED))

        # 2. Logo List Panel
        res = self.discovery[self.active_category]
        self._draw_box(stdscr, main_y, cat_w, main_h, list_w, "LOGO LIST", self.focus_panel == "logos", colors)
        inner_list_h = main_h - 2
        if res.error:
            self._safe_addstr(stdscr, main_y + 1, cat_w + 2, res.error[: list_w - 4], colors.ui(PAIR_ERROR))
        elif not res.items:
            self._safe_addstr(stdscr, main_y + 1, cat_w + 2, "(Empty directory)", colors.ui(PAIR_MUTED))
            self._safe_addstr(stdscr, main_y + 2, cat_w + 2, "Add files & press R", colors.ui(PAIR_MUTED))
        else:
            sel_idx = self.logo_indices[self.active_category]
            scroll = self.logo_scroll[self.active_category]
            if sel_idx < scroll:
                scroll = sel_idx
            elif sel_idx >= scroll + inner_list_h:
                scroll = sel_idx - inner_list_h + 1
            self.logo_scroll[self.active_category] = scroll

            for row in range(inner_list_h):
                idx = scroll + row
                if idx >= len(res.items):
                    break
                item = res.items[idx]
                is_sel = idx == sel_idx
                is_act = self._is_logo_working_active(item)
                mark = "*" if is_act else " "
                size_str = item.size_human
                name_max = max(6, list_w - 6 - len(size_str))
                disp_name = item.name[:name_max]
                line = f"{mark} {disp_name:<{name_max}} {size_str}"
                if not item.readable:
                    attr = colors.ui(PAIR_ERROR)
                elif is_sel:
                    attr = colors.ui(PAIR_SELECTED) | curses.A_BOLD
                elif is_act:
                    attr = colors.ui(PAIR_ACTIVE) | curses.A_BOLD
                else:
                    attr = colors.ui(PAIR_DEFAULT)
                self._safe_addstr(stdscr, main_y + 1 + row, cat_w + 2, line[: list_w - 4], attr)

        # 3. Preview Panel
        prev_x = cat_w + list_w
        self._draw_box(stdscr, main_y, prev_x, main_h, prev_w, "PREVIEW", self.focus_panel == "preview", colors)
        self._render_preview_panel(stdscr, main_y + 1, prev_x + 2, main_h - 2, prev_w - 4, colors)

        # 4. Settings Panel
        set_y = main_y + main_h
        self._draw_box(stdscr, set_y, 0, settings_h, max_x, "LOGO SETTINGS", self.focus_panel == "settings", colors)
        fields = self._settings_fields()
        cols = 2 if max_x >= 76 else 1
        col_w = (max_x - 4) // cols
        rows_per_col = (len(fields) + cols - 1) // cols
        for idx, (key, label, val) in enumerate(fields):
            c = idx // rows_per_col if cols > 1 else 0
            r = idx % rows_per_col
            if r >= settings_h - 2:
                continue
            fx = 2 + c * col_w
            fy = set_y + 1 + r
            is_sel = self.focus_panel == "settings" and idx == self.setting_index
            line = f"{label:<11}: < {val} >"
            attr = colors.ui(PAIR_SELECTED) | curses.A_BOLD if is_sel else colors.ui(PAIR_DEFAULT)
            self._safe_addstr(stdscr, fy, fx, line[: col_w - 2], attr)

        # 5. Footer: Status, Actions, Keybindings
        foot_y = set_y + settings_h
        status_pair = {
            "info": PAIR_DEFAULT,
            "ok": PAIR_OK,
            "warn": PAIR_WARN,
            "error": PAIR_ERROR,
        }.get(self.status_level, PAIR_DEFAULT)
        self._safe_addstr(stdscr, foot_y, 1, self.status_msg[: max_x - 2], colors.ui(status_pair))

        actions = "[A] Apply   [C] Cancel   [D] Defaults   [R] Refresh   [H] Help   [Q] Quit"
        self._safe_addstr(stdscr, foot_y + 1, 1, actions[: max_x - 2], colors.ui(PAIR_ACCENT) | curses.A_BOLD)

        hints = "Up/Dn: Item | Lt/Rt: Cat/Val | Tab: Panel | Enter: Select/Edit | Space: Preview | Esc: Back"
        self._safe_addstr(stdscr, foot_y + 2, 1, hints[: max_x - 2], colors.ui(PAIR_MUTED))

        if self.show_help:
            self._render_help_modal(stdscr, colors)

        stdscr.refresh()

    def _render_preview_panel(
        self,
        stdscr: "curses._CursesWindow",
        y: int,
        x: int,
        h: int,
        w: int,
        colors: ColorManager,
    ) -> None:
        if h < 2 or w < 10:
            return
        item = self.selected_logo
        if not item:
            self._safe_addstr(stdscr, y, x, "No logo selected.", colors.ui(PAIR_MUTED))
            return
        if not item.readable:
            self._safe_addstr(stdscr, y, x, f"{item.name}: {item.error}", colors.ui(PAIR_ERROR))
            return

        if item.category in ("ascii", "pokemon"):
            data = self._get_ascii_cached(item)
            if data.error:
                self._safe_addstr(stdscr, y, x, data.error[:w], colors.ui(PAIR_ERROR))
                return
            meta = f"{item.name} | {data.max_width}x{data.total_lines} chars | {item.size_human}"
            if data.truncated:
                meta += " [truncated]"
            self._safe_addstr(stdscr, y, x, meta[:w], colors.ui(PAIR_MUTED))

            view_h = h - 1
            max_sy = max(0, data.total_lines - view_h)
            max_sx = max(0, data.max_width - w)
            self.preview_scroll_y = max(0, min(max_sy, self.preview_scroll_y))
            self.preview_scroll_x = max(0, min(max_sx, self.preview_scroll_x))

            for r in range(view_h):
                line_idx = self.preview_scroll_y + r
                if line_idx >= data.total_lines:
                    break
                spans = data.lines[line_idx]
                col_cursor = -self.preview_scroll_x
                for span in spans:
                    text = span.text
                    if col_cursor + len(text) <= 0:
                        col_cursor += len(text)
                        continue
                    if col_cursor < 0:
                        text = text[-col_cursor:]
                        col_cursor = 0
                    if col_cursor >= w:
                        break
                    attr = colors.get_dynamic_pair(span.fg, span.bg)
                    if span.bold:
                        attr |= curses.A_BOLD
                    if span.dim:
                        attr |= curses.A_DIM
                    if span.underline:
                        attr |= curses.A_UNDERLINE
                    if span.reverse:
                        attr |= curses.A_REVERSE
                    self._safe_addstr(stdscr, y + 1 + r, x + col_cursor, text[: w - col_cursor], attr)
                    col_cursor += len(text)
        else:
            info = self._get_image_info_cached(item)
            if not info.valid:
                self._safe_addstr(stdscr, y, x, f"{item.name}: {info.error}", colors.ui(PAIR_ERROR))
                return
            meta = f"{item.name} | {info.width}x{info.height} {info.format_name} | {item.size_human}"
            self._safe_addstr(stdscr, y, x, meta[:w], colors.ui(PAIR_MUTED))

            grid, err = self._inline_img_cache.get_halfblock_grid(
                item.path,
                w,
                h - 2,
                self.working_settings.aspect_mode,
                self.working_settings.width,
                self.working_settings.height,
                self.caps.ffmpeg_path,
                info,
            )
            if grid:
                off_x = x + max(0, (w - grid.cols) // 2)
                for r, row_cells in enumerate(grid.cells):
                    if r >= h - 2:
                        break
                    for c, (fg, bg) in enumerate(row_cells):
                        if c >= w:
                            break
                        attr = colors.get_dynamic_pair(fg, bg)
                        self._safe_addstr(stdscr, y + 1 + r, off_x + c, "▀", attr)
                renderer_name = self.caps.best_fullscreen_renderer or "none"
                hint = f"Space: full preview ({renderer_name})"
                self._safe_addstr(stdscr, y + h - 1, x, hint[:w], colors.ui(PAIR_MUTED))
            else:
                self._safe_addstr(stdscr, y + 2, x, err or "Inline preview unavailable", colors.ui(PAIR_WARN))
                self._safe_addstr(stdscr, y + 3, x, "Press Space for native preview.", colors.ui(PAIR_MUTED))

    def _render_help_modal(self, stdscr: "curses._CursesWindow", colors: ColorManager) -> None:
        h, w = stdscr.getmaxyx()
        bw = min(68, w - 4)
        bh = min(19, h - 2)
        sy = max(0, (h - bh) // 2)
        sx = max(0, (w - bw) // 2)
        win = curses.newwin(bh, bw, sy, sx)
        win.erase()
        win.box()
        lines = [
            "RYOKU FASTFETCH LOGO MANAGER - HELP",
            "",
            "Navigation:",
            "  Up / Down     : Move item / scroll ASCII preview",
            "  Left / Right  : Switch category / adjust setting",
            "  Tab           : Cycle panels (Categories/Logos/Settings/Preview)",
            "  Enter         : Select logo / edit numeric setting",
            "  Space         : Full-screen preview (Ghostty kitten icat)",
            "  Backspace / X : Reset focused setting to default",
            "",
            "Actions:",
            "  A : Apply & save   C : Cancel changes   R : Refresh logos",
            "  D : Restore all defaults   H : Help   Esc : Close   Q : Quit",
            "",
            "Fastfetch Notes:",
            "  - H-Align 'center' maps to Fastfetch position 'top'.",
            "  - V-Pos is stored for compatibility; use Pad Top for offset.",
            "  - Drop new logos in ~/.config/fastfetch/logos/{ascii,images}/",
        ]
        for idx, line in enumerate(lines[: bh - 2]):
            attr = colors.ui(PAIR_ACCENT) | curses.A_BOLD if idx == 0 else colors.ui(PAIR_DEFAULT)
            self._safe_addstr(win, 1 + idx, 2, line[: bw - 4], attr)
        win.refresh()

    def handle_key(self, stdscr: "curses._CursesWindow", ch: int) -> bool:
        """Process a single key event. Returns False when app should exit."""
        if ch == curses.KEY_RESIZE:
            return True

        if self.show_help:
            if ch in (27, ord("h"), ord("H"), ord("?"), ord("q"), ord("Q"), 10, 13):
                self.show_help = False
            return True

        # Global shortcuts
        if ch in (ord("q"), ord("Q")):
            if self.has_unsaved_changes:
                choice = self._confirm_quit_unsaved(stdscr)
                if choice == "apply":
                    self.apply_changes()
                    return False
                if choice == "quit":
                    return False
                return True
            return False

        if ch in (ord("h"), ord("H"), ord("?")):
            self.show_help = True
            return True
        if ch in (ord("a"), ord("A")):
            self.apply_changes()
            return True
        if ch in (ord("c"), ord("C")):
            self.cancel_changes()
            return True
        if ch in (ord("r"), ord("R")):
            self.refresh_logos()
            return True
        if ch in (ord("d"), ord("D")):
            self.restore_defaults()
            return True
        if ch == ord(" "):
            self._launch_fullscreen_preview(stdscr)
            return True
        if ch == 9:  # Tab
            idx = PANELS.index(self.focus_panel)
            self.focus_panel = PANELS[(idx + 1) % len(PANELS)]
            return True
        if ch == curses.KEY_BTAB:  # Shift+Tab
            idx = PANELS.index(self.focus_panel)
            self.focus_panel = PANELS[(idx - 1) % len(PANELS)]
            return True
        if ch == 27:  # Esc
            if self.focus_panel != "logos":
                self.focus_panel = "logos"
            return True

        # Panel-specific navigation
        if self.focus_panel == "categories":
            if ch in (curses.KEY_UP, curses.KEY_LEFT):
                self.cat_index = (self.cat_index - 1) % len(CATEGORIES)
            elif ch in (curses.KEY_DOWN, curses.KEY_RIGHT):
                self.cat_index = (self.cat_index + 1) % len(CATEGORIES)
            elif ch in (10, 13, curses.KEY_ENTER):
                self.focus_panel = "logos"

        elif self.focus_panel == "logos":
            items = self.current_items
            if ch == curses.KEY_LEFT:
                self.cat_index = (self.cat_index - 1) % len(CATEGORIES)
                self.preview_scroll_y = 0
                self.preview_scroll_x = 0
            elif ch == curses.KEY_RIGHT:
                self.cat_index = (self.cat_index + 1) % len(CATEGORIES)
                self.preview_scroll_y = 0
                self.preview_scroll_x = 0
            elif ch == curses.KEY_UP and items:
                self.logo_indices[self.active_category] = max(0, self.logo_indices[self.active_category] - 1)
                self.preview_scroll_y = 0
                self.preview_scroll_x = 0
            elif ch == curses.KEY_DOWN and items:
                self.logo_indices[self.active_category] = min(
                    len(items) - 1, self.logo_indices[self.active_category] + 1
                )
                self.preview_scroll_y = 0
                self.preview_scroll_x = 0
            elif ch in (10, 13, curses.KEY_ENTER):
                self._select_current_logo()

        elif self.focus_panel == "settings":
            fields = self._settings_fields()
            key, label, _ = fields[self.setting_index]
            if ch == curses.KEY_UP:
                self.setting_index = (self.setting_index - 1) % len(fields)
            elif ch == curses.KEY_DOWN:
                self.setting_index = (self.setting_index + 1) % len(fields)
            elif ch == curses.KEY_LEFT:
                self._adjust_setting(key, -1)
            elif ch == curses.KEY_RIGHT:
                self._adjust_setting(key, 1)
            elif ch in (curses.KEY_BACKSPACE, 127, 8, ord("x"), ord("X")):
                self._reset_single_setting(key)
            elif ch in (10, 13, curses.KEY_ENTER):
                bounds = {
                    "width": (self.working_settings.width, 1, 300),
                    "height": (self.working_settings.height, 1, 200),
                    "pad_top": (self.working_settings.padding.top, -20, 100),
                    "pad_bottom": (self.working_settings.padding.bottom, 0, 100),
                    "pad_left": (self.working_settings.padding.left, 0, 100),
                    "pad_right": (self.working_settings.padding.right, 0, 100),
                }
                if key in bounds:
                    cur, lo, hi = bounds[key]
                    new_val = self._prompt_numeric_input(stdscr, label, cur, lo, hi)
                    if new_val is not None:
                        if key == "width":
                            self.working_settings.width = new_val
                        elif key == "height":
                            self.working_settings.height = new_val
                        elif key == "pad_top":
                            self.working_settings.padding.top = new_val
                        elif key == "pad_bottom":
                            self.working_settings.padding.bottom = new_val
                        elif key == "pad_left":
                            self.working_settings.padding.left = new_val
                        elif key == "pad_right":
                            self.working_settings.padding.right = new_val
                else:
                    self._adjust_setting(key, 1)

        elif self.focus_panel == "preview":
            if ch == curses.KEY_UP:
                self.preview_scroll_y = max(0, self.preview_scroll_y - 1)
            elif ch == curses.KEY_DOWN:
                self.preview_scroll_y += 1
            elif ch == curses.KEY_LEFT:
                self.preview_scroll_x = max(0, self.preview_scroll_x - 2)
            elif ch == curses.KEY_RIGHT:
                self.preview_scroll_x += 2

        return True

    def run(self, stdscr: "curses._CursesWindow") -> int:
        curses.curs_set(0)
        stdscr.keypad(True)
        curses.set_escdelay(25)
        colors = ColorManager()

        running = True
        while running:
            self.render(stdscr, colors)
            ch = stdscr.getch()
            running = self.handle_key(stdscr, ch)
        return 0


def main() -> int:
    xdg_cfg = os.environ.get("XDG_CONFIG_HOME")
    base_cfg = Path(xdg_cfg) if xdg_cfg else Path.home() / ".config"
    fastfetch_dir = base_cfg / "fastfetch"

    app = LogoManagerApp(fastfetch_dir)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Error: fastfetch-change requires an interactive terminal (TTY).", file=sys.stderr)
        return 1
    try:
        return curses.wrapper(app.run)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"fastfetch-change fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
