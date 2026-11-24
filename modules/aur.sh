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

    git clone "https://aur.archlinux.org/${HELPER}.git"
    cd "$HELPER" || exit 1
    makepkg -si --noconfirm
    cd "$BASE" || exit 1
fi

if [[ "$HELPER" == "paru" ]]; then
    INSTALL_CMD="paru -S --noconfirm --needed --skipreview"
else
    INSTALL_CMD="yay -S --noconfirm --needed --answerdiff None --answeredit None"
fi

export INSTALL_CMD
