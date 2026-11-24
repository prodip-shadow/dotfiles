"""ASCII and ANSI (.txt / .ans) logo parsing and safe curses preview."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

MAX_ASCII_BYTES = 1024 * 1024  # 1 MiB safety limit

_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")
_OTHER_ESC_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b.")


@dataclass(frozen=True)
class StyledSpan:
    """A contiguous run of text with curses-compatible styling."""

    text: str
    fg: int = -1  # -1 = default, 0..255 = xterm-256
    bg: int = -1
    bold: bool = False
    dim: bool = False
    underline: bool = False
    reverse: bool = False


@dataclass
class AsciiPreviewData:
    """Parsed ASCII/ANSI logo ready for scrollable rendering."""

    lines: List[List[StyledSpan]]
    max_width: int
    total_lines: int
    truncated: bool = False
    error: Optional[str] = None


def rgb_to_xterm256(r: int, g: int, b: int) -> int:
    """Map 24-bit RGB to nearest xterm-256 color index (16..255)."""
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + round(((r - 8) / 247) * 23)

    def _to_cube(v: int) -> int:
        if v < 48:
            return 0
        if v < 115:
            return 1
        return min(5, (v - 35) // 40)

    return 16 + 36 * _to_cube(r) + 6 * _to_cube(g) + _to_cube(b)


def _sanitize_plain(text: str) -> str:
    """Strip non-SGR control characters that could corrupt curses."""
    text = _OTHER_ESC_RE.sub("", text)
    return "".join(ch if ch == "\t" or ord(ch) >= 32 else "" for ch in text).replace("\t", "    ")


def parse_ansi_line(line: str, state: dict) -> List[StyledSpan]:
    """Parse a single line with ANSI SGR sequences into StyledSpans, mutating state."""
    spans: List[StyledSpan] = []
    pos = 0
    for match in _SGR_RE.finditer(line):
        if match.start() > pos:
            chunk = _sanitize_plain(line[pos : match.start()])
            if chunk:
                spans.append(
                    StyledSpan(
                        text=chunk,
                        fg=state["fg"],
                        bg=state["bg"],
                        bold=state["bold"],
                        dim=state["dim"],
                        underline=state["underline"],
                        reverse=state["reverse"],
                    )
                )
        codes_str = match.group(1)
        codes = [int(c) if c.isdigit() else 0 for c in codes_str.split(";")] if codes_str else [0]
        idx = 0
        while idx < len(codes):
            c = codes[idx]
            if c == 0:
                state["fg"] = -1
                state["bg"] = -1
                state["bold"] = False
                state["dim"] = False
                state["underline"] = False
                state["reverse"] = False
            elif c == 1:
                state["bold"] = True
            elif c == 2:
                state["dim"] = True
            elif c == 4:
                state["underline"] = True
            elif c == 7:
                state["reverse"] = True
            elif c == 22:
                state["bold"] = False
                state["dim"] = False
            elif c == 24:
                state["underline"] = False
            elif c == 27:
                state["reverse"] = False
            elif 30 <= c <= 37:
                state["fg"] = c - 30
            elif c == 39:
                state["fg"] = -1
            elif 40 <= c <= 47:
                state["bg"] = c - 40
            elif c == 49:
                state["bg"] = -1
            elif 90 <= c <= 97:
                state["fg"] = (c - 90) + 8
            elif 100 <= c <= 107:
                state["bg"] = (c - 100) + 8
            elif c in (38, 48) and idx + 1 < len(codes):
                is_fg = c == 38
                mode = codes[idx + 1]
                if mode == 5 and idx + 2 < len(codes):
                    color_idx = max(0, min(255, codes[idx + 2]))
                    if is_fg:
                        state["fg"] = color_idx
                    else:
                        state["bg"] = color_idx
                    idx += 2
                elif mode == 2 and idx + 4 < len(codes):
                    r, g, b = codes[idx + 2], codes[idx + 3], codes[idx + 4]
                    color_idx = rgb_to_xterm256(
                        max(0, min(255, r)),
                        max(0, min(255, g)),
                        max(0, min(255, b)),
                    )
                    if is_fg:
                        state["fg"] = color_idx
                    else:
                        state["bg"] = color_idx
                    idx += 4
            idx += 1
        pos = match.end()

    if pos < len(line):
        chunk = _sanitize_plain(line[pos:])
        if chunk:
            spans.append(
                StyledSpan(
                    text=chunk,
                    fg=state["fg"],
                    bg=state["bg"],
                    bold=state["bold"],
                    dim=state["dim"],
                    underline=state["underline"],
                    reverse=state["reverse"],
                )
            )
    return spans


def load_ascii_preview(path: Path) -> AsciiPreviewData:
    """Load and parse an ASCII/ANSI logo file safely."""
    try:
        size = path.stat().st_size
        truncated = size > MAX_ASCII_BYTES
        with path.open("rb") as fh:
            raw_bytes = fh.read(MAX_ASCII_BYTES)
        raw_text = raw_bytes.decode("utf-8", errors="replace")
    except OSError as exc:
        return AsciiPreviewData(lines=[], max_width=0, total_lines=0, error=f"Cannot read file: {exc}")

    raw_lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # Drop trailing empty line if file ended with newline
    if len(raw_lines) > 1 and raw_lines[-1] == "":
        raw_lines.pop()

    state = {
        "fg": -1,
        "bg": -1,
        "bold": False,
        "dim": False,
        "underline": False,
        "reverse": False,
    }

    parsed_lines: List[List[StyledSpan]] = []
    max_width = 0
    for raw_line in raw_lines:
        spans = parse_ansi_line(raw_line, state)
        line_len = sum(len(s.text) for s in spans)
        if line_len > max_width:
            max_width = line_len
        parsed_lines.append(spans)

    return AsciiPreviewData(
        lines=parsed_lines,
        max_width=max_width,
        total_lines=len(parsed_lines),
        truncated=truncated,
        error=None,
    )


def load_pokemon_preview(name: str = "random", no_title: bool = True) -> AsciiPreviewData:
    """Run pokemon-colorscripts and parse its ANSI output for preview."""
    import shutil
    import subprocess

    exe = shutil.which("pokemon-colorscripts")
    if not exe:
        return AsciiPreviewData(
            lines=[],
            max_width=0,
            total_lines=0,
            error="pokemon-colorscripts not found in PATH",
        )

    cmd = [exe]
    if not name or name == "random":
        cmd.append("-r")
    else:
        cmd.extend(["-n", name])
    if no_title:
        cmd.append("--no-title")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3, check=False)
    except Exception as exc:
        return AsciiPreviewData(lines=[], max_width=0, total_lines=0, error=f"Preview failed: {exc}")

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip() or f"Exited with code {proc.returncode}"
        return AsciiPreviewData(lines=[], max_width=0, total_lines=0, error=err.splitlines()[0][:80])

    raw_lines = proc.stdout.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(raw_lines) > 1 and raw_lines[-1] == "":
        raw_lines.pop()

    state = {"fg": -1, "bg": -1, "bold": False, "dim": False, "underline": False, "reverse": False}
    parsed_lines: List[List[StyledSpan]] = []
    max_width = 0
    for raw_line in raw_lines:
        spans = parse_ansi_line(raw_line, state)
        line_len = sum(len(s.text) for s in spans)
        if line_len > max_width:
            max_width = line_len
        parsed_lines.append(spans)

    return AsciiPreviewData(
        lines=parsed_lines,
        max_width=max_width,
        total_lines=len(parsed_lines),
        truncated=False,
        error=None,
    )
