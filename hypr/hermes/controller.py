#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys


def get_windows():
    result = subprocess.run(
        ["hyprctl", "-j", "clients"], capture_output=True, text=True, check=True
    )

    windows = json.loads(result.stdout)

    return [
        {
            "address": window["address"],
            "class": window["class"],
            "title": window["title"],
            "workspace": window["workspace"]["name"],
            "focused": window["focusHistoryID"] == 0,
            "pid": window["pid"],
        }
        for window in windows
        if window["mapped"] and not window["hidden"]
    ]


def focus_window(address):
    if not address.startswith("0x"):
        raise ValueError("Invalid window address")

    lua_command = f'hl.dsp.focus({{ window = "address:{address}" }})'

    result = subprocess.run(
        ["hyprctl", "dispatch", lua_command], capture_output=True, text=True
    )

    if result.returncode != 0 or result.stdout.strip() != "ok":
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip() or "Failed to focus window"
        )

    return "Window focused successfully"


def main():
    parser = argparse.ArgumentParser(description="Hermes Hyprland Controller")

    parser.add_argument("action", choices=["list", "focus"])

    parser.add_argument("--address", help="Target window address")

    args = parser.parse_args()

    if args.action == "list":
        print(json.dumps(get_windows(), indent=2))

    elif args.action == "focus":
        if not args.address:
            parser.error("--address is required for focus")

        print(focus_window(args.address))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
