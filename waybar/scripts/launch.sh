#!/usr/bin/env bash

killall -9 waybar
pkill swaync
kill "$(cat /tmp/waybar-wifi-panel.pid 2>/dev/null)" 2>/dev/null || true
kill "$(cat /tmp/waybar-bt-panel.pid 2>/dev/null)" 2>/dev/null || true

waybar &
swaync &
~/.config/waybar/scripts/wifi-menu.py --daemon &
~/.config/waybar/scripts/bluetooth-menu.py --daemon &
