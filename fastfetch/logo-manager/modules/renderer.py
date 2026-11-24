"""Image metadata extraction, inline half-block preview, and fullscreen Ghostty preview."""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import termios
import tty
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .preview import rgb_to_xterm256
from .terminal import TerminalCapabilities


@dataclass(frozen=True)
class ImageInfo:
    """Basic metadata for an image logo."""

    width: int
    height: int
    format_name: str
    valid: bool
    error: Optional[str] = None

    @property
    def aspect_ratio(self) -> float:
        if self.height <= 0:
            return 1.0
        return self.width / self.height


def _read_png_size(fh) -> Optional[Tuple[int, int]]:
    sig = fh.read(8)
    if sig != b"\x89PNG\r\n\x1a\n":
        return None
    ihdr = fh.read(16)
    if len(ihdr) < 16 or ihdr[4:8] != b"IHDR":
        return None
    w, h = struct.unpack(">II", ihdr[8:16])
    return w, h


def _read_jpeg_size(fh) -> Optional[Tuple[int, int]]:
    if fh.read(2) != b"\xff\xd8":
        return None
    while True:
        byte = fh.read(1)
        if not byte:
            return None
        while byte == b"\xff":
            marker = fh.read(1)
            if not marker:
                return None
            if marker != b"\xff":
                break
        else:
            continue
        m = marker[0]
        if m in (0xD8, 0xD9, 0x01) or (0xD0 <= m <= 0xD7):
            continue
        seg_len_raw = fh.read(2)
        if len(seg_len_raw) < 2:
            return None
        seg_len = struct.unpack(">H", seg_len_raw)[0]
        if seg_len < 2:
            return None
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            data = fh.read(5)
            if len(data) < 5:
                return None
            h, w = struct.unpack(">HH", data[1:5])
            return w, h
        fh.seek(seg_len - 2, os.SEEK_CUR)


def _read_webp_size(fh) -> Optional[Tuple[int, int]]:
    header = fh.read(12)
    if len(header) < 12 or header[0:4] != b"RIFF" or header[8:12] != b"WEBP":
        return None
    chunk_hdr = fh.read(8)
    if len(chunk_hdr) < 8:
        return None
    ctype = chunk_hdr[0:4]
    if ctype == b"VP8 ":
        data = fh.read(10)
        if len(data) < 10 or data[3:6] != b"\x9d\x01\x2a":
            return None
        w, h = struct.unpack("<HH", data[6:10])
        return w & 0x3FFF, h & 0x3FFF
    if ctype == b"VP8L":
        data = fh.read(5)
        if len(data) < 5 or data[0] != 0x2F:
            return None
        bits = struct.unpack("<I", data[1:5])[0]
        w = (bits & 0x3FFF) + 1
        h = ((bits >> 14) & 0x3FFF) + 1
        return w, h
    if ctype == b"VP8X":
        data = fh.read(10)
        if len(data) < 10:
            return None
        w = 1 + int.from_bytes(data[4:7], "little")
        h = 1 + int.from_bytes(data[7:10], "little")
        return w, h
    return None


def get_image_info(path: Path, ffprobe_path: Optional[str] = None) -> ImageInfo:
    """Read image dimensions without loading full image data into memory."""
    ext = path.suffix.lower()
    fmt = ext.lstrip(".").upper()
    try:
        with path.open("rb") as fh:
            dims = None
            if ext == ".png":
                dims = _read_png_size(fh)
            elif ext in (".jpg", ".jpeg"):
                dims = _read_jpeg_size(fh)
            elif ext == ".webp":
                dims = _read_webp_size(fh)
            if dims and dims[0] > 0 and dims[1] > 0:
                return ImageInfo(width=dims[0], height=dims[1], format_name=fmt, valid=True)
    except OSError as exc:
        return ImageInfo(width=0, height=0, format_name=fmt, valid=False, error=f"Unreadable: {exc}")

    if ffprobe_path:
        try:
            proc = subprocess.run(
                [
                    ffprobe_path,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height",
                    "-of",
                    "json",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if proc.returncode == 0:
                payload = json.loads(proc.stdout)
                streams = payload.get("streams", [])
                if streams:
                    w = int(streams[0].get("width", 0))
                    h = int(streams[0].get("height", 0))
                    if w > 0 and h > 0:
                        return ImageInfo(width=w, height=h, format_name=fmt, valid=True)
        except Exception:
            pass

    return ImageInfo(
        width=0,
        height=0,
        format_name=fmt,
        valid=False,
        error=f"Invalid or unsupported {fmt} image header",
    )


@dataclass
class HalfBlockGrid:
    """Pre-quantized xterm-256 half-block grid for inline curses rendering."""

    cols: int
    rows: int
    cells: List[List[Tuple[int, int]]]  # [row][col] -> (top_fg_256, bottom_bg_256)


class InlineImageCache:
    """Small LRU-1 cache for inline image previews to keep TUI navigation snappy."""

    def __init__(self) -> None:
        self._key: Optional[Tuple[str, float, int, int, str]] = None
        self._grid: Optional[HalfBlockGrid] = None
        self._error: Optional[str] = None

    def get_halfblock_grid(
        self,
        path: Path,
        max_cols: int,
        max_rows: int,
        aspect_mode: str,
        req_width: int,
        req_height: int,
        ffmpeg_path: Optional[str],
        info: ImageInfo,
    ) -> Tuple[Optional[HalfBlockGrid], Optional[str]]:
        if not info.valid:
            return None, info.error or "Invalid image"
        if not ffmpeg_path:
            return None, "ffmpeg not found for inline preview (press Space for native preview)"
        if max_cols < 4 or max_rows < 2:
            return None, "Preview area too small"

        try:
            mtime = path.stat().st_mtime
        except OSError as exc:
            return None, str(exc)

        # Calculate target character dimensions preserving aspect ratio or custom stretch
        if aspect_mode == "custom" and req_width > 0 and req_height > 0:
            target_cols = min(max_cols, req_width)
            target_rows = min(max_rows, req_height)
            # Scale down proportionally if larger than preview box
            scale = min(max_cols / max(1, req_width), max_rows / max(1, req_height), 1.0)
            target_cols = max(2, int(round(req_width * scale)))
            target_rows = max(1, int(round(req_height * scale)))
        else:
            # Terminal cell is roughly 1:2 (width:height), so 1 col x 1 row = 1 x 2 pixels
            img_ratio = info.width / max(1, info.height)
            # In half-block pixel space: px_w / px_h = img_ratio, where px_h = rows * 2, px_w = cols
            target_cols = max_cols
            target_rows = int(round((target_cols / img_ratio) / 2.0))
            if target_rows > max_rows:
                target_rows = max_rows
                target_cols = int(round((target_rows * 2.0) * img_ratio))
            target_cols = max(2, min(max_cols, target_cols))
            target_rows = max(1, min(max_rows, target_rows))

        px_w = target_cols
        px_h = target_rows * 2

        cache_key = (str(path), mtime, px_w, px_h, aspect_mode)
        if self._key == cache_key:
            return self._grid, self._error

        try:
            proc = subprocess.run(
                [
                    ffmpeg_path,
                    "-v",
                    "error",
                    "-i",
                    str(path),
                    "-vf",
                    f"scale={px_w}:{px_h}:flags=lanczos",
                    "-frames:v",
                    "1",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-",
                ],
                capture_output=True,
                timeout=4,
                check=False,
            )
        except Exception as exc:
            self._key = cache_key
            self._grid = None
            self._error = f"Preview decode failed: {exc}"
            return None, self._error

        expected = px_w * px_h * 3
        if proc.returncode != 0 or len(proc.stdout) < expected:
            err_msg = proc.stderr.decode("utf-8", errors="replace").strip() or "ffmpeg decode error"
            self._key = cache_key
            self._grid = None
            self._error = err_msg.splitlines()[0][:80]
            return None, self._error

        raw = proc.stdout
        cells: List[List[Tuple[int, int]]] = []
        stride = px_w * 3
        for r in range(target_rows):
            row_cells: List[Tuple[int, int]] = []
            top_off = (r * 2) * stride
            bot_off = (r * 2 + 1) * stride
            for c in range(target_cols):
                ti = top_off + c * 3
                bi = bot_off + c * 3
                fg = rgb_to_xterm256(raw[ti], raw[ti + 1], raw[ti + 2])
                bg = rgb_to_xterm256(raw[bi], raw[bi + 1], raw[bi + 2])
                row_cells.append((fg, bg))
            cells.append(row_cells)

        grid = HalfBlockGrid(cols=target_cols, rows=target_rows, cells=cells)
        self._key = cache_key
        self._grid = grid
        self._error = None
        return grid, None


def _wait_for_any_key() -> None:
    """Wait for a single keypress in raw mode, falling back to input()."""
    if not sys.stdin.isatty():
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        os.read(fd, 1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def render_fullscreen_image(
    path: Path,
    caps: TerminalCapabilities,
    info: ImageInfo,
    width_cells: int,
    height_cells: int,
) -> Optional[str]:
    """Render full-screen native image preview (called while curses is suspended)."""
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()

    renderer = caps.best_fullscreen_renderer
    header = (
        f"Ryoku Image Preview: {path.name} "
        f"({info.width}x{info.height} {info.format_name}) | "
        f"Renderer: {renderer or 'none'}\r\n"
        f"Requested cells: {width_cells}x{height_cells}\r\n\r\n"
    )
    sys.stdout.write(header)
    sys.stdout.flush()

    err: Optional[str] = None
    if not info.valid:
        sys.stdout.write(f"Cannot preview image: {info.error or 'Invalid image'}\r\n")
    elif renderer == "kitten" and caps.kitten_path:
        res = subprocess.run(
            [caps.kitten_path, "icat", "--align=left", str(path)],
            check=False,
        )
        if res.returncode != 0:
            err = f"kitten icat exited with code {res.returncode}"
    elif renderer == "chafa" and caps.chafa_path:
        res = subprocess.run(
            [caps.chafa_path, f"--size={width_cells}x{height_cells}", str(path)],
            check=False,
        )
        if res.returncode != 0:
            err = f"chafa exited with code {res.returncode}"
    elif renderer == "viu" and caps.viu_path:
        res = subprocess.run(
            [caps.viu_path, "-w", str(width_cells), "-h", str(height_cells), str(path)],
            check=False,
        )
        if res.returncode != 0:
            err = f"viu exited with code {res.returncode}"
    elif renderer == "img2sixel" and caps.img2sixel_path:
        res = subprocess.run([caps.img2sixel_path, str(path)], check=False)
        if res.returncode != 0:
            err = f"img2sixel exited with code {res.returncode}"
    elif renderer == "ffmpeg-halfblock" and caps.ffmpeg_path:
        px_w = max(16, min(100, width_cells * 2))
        px_h = max(16, min(80, height_cells * 2))
        res = subprocess.run(
            [
                caps.ffmpeg_path,
                "-v",
                "error",
                "-i",
                str(path),
                "-vf",
                f"scale={px_w}:{px_h}:force_original_aspect_ratio=decrease",
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ],
            capture_output=True,
            timeout=4,
            check=False,
        )
        if res.returncode == 0 and res.stdout:
            # Print simple 24-bit half-block fallback
            raw = res.stdout
            # Estimate actual output width/height if force_original_aspect_ratio changed it
            ratio = info.width / max(1, info.height)
            out_w = min(px_w, int(round(px_h * ratio)))
            out_h = len(raw) // (3 * max(1, out_w))
            out_h -= out_h % 2
            for y in range(0, out_h, 2):
                line_parts: List[str] = []
                for x in range(out_w):
                    ti = (y * out_w + x) * 3
                    bi = ((y + 1) * out_w + x) * 3
                    if bi + 2 < len(raw):
                        line_parts.append(
                            f"\x1b[38;2;{raw[ti]};{raw[ti+1]};{raw[ti+2]};"
                            f"48;2;{raw[bi]};{raw[bi+1]};{raw[bi+2]}m▀"
                        )
                sys.stdout.write("".join(line_parts) + "\x1b[0m\r\n")
        else:
            err = "ffmpeg preview failed"
    else:
        sys.stdout.write(
            "No compatible terminal image renderer found (checked: kitten, chafa, viu, img2sixel, ffmpeg).\r\n"
        )

    if err:
        sys.stdout.write(f"\r\nRenderer warning: {err}\r\n")

    sys.stdout.write("\r\nPress any key to return to Ryoku Logo Manager...")
    sys.stdout.flush()
    _wait_for_any_key()
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()
    return err
