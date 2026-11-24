#!/usr/bin/env python3

import json
import os
import re
import subprocess

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Hyprland Controller")


def get_hyprland_env():
    result = subprocess.run(
        [
            "/usr/bin/env",
            "-u",
            "HYPRLAND_INSTANCE_SIGNATURE",
            "/usr/bin/hyprctl",
            "instances",
            "-j",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )

    instances = json.loads(result.stdout)

    if not instances:
        raise RuntimeError("No active Hyprland instance found")

    instance = instances[0]

    return {
        "HYPRLAND_INSTANCE_SIGNATURE": instance["instance"],
        "WAYLAND_DISPLAY": instance["wl_socket"],
        "XDG_RUNTIME_DIR": os.environ.get(
            "XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"
        ),
    }


def run_hyprctl(*args):
    env = os.environ.copy()
    env.update(get_hyprland_env())

    result = subprocess.run(
        ["/usr/bin/hyprctl", *args], capture_output=True, text=True, timeout=10, env=env
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"hyprctl failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    return result


@mcp.tool()
def list_windows() -> str:
    """List all currently open Hyprland windows with their details."""

    result = run_hyprctl("-j", "clients")
    windows = json.loads(result.stdout)

    data = [
        {
            "address": w["address"],
            "class": w["class"],
            "title": w["title"],
            "workspace": w["workspace"]["name"],
            "focused": w["focusHistoryID"] == 0,
            "pid": w["pid"],
        }
        for w in windows
        if w["mapped"] and not w["hidden"]
    ]

    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
def focus_window(address: str) -> str:
    """Focus a Hyprland window using its window address."""

    if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
        return "Error: Invalid window address"

    lua_command = f'hl.dsp.focus({{ window = "address:{address}" }})'

    result = run_hyprctl("dispatch", lua_command)

    if result.stdout.strip() != "ok":
        return f"Error: {result.stdout.strip()}"

    return f"Successfully focused window: {address}"


@mcp.tool()
def check_environment() -> str:
    """Check whether the MCP server received the required Hyprland environment."""
    import os
    import shutil

    return json.dumps(
        {
            "HYPRLAND_INSTANCE_SIGNATURE": os.environ.get(
                "HYPRLAND_INSTANCE_SIGNATURE"
            ),
            "detected_hyprland": get_hyprland_env(),
            "process_signature": os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"),
            "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY"),
            "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR"),
            "hyprctl_path": shutil.which("hyprctl"),
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
