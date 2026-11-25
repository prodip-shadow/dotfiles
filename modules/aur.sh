#!/usr/bin/env bash

HELPER=$(get_selection "Select AUR Helper" "paru" "yay")

if command -v "$HELPER" &> /dev/null; then
    log_info "$HELPER is already installed."
else
    log_info "Installing $HELPER from AUR..."
    cd "$DOWNLOADS" || exit 1

    if [[ -d "$HELPER" ]]; then
        mv "$HELPER" "${HELPER}.old.$(date +%s)"
    fi

    if git clone "https://aur.archlinux.org/${HELPER}-bin.git" "$HELPER" 2>/dev/null; then
        cd "$HELPER" || exit 1
    else
        rm -rf "$HELPER"
        git clone "https://aur.archlinux.org/${HELPER}.git" "$HELPER"
        cd "$HELPER" || exit 1
    fi
    makepkg -si --noconfirm
    cd "$BASE" || exit 1
fi

if [[ "$HELPER" == "paru" ]]; then
    INSTALL_CMD="paru -S --noconfirm --needed --skipreview"
else
    INSTALL_CMD="yay -S --noconfirm --needed --answerdiff None --answeredit None"
fi

export HELPER INSTALL_CMD
