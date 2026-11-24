"""JSONC configuration management, validation, atomic writes, and backups."""

from __future__ import annotations

import copy
import datetime
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VALID_MODES = ("image", "ascii", "pokemon")
VALID_IMAGE_PROTOCOLS = ("kitty-direct", "kitty-icat", "kitty", "sixel", "iterm", "chafa")
VALID_ASCII_TYPES = ("file", "file-raw")
VALID_POSITIONS = ("left", "right", "top", "auto")
VALID_HORIZONTAL_ALIGNMENTS = ("left", "center", "right")
VALID_VERTICAL_POSITIONS = ("top", "center", "bottom")
VALID_ASPECT_MODES = ("preserve", "custom", "auto")


@dataclass
class PaddingSettings:
    """Logo padding in terminal character cells."""

    top: int = 0
    right: int = 2
    bottom: int = 0
    left: int = 0


@dataclass
class LogoSettings:
    """In-memory representation of logo-settings.jsonc."""

    mode: str = "image"
    image_source: str = "~/.config/fastfetch/logos/images/custom.png"
    ascii_source: str = "~/.config/fastfetch/logos/ascii/custom.txt"
    pokemon_name: str = "random"
    pokemon_no_title: bool = True
    image_protocol: str = "kitty-direct"
    ascii_type: str = "file"
    width: int = 28
    height: int = 14
    padding: PaddingSettings = field(default_factory=PaddingSettings)
    position: str = "left"
    horizontal_alignment: str = "left"
    vertical_position: str = "top"
    aspect_mode: str = "preserve"  # preserve | custom | auto
    preserve_aspect_ratio: bool = True
    scaling: str = "fit"
    transparent_background: bool = True
    print_remaining: bool = True

    def clone(self) -> "LogoSettings":
        return copy.deepcopy(self)

    def sync_derived_fields(self) -> None:
        """Keep Fastfetch-compatible fields synchronized with UI choices."""
        if self.aspect_mode == "preserve":
            self.preserve_aspect_ratio = True
            self.scaling = "fit"
        elif self.aspect_mode == "custom":
            self.preserve_aspect_ratio = False
            self.scaling = "stretch"
        elif self.aspect_mode == "auto":
            self.preserve_aspect_ratio = True
            self.scaling = "auto"

        if self.horizontal_alignment == "left":
            self.position = "left"
        elif self.horizontal_alignment == "right":
            self.position = "right"
        elif self.horizontal_alignment == "center":
            # Fastfetch only supports left/right/top/auto; 'top' centers/places above modules.
            self.position = "top"


DEFAULT_SETTINGS = LogoSettings()


def strip_jsonc_comments_and_trailing_commas(raw: str) -> str:
    """Strip // and /* */ comments and trailing commas while preserving strings."""
    out_chars: List[str] = []
    i = 0
    n = len(raw)
    in_str = False
    while i < n:
        ch = raw[i]
        if in_str:
            out_chars.append(ch)
            if ch == "\\" and i + 1 < n:
                out_chars.append(raw[i + 1])
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
        elif ch == '"':
            in_str = True
            out_chars.append(ch)
            i += 1
        elif ch == "/" and i + 1 < n and raw[i + 1] == "/":
            i += 2
            while i < n and raw[i] != "\n":
                i += 1
        elif ch == "/" and i + 1 < n and raw[i + 1] == "*":
            i += 2
            while i + 1 < n and not (raw[i] == "*" and raw[i + 1] == "/"):
                i += 1
            i += 2
        else:
            out_chars.append(ch)
            i += 1
    clean = "".join(out_chars)
    return re.sub(r",(\s*[}\]])", r"\1", clean)


def parse_jsonc(raw: str) -> Dict[str, Any]:
    """Parse JSONC text into a dictionary."""
    clean = strip_jsonc_comments_and_trailing_commas(raw)
    data = json.loads(clean)
    if not isinstance(data, dict):
        raise ValueError("JSONC root must be a JSON object")
    return data


def _clamp_int(value: Any, default: int, min_val: int, max_val: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(min_val, min(max_val, value))
    return default


def settings_from_dict(data: Dict[str, Any]) -> LogoSettings:
    """Build LogoSettings from a parsed JSONC dict with safe defaults."""
    mode = str(data.get("mode", DEFAULT_SETTINGS.mode)).lower()
    if mode not in VALID_MODES:
        mode = DEFAULT_SETTINGS.mode

    proto = str(data.get("imageProtocol", DEFAULT_SETTINGS.image_protocol))
    if proto not in VALID_IMAGE_PROTOCOLS:
        proto = DEFAULT_SETTINGS.image_protocol

    ascii_type = str(data.get("asciiType", DEFAULT_SETTINGS.ascii_type))
    if ascii_type not in VALID_ASCII_TYPES:
        ascii_type = DEFAULT_SETTINGS.ascii_type

    pad_raw = data.get("padding", {})
    if not isinstance(pad_raw, dict):
        pad_raw = {}
    padding = PaddingSettings(
        top=_clamp_int(pad_raw.get("top"), DEFAULT_SETTINGS.padding.top, -20, 100),
        right=_clamp_int(pad_raw.get("right"), DEFAULT_SETTINGS.padding.right, 0, 100),
        bottom=_clamp_int(pad_raw.get("bottom"), DEFAULT_SETTINGS.padding.bottom, 0, 100),
        left=_clamp_int(pad_raw.get("left"), DEFAULT_SETTINGS.padding.left, 0, 100),
    )

    position = str(data.get("position", DEFAULT_SETTINGS.position)).lower()
    if position not in VALID_POSITIONS:
        position = DEFAULT_SETTINGS.position

    h_align = str(data.get("horizontalAlignment", "")).lower()
    if h_align not in VALID_HORIZONTAL_ALIGNMENTS:
        if position == "right":
            h_align = "right"
        elif position == "top":
            h_align = "center"
        else:
            h_align = "left"

    v_pos = str(data.get("verticalPosition", "top")).lower()
    if v_pos not in VALID_VERTICAL_POSITIONS:
        v_pos = "top"

    preserve = bool(data.get("preserveAspectRatio", DEFAULT_SETTINGS.preserve_aspect_ratio))
    scaling = str(data.get("scaling", DEFAULT_SETTINGS.scaling)).lower()
    aspect_mode = str(data.get("aspectMode", "")).lower()
    if aspect_mode not in VALID_ASPECT_MODES:
        if not preserve or scaling == "stretch":
            aspect_mode = "custom"
        elif scaling == "auto":
            aspect_mode = "auto"
        else:
            aspect_mode = "preserve"

    return LogoSettings(
        mode=mode,
        image_source=str(data.get("imageSource", DEFAULT_SETTINGS.image_source)),
        ascii_source=str(data.get("asciiSource", DEFAULT_SETTINGS.ascii_source)),
        pokemon_name=str(data.get("pokemonName", DEFAULT_SETTINGS.pokemon_name)),
        pokemon_no_title=bool(data.get("pokemonNoTitle", DEFAULT_SETTINGS.pokemon_no_title)),
        image_protocol=proto,
        ascii_type=ascii_type,
        width=_clamp_int(data.get("width"), DEFAULT_SETTINGS.width, 1, 300),
        height=_clamp_int(data.get("height"), DEFAULT_SETTINGS.height, 1, 200),
        padding=padding,
        position=position,
        horizontal_alignment=h_align,
        vertical_position=v_pos,
        aspect_mode=aspect_mode,
        preserve_aspect_ratio=preserve,
        scaling=scaling if scaling in ("fit", "stretch", "auto") else "fit",
        transparent_background=bool(
            data.get("transparentBackground", DEFAULT_SETTINGS.transparent_background)
        ),
        print_remaining=bool(data.get("printRemaining", DEFAULT_SETTINGS.print_remaining)),
    )


def validate_settings(settings: LogoSettings) -> List[str]:
    """Return a list of validation errors; empty list means valid."""
    errors: List[str] = []
    if settings.mode not in VALID_MODES:
        errors.append(f"Invalid mode: {settings.mode}")
    if not (1 <= settings.width <= 300):
        errors.append(f"Width must be between 1 and 300 (got {settings.width})")
    if not (1 <= settings.height <= 200):
        errors.append(f"Height must be between 1 and 200 (got {settings.height})")
    if not (-20 <= settings.padding.top <= 100):
        errors.append(f"Top padding must be between -20 and 100 (got {settings.padding.top})")
    for side_name, val in (
        ("right", settings.padding.right),
        ("bottom", settings.padding.bottom),
        ("left", settings.padding.left),
    ):
        if not (0 <= val <= 100):
            errors.append(f"{side_name.capitalize()} padding must be between 0 and 100 (got {val})")

    if settings.mode == "pokemon":
        if not settings.pokemon_name or not settings.pokemon_name.strip():
            errors.append("Pokemon name cannot be empty")
    else:
        active_src = settings.ascii_source if settings.mode == "ascii" else settings.image_source
        expanded = Path(os.path.expanduser(active_src))
        if not active_src or not expanded.is_file():
            errors.append(f"Selected logo file does not exist: {active_src}")
        elif not os.access(expanded, os.R_OK):
            errors.append(f"Selected logo file is not readable: {active_src}")

    return errors


def _find_json_key_value_span(raw: str, key: str, start: int = 0, end: Optional[int] = None) -> Optional[Tuple[int, int]]:
    """Find (val_start, val_end) byte/char span for a key inside a JSONC object."""
    if end is None:
        end = len(raw)
    i = start
    depth = 0
    in_str = False
    while i < end:
        ch = raw[i]
        if in_str:
            if ch == "\\" and i + 1 < end:
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
            continue

        if ch == "/" and i + 1 < end and raw[i + 1] == "/":
            i += 2
            while i < end and raw[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < end and raw[i + 1] == "*":
            i += 2
            while i + 1 < end and not (raw[i] == "*" and raw[i + 1] == "/"):
                i += 1
            i += 2
            continue

        if ch in "{[":
            depth += 1
            i += 1
            continue
        if ch in "}]":
            depth -= 1
            i += 1
            continue

        if ch == '"' and depth == 1:
            # Parse key string
            k_start = i + 1
            j = k_start
            while j < end:
                if raw[j] == "\\" and j + 1 < end:
                    j += 2
                    continue
                if raw[j] == '"':
                    break
                j += 1
            found_key = raw[k_start:j]
            k = j + 1
            # Skip whitespace/comments to colon
            while k < end and raw[k] in " \t\r\n":
                k += 1
            if k < end and raw[k] == ":":
                k += 1
                while k < end and raw[k] in " \t\r\n":
                    k += 1
                val_start = k
                val_end = _scan_json_value_end(raw, val_start, end)
                if found_key == key:
                    return (val_start, val_end)
                i = val_end
                continue
            i = j + 1
            continue

        i += 1
    return None


def _scan_json_value_end(raw: str, start: int, end: int) -> int:
    """Return end index of the JSON value starting at `start`."""
    if start >= end:
        return start
    ch = raw[start]
    if ch == '"':
        i = start + 1
        while i < end:
            if raw[i] == "\\" and i + 1 < end:
                i += 2
                continue
            if raw[i] == '"':
                return i + 1
            i += 1
        return end
    if ch in "{[":
        depth = 0
        i = start
        in_str = False
        while i < end:
            c = raw[i]
            if in_str:
                if c == "\\" and i + 1 < end:
                    i += 2
                    continue
                if c == '"':
                    in_str = False
                i += 1
                continue
            if c == '"':
                in_str = True
            elif c == "/" and i + 1 < end and raw[i + 1] == "/":
                i += 2
                while i < end and raw[i] != "\n":
                    i += 1
                continue
            elif c == "/" and i + 1 < end and raw[i + 1] == "*":
                i += 2
                while i + 1 < end and not (raw[i] == "*" and raw[i + 1] == "/"):
                    i += 1
                i += 2
                continue
            elif c in "{[":
                depth += 1
            elif c in "}]":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return end

    i = start
    while i < end and raw[i] not in ",}]\r\n/":
        i += 1
    return len(raw[start:i].rstrip(" \t")) + start


def _replace_or_insert_jsonc_key(raw: str, key: str, json_val_str: str) -> str:
    """Update a top-level key in JSONC text preserving comments, or insert before final '}'."""
    span = _find_json_key_value_span(raw, key)
    if span is not None:
        return raw[: span[0]] + json_val_str + raw[span[1] :]

    last_brace = raw.rfind("}")
    if last_brace == -1:
        return raw
    before = raw[:last_brace].rstrip()
    needs_comma = len(before) > 0 and before[-1] not in "{,"
    comma = "," if needs_comma else ""
    insertion = f'{comma}\n  "{key}": {json_val_str}\n'
    return before + insertion + raw[last_brace:]


def update_jsonc_preserving_comments(raw: str, settings: LogoSettings) -> str:
    """Update logo-settings.jsonc content in-place while preserving comments and unknown keys."""
    settings.sync_derived_fields()
    updates: List[Tuple[str, Any]] = [
        ("mode", settings.mode),
        ("imageSource", settings.image_source),
        ("asciiSource", settings.ascii_source),
        ("pokemonName", settings.pokemon_name),
        ("pokemonNoTitle", settings.pokemon_no_title),
        ("imageProtocol", settings.image_protocol),
        ("asciiType", settings.ascii_type),
        ("width", settings.width),
        ("height", settings.height),
        ("position", settings.position),
        ("horizontalAlignment", settings.horizontal_alignment),
        ("verticalPosition", settings.vertical_position),
        ("aspectMode", settings.aspect_mode),
        ("preserveAspectRatio", settings.preserve_aspect_ratio),
        ("scaling", settings.scaling),
        ("transparentBackground", settings.transparent_background),
        ("printRemaining", settings.print_remaining),
    ]

    text = raw
    for k, v in updates:
        text = _replace_or_insert_jsonc_key(text, k, json.dumps(v))

    # Update padding object fields individually if padding object exists
    pad_span = _find_json_key_value_span(text, "padding")
    if pad_span is not None:
        pad_raw = text[pad_span[0] : pad_span[1]]
        for side, val in (
            ("top", settings.padding.top),
            ("right", settings.padding.right),
            ("bottom", settings.padding.bottom),
            ("left", settings.padding.left),
        ):
            pad_raw = _replace_or_insert_jsonc_key(pad_raw, side, json.dumps(val))
        text = text[: pad_span[0]] + pad_raw + text[pad_span[1] :]
    else:
        pad_obj = {
            "top": settings.padding.top,
            "right": settings.padding.right,
            "bottom": settings.padding.bottom,
            "left": settings.padding.left,
        }
        text = _replace_or_insert_jsonc_key(text, "padding", json.dumps(pad_obj, indent=2))

    # Validate result parses cleanly before returning
    parse_jsonc(text)
    return text


def create_timestamped_backup(file_path: Path, backup_dir: Path) -> Optional[Path]:
    """Create a timestamped backup of file_path without overwriting existing backups."""
    if not file_path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = backup_dir / f"{file_path.name}.bak.{ts}"
    counter = 1
    while candidate.exists():
        candidate = backup_dir / f"{file_path.name}.bak.{ts}.{counter}"
        counter += 1
    shutil.copy2(file_path, candidate)
    return candidate


def atomic_write_text(file_path: Path, content: str) -> None:
    """Atomically write UTF-8 text to file_path."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{file_path.name}.", suffix=".tmp", dir=str(file_path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        if file_path.exists():
            shutil.copymode(file_path, tmp_path)
        os.replace(tmp_path, file_path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def load_settings(cfg_path: Path) -> Tuple[LogoSettings, str, Optional[str]]:
    """Load logo-settings.jsonc. Returns (settings, raw_text, error_message)."""
    if not cfg_path.exists():
        default_json = json.dumps(
            {
                "mode": DEFAULT_SETTINGS.mode,
                "imageSource": DEFAULT_SETTINGS.image_source,
                "asciiSource": DEFAULT_SETTINGS.ascii_source,
                "imageProtocol": DEFAULT_SETTINGS.image_protocol,
                "asciiType": DEFAULT_SETTINGS.ascii_type,
                "width": DEFAULT_SETTINGS.width,
                "height": DEFAULT_SETTINGS.height,
                "padding": {
                    "top": DEFAULT_SETTINGS.padding.top,
                    "right": DEFAULT_SETTINGS.padding.right,
                    "bottom": DEFAULT_SETTINGS.padding.bottom,
                    "left": DEFAULT_SETTINGS.padding.left,
                },
                "position": DEFAULT_SETTINGS.position,
                "horizontalAlignment": DEFAULT_SETTINGS.horizontal_alignment,
                "verticalPosition": DEFAULT_SETTINGS.vertical_position,
                "aspectMode": DEFAULT_SETTINGS.aspect_mode,
                "preserveAspectRatio": DEFAULT_SETTINGS.preserve_aspect_ratio,
                "scaling": DEFAULT_SETTINGS.scaling,
                "transparentBackground": DEFAULT_SETTINGS.transparent_background,
                "printRemaining": DEFAULT_SETTINGS.print_remaining,
            },
            indent=2,
        ) + "\n"
        return DEFAULT_SETTINGS.clone(), default_json, f"Config not found; using defaults ({cfg_path})"

    try:
        raw = cfg_path.read_text(encoding="utf-8")
    except OSError as exc:
        return DEFAULT_SETTINGS.clone(), "{}", f"Failed to read {cfg_path}: {exc}"

    try:
        data = parse_jsonc(raw)
    except Exception as exc:
        return DEFAULT_SETTINGS.clone(), raw, f"Malformed JSONC in {cfg_path.name}: {exc}"

    return settings_from_dict(data), raw, None


def save_settings(cfg_path: Path, backup_dir: Path, settings: LogoSettings, base_raw: str) -> Tuple[Optional[Path], str]:
    """Validate, backup, and atomically write logo-settings.jsonc. Returns (backup_path, new_raw)."""
    errors = validate_settings(settings)
    if errors:
        raise ValueError("; ".join(errors))

    backup_path = create_timestamped_backup(cfg_path, backup_dir)
    # If base_raw was malformed, start from clean JSON instead of silently writing broken JSONC
    try:
        parse_jsonc(base_raw)
        new_raw = update_jsonc_preserving_comments(base_raw, settings)
    except Exception:
        new_raw = update_jsonc_preserving_comments("{\n}\n", settings)

    atomic_write_text(cfg_path, new_raw)
    return backup_path, new_raw
