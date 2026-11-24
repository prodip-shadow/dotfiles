#!/usr/bin/env python3

import json
import subprocess
import sys


def get_windows():
    result = subprocess.run(
        ["hyprctl", "clients", "-j"], capture_output=True, text=True, check=True
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


if __name__ == "__main__":
    try:
        print(json.dumps(get_windows(), indent=2, ensure_ascii=False))
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
