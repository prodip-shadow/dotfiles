"""Automatic logo discovery for ASCII and image logos."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

ASCII_EXTENSIONS = frozenset({".txt", ".ans"})
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})

_NATURAL_RE = re.compile(r"(\d+)")


def natural_sort_key(name: str) -> list:
    """Return a key for natural (human-friendly) sorting of filenames."""
    parts = _NATURAL_RE.split(name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def format_size(size_bytes: int) -> str:
    """Format byte count into a concise human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


@dataclass(frozen=True)
class LogoItem:
    """Represents a discovered logo file."""

    name: str
    stem: str
    extension: str
    category: str  # "ascii" or "images"
    path: Path
    size_bytes: int
    size_human: str
    readable: bool
    error: Optional[str] = None

    @property
    def display_path(self) -> str:
        """Return ~/... form if inside home directory, else absolute path."""
        home = Path.home()
        try:
            rel = self.path.relative_to(home)
            return f"~/{rel.as_posix()}"
        except ValueError:
            return str(self.path)


@dataclass
class DiscoveryResult:
    """Result of scanning a logo category directory."""

    category: str
    directory: Path
    exists: bool
    items: List[LogoItem]
    error: Optional[str] = None


def is_safe_child_path(base_dir: Path, target: Path) -> bool:
    """Validate that target resolves strictly inside base_dir (rejects path traversal)."""
    try:
        resolved_base = base_dir.resolve(strict=False)
        resolved_target = target.resolve(strict=False)
        resolved_target.relative_to(resolved_base)
        return resolved_target != resolved_base
    except (ValueError, OSError):
        return False


def scan_category(base_dir: Path, category: str) -> DiscoveryResult:
    """Scan a logo directory ('ascii' or 'images') without loading file contents."""
    allowed_exts = ASCII_EXTENSIONS if category == "ascii" else IMAGE_EXTENSIONS
    if not base_dir.exists():
        return DiscoveryResult(
            category=category,
            directory=base_dir,
            exists=False,
            items=[],
            error=f"Directory does not exist: {base_dir}",
        )
    if not base_dir.is_dir():
        return DiscoveryResult(
            category=category,
            directory=base_dir,
            exists=False,
            items=[],
            error=f"Path is not a directory: {base_dir}",
        )

    items: List[LogoItem] = []
    try:
        entries = list(os.scandir(base_dir))
    except OSError as exc:
        return DiscoveryResult(
            category=category,
            directory=base_dir,
            exists=True,
            items=[],
            error=f"Cannot read directory: {exc}",
        )

    for entry in entries:
        try:
            if not entry.is_file(follow_symlinks=True):
                continue
        except OSError:
            continue

        p = Path(entry.path)
        ext = p.suffix.lower()
        if ext not in allowed_exts:
            continue
        if not is_safe_child_path(base_dir, p):
            continue

        size_bytes = 0
        readable = os.access(p, os.R_OK)
        err: Optional[str] = None if readable else "Permission denied"
        try:
            st = entry.stat(follow_symlinks=True)
            size_bytes = st.st_size
        except OSError as exc:
            readable = False
            err = str(exc)

        items.append(
            LogoItem(
                name=entry.name,
                stem=p.stem,
                extension=ext,
                category=category,
                path=p,
                size_bytes=size_bytes,
                size_human=format_size(size_bytes),
                readable=readable,
                error=err,
            )
        )

    items.sort(key=lambda item: natural_sort_key(item.name))
    return DiscoveryResult(
        category=category,
        directory=base_dir,
        exists=True,
        items=items,
        error=None,
    )


def discover_pokemon() -> DiscoveryResult:
    """Discover available Pokemon colorscripts (always includes 'random')."""
    import shutil
    import subprocess

    items: List[LogoItem] = [
        LogoItem(
            name="random",
            stem="random",
            extension=".pokemon",
            category="pokemon",
            path=Path("random"),
            size_bytes=0,
            size_human="rand",
            readable=True,
        )
    ]
    exe = shutil.which("pokemon-colorscripts")
    if exe:
        try:
            proc = subprocess.run(
                [exe, "-l"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if proc.returncode == 0:
                names = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
                for nm in sorted(set(names), key=natural_sort_key):
                    items.append(
                        LogoItem(
                            name=nm,
                            stem=nm,
                            extension=".pokemon",
                            category="pokemon",
                            path=Path(nm),
                            size_bytes=0,
                            size_human="poke",
                            readable=True,
                        )
                    )
        except Exception:
            pass

    return DiscoveryResult(
        category="pokemon",
        directory=Path("/opt/pokemon-colorscripts"),
        exists=bool(exe),
        items=items,
        error=None,
    )


def discover_all_logos(fastfetch_dir: Path) -> dict[str, DiscoveryResult]:
    """Discover ASCII, image, and Pokemon logos."""
    logos_root = fastfetch_dir / "logos"
    return {
        "ascii": scan_category(logos_root / "ascii", "ascii"),
        "images": scan_category(logos_root / "images", "images"),
        "pokemon": discover_pokemon(),
    }
