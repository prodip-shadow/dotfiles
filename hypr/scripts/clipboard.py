#!/usr/bin/env python3
"""Rofi-based clipboard manager for Hyprland using cliphist with persistent pinning."""

import base64
import hashlib
import html
import json
import os
import subprocess
import sys

PINS_FILE = os.path.expanduser("~/.local/share/cliphist-pins.json")
ROFI_THEME = os.path.expanduser("~/.config/rofi/clipboard.rasi")


def load_pins():
    if not os.path.exists(PINS_FILE):
        return []
    try:
        with open(PINS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_pins(pins):
    os.makedirs(os.path.dirname(PINS_FILE), exist_ok=True)
    with open(PINS_FILE, "w", encoding="utf-8") as f:
        json.dump(pins, f, ensure_ascii=False, indent=2)


def get_cliphist_entries():
    res = subprocess.run(["cliphist", "list"], capture_output=True, text=True)
    if res.returncode != 0:
        return []
    entries = []
    for line in res.stdout.splitlines():
        if "\t" not in line:
            continue
        entry_id, preview = line.split("\t", 1)
        entries.append((entry_id, preview, line))
    return entries


def decode_entry(entry_id):
    res = subprocess.run(["cliphist", "decode", entry_id], capture_output=True)
    return res.stdout if res.returncode == 0 else b""


def copy_bytes(data):
    subprocess.run(["wl-copy"], input=data, check=False)


def make_preview(raw_bytes, fallback_preview):
    if fallback_preview.startswith("[[ binary data"):
        return fallback_preview
    try:
        text = raw_bytes.decode("utf-8", errors="replace").strip()
        single = " ".join(text.split())
        return (single[:110] + "…") if len(single) > 110 else single
    except Exception:
        return fallback_preview


def build_menu():
    pins = load_pins()
    entries = get_cliphist_entries()

    pinned_previews = {p.get("preview") for p in pins}
    items = []
    rows = []

    for idx, pin in enumerate(pins):
        preview = pin.get("preview", "")
        escaped = html.escape(preview)
        rows.append(f"<span foreground='#9dcbfc' weight='bold'>󰐃</span>  {escaped}")
        items.append({"type": "pin", "pin_idx": idx, "pin": pin})

    for entry_id, preview, raw_line in entries:
        if preview in pinned_previews:
            continue
        escaped = html.escape(preview)
        if preview.startswith("[[ binary data"):
            rows.append(f"<span foreground='#7ee787'>󰋩</span>  {escaped}")
        else:
            rows.append(escaped)
        items.append({
            "type": "hist",
            "id": entry_id,
            "preview": preview,
            "raw_line": raw_line,
        })

    return pins, items, rows


def run_rofi(rows, selected_row=0):
    cmd = [
        "rofi",
        "-dmenu",
        "-i",
        "-format", "i",
        "-no-sort",
        "-disable-history",
        "-markup-rows",
        "-selected-row", str(selected_row),
        "-p", "󰅍 Clipboard",
        "-mesg", "<span size='small' foreground='#8b949e'><b>Enter</b> Copy   •   <b>Alt+P</b> Pin/Unpin   •   <b>Alt+D</b> Delete   •   <b>Alt+C</b> Clear Unpinned</span>",
        "-kb-custom-1", "Alt+p",
        "-kb-custom-2", "Alt+d",
        "-kb-custom-3", "Alt+c",
        "-theme", ROFI_THEME,
    ]
    input_text = "\n".join(rows) if rows else "<span foreground='#8b949e'>Clipboard is empty</span>"
    res = subprocess.run(cmd, input=input_text, capture_output=True, text=True)
    out = res.stdout.strip()
    idx = int(out) if out.isdigit() else None
    return res.returncode, idx


def main():
    selected_row = 0
    while True:
        pins, items, rows = build_menu()
        code, idx = run_rofi(rows, selected_row)

        if code == 12:  # Alt+C: Clear unpinned
            subprocess.run(["cliphist", "wipe"], check=False)
            selected_row = 0
            continue

        if code not in (0, 10, 11) or idx is None or idx >= len(items):
            break

        item = items[idx]

        if code == 0:  # Enter: Copy
            if item["type"] == "pin":
                raw = base64.b64decode(item["pin"]["b64"])
                copy_bytes(raw)
            else:
                raw = decode_entry(item["id"])
                copy_bytes(raw)
            break

        elif code == 10:  # Alt+P: Pin / Unpin
            if item["type"] == "pin":
                pins.pop(item["pin_idx"])
                save_pins(pins)
                selected_row = max(0, idx - 1)
            else:
                raw = decode_entry(item["id"])
                if raw:
                    h = hashlib.sha256(raw).hexdigest()
                    if not any(p.get("hash") == h for p in pins):
                        pins.insert(0, {
                            "hash": h,
                            "preview": item["preview"],
                            "b64": base64.b64encode(raw).decode("ascii"),
                        })
                        save_pins(pins)
                selected_row = 0
            continue

        elif code == 11:  # Alt+D: Delete
            if item["type"] == "pin":
                pins.pop(item["pin_idx"])
                save_pins(pins)
            else:
                subprocess.run(
                    ["cliphist", "delete"],
                    input=item["raw_line"] + "\n",
                    text=True,
                    check=False,
                )
            selected_row = max(0, idx - 1)
            continue


if __name__ == "__main__":
    main()
