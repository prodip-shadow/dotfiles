"""Terminal and image-renderer capability detection."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TerminalCapabilities:
    """Detected terminal environment and available rendering utilities."""

    term: str
    term_program: str
    is_ghostty: bool
    is_kitty: bool
    supports_kitty_graphics: bool
    supports_sixel: bool
    fastfetch_path: Optional[str]
    kitten_path: Optional[str]
    chafa_path: Optional[str]
    viu_path: Optional[str]
    img2sixel_path: Optional[str]
    ffmpeg_path: Optional[str]
    ffprobe_path: Optional[str]

    @property
    def best_fullscreen_renderer(self) -> Optional[str]:
        """Return the highest-fidelity external renderer for full-screen preview."""
        if self.supports_kitty_graphics and self.kitten_path:
            return "kitten"
        if self.chafa_path:
            return "chafa"
        if self.viu_path:
            return "viu"
        if self.supports_sixel and self.img2sixel_path:
            return "img2sixel"
        if self.ffmpeg_path:
            return "ffmpeg-halfblock"
        return None

    @property
    def inline_renderer(self) -> Optional[str]:
        """Return the best renderer safe for inline curses preview."""
        if self.ffmpeg_path:
            return "ffmpeg-halfblock"
        if self.chafa_path:
            return "chafa-text"
        return None


def detect_capabilities() -> TerminalCapabilities:
    """Detect current terminal capabilities and installed CLI tools."""
    term = os.environ.get("TERM", "")
    term_program = os.environ.get("TERM_PROGRAM", "")
    kitty_win = os.environ.get("KITTY_WINDOW_ID", "")

    is_ghostty = "ghostty" in term.lower() or term_program.lower() == "ghostty"
    is_kitty = "kitty" in term.lower() or term_program.lower() == "kitty" or bool(kitty_win)

    kitten_path = shutil.which("kitten")
    chafa_path = shutil.which("chafa")
    viu_path = shutil.which("viu")
    img2sixel_path = shutil.which("img2sixel")
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    fastfetch_path = shutil.which("fastfetch")

    supports_kitty_graphics = is_ghostty or is_kitty
    supports_sixel = is_ghostty or "sixel" in term.lower() or term_program.lower() in {
        "wezterm",
        "foot",
        "mlterm",
        "contour",
    }

    return TerminalCapabilities(
        term=term,
        term_program=term_program,
        is_ghostty=is_ghostty,
        is_kitty=is_kitty,
        supports_kitty_graphics=supports_kitty_graphics,
        supports_sixel=supports_sixel,
        fastfetch_path=fastfetch_path,
        kitten_path=kitten_path,
        chafa_path=chafa_path,
        viu_path=viu_path,
        img2sixel_path=img2sixel_path,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
    )
