#!/usr/bin/env bash
# Waybar Caffeine module: inhibits idle/screen-off & pauses hypridle when active.

set -euo pipefail

PID_FILE="/tmp/waybar-caffeine.pid"

is_active() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        rm -f "$PID_FILE"
    fi
    return 1
}

toggle_caffeine() {
    if is_active; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
        rm -f "$PID_FILE"
        if command -v hypridle >/dev/null 2>&1 && ! pgrep -x hypridle >/dev/null 2>&1; then
            setsid -f hypridle >/dev/null 2>&1
        fi
    else
        pkill -x hypridle 2>/dev/null || true
        if command -v systemd-inhibit >/dev/null 2>&1; then
            systemd-inhibit --what=idle:sleep --who="Waybar Caffeine" --why="Keep screen awake" sleep infinity >/dev/null 2>&1 &
        else
            sleep infinity >/dev/null 2>&1 &
        fi
        echo $! > "$PID_FILE"
    fi
    pkill -RTMIN+8 waybar 2>/dev/null || true
}

if [[ "${1:-}" == "toggle" ]]; then
    toggle_caffeine
    exit 0
fi

if is_active; then
    printf '{"text":"󰅶","tooltip":"Caffeine: ON (Screen will stay awake)","class":"active"}\n'
else
    printf '{"text":"󰛊","tooltip":"Caffeine: OFF (Click to keep screen awake)","class":"inactive"}\n'
fi
