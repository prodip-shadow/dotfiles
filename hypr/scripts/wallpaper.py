#!/usr/bin/env python3
"""Lightweight Rofi wallpaper picker for hyprpaper (+ matugen if installed)."""

import os
import shutil
import subprocess

WALL_DIR = os.path.expanduser("~/Wallpapers")
HYPRPAPER_CONF = os.path.expanduser("~/.config/hypr/hyprpaper.conf")
ROFI_THEME = os.path.expanduser("~/.config/rofi/clipboard.rasi")
EXTS = (".png", ".jpg", ".jpeg", ".webp")


def main():
    if not os.path.isdir(WALL_DIR):
        return

    files = sorted(
        f for f in os.listdir(WALL_DIR)
        if f.lower().endswith(EXTS) and os.path.isfile(os.path.join(WALL_DIR, f))
    )
    if not files:
        return

    current_name = ""
    try:
        la = subprocess.run(["hyprctl", "hyprpaper", "listactive"], capture_output=True, text=True)
        if la.returncode == 0 and "=" in la.stdout:
            current_name = os.path.basename(os.path.expanduser(la.stdout.splitlines()[0].split("=", 1)[1].strip()))
    except Exception:
        pass
    if not current_name and os.path.isfile(HYPRPAPER_CONF):
        with open(HYPRPAPER_CONF, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s.startswith("path") and "=" in s:
                    current_name = os.path.basename(os.path.expanduser(s.split("=", 1)[1].strip()))
                    break
                if s.startswith("wallpaper") and "," in s:
                    current_name = os.path.basename(os.path.expanduser(s.split(",", 1)[1].strip()))
                    break

    rofi_cmd = [
        "rofi", "-dmenu", "-i", "-show-icons",
        "-p", "󰸉 Wallpaper",
        "-theme", ROFI_THEME,
        "-theme-str", "listview { lines: 8; } element-icon { size: 42px; margin: 0px 10px 0px 0px; }",
    ]
    if current_name in files:
        idx = str(files.index(current_name))
        rofi_cmd += ["-selected-row", idx, "-a", idx]

    rofi_input = "\n".join(
        f"{'✓ ' + f if f == current_name else f}\x00icon\x1f{os.path.join(WALL_DIR, f)}"
        for f in files
    )

    res = subprocess.run(
        rofi_cmd,
        input=rofi_input,
        capture_output=True,
        text=True,
    )
    choice = res.stdout.strip().removeprefix("✓ ")
    if res.returncode != 0 or not choice:
        return

    full_path = os.path.join(WALL_DIR, choice)
    if not os.path.isfile(full_path):
        return

    # Update hyprpaper.conf so it persists across restarts
    conf_content = f"""ipc = on
splash = false

wallpaper {{
    monitor =
    path = {full_path}
    fit_mode = fill
}}
"""
    with open(HYPRPAPER_CONF, "w", encoding="utf-8") as f:
        f.write(conf_content)

    # Apply immediately via hyprpaper IPC (fallback: restart hyprpaper)
    r = subprocess.run(["hyprctl", "hyprpaper", "wallpaper", f",{full_path}"], capture_output=True)
    if r.returncode != 0:
        subprocess.run(["pkill", "-x", "hyprpaper"], check=False)
        subprocess.Popen(["hyprpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    # Update Matugen theme colors if installed
    if shutil.which("matugen"):
        subprocess.run(["matugen", "image", full_path], check=False)


if __name__ == "__main__":
    main()
