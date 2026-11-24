#!/usr/bin/env bash

if [[ -d "$BASE/fonts" ]] && compgen -G "$BASE/fonts/*" > /dev/null; then
    mkdir -p "$HOME/.local/share/fonts"
    cp -r "$BASE/fonts/"* "$HOME/.local/share/fonts/"
    fc-cache -f
    log_success "Custom fonts installed."
fi
