#!/usr/bin/env bash

# Interactive default terminal selection
TERMINAL_CHOICE=$(get_selection "Select Default Terminal" \
    "kitty" \
    "ghostty" \
    "alacritty" \
    "wezterm" \
    "foot" \
    "tilix" \
    "Skip")

if [[ "$TERMINAL_CHOICE" == "Skip" ]]; then
    log_warn "Skipped terminal installation."
    return 0 2>/dev/null || exit 0
fi

log_info "Installing $TERMINAL_CHOICE..."
$INSTALL_CMD "$TERMINAL_CHOICE"

if [[ -f "$BASE/hypr/modules/programs.lua" ]]; then
    sed -i "s/^terminal = .*/terminal = \"$TERMINAL_CHOICE\"/" "$BASE/hypr/modules/programs.lua"
fi

log_success "$TERMINAL_CHOICE installed and set as default Hyprland terminal."
