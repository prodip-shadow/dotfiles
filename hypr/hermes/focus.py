#!/usr/bin/env python3

import subprocess
import sys


def focus_window(identifier):
    if not identifier:
        raise ValueError("Window address is required")

    lua_command = 'hl.dsp.focus({ window = "address:' + identifier + '" })'

    result = subprocess.run(
        ["hyprctl", "dispatch", lua_command], capture_output=True, text=True
    )

    if result.returncode != 0 or result.stdout.strip() != "ok":
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip() or "Failed to focus window"
        )

    print("Window focused successfully")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: focus.py <window-address>")
        sys.exit(1)

    try:
        focus_window(sys.argv[1])
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
