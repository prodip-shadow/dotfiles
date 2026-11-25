#!/usr/bin/env bash

# Interactive code editor selection using the chosen AUR helper (paru/yay)
EDITOR_CHOICE=$(get_selection "Select Default Code Editor (SUPER + C)" \
    "VS Code" \
    "Cursor" \
    "Zed" \
    "VSCodium" \
    "Sublime Text" \
    "Kate" \
    "Neovim (Terminal)" \
    "Skip")

case "$EDITOR_CHOICE" in
    "VS Code")
        log_info "Installing VS Code..."
        $INSTALL_CMD visual-studio-code-bin
        EDITOR_CMD="code"
        ;;
    "Cursor")
        log_info "Installing Cursor..."
        $INSTALL_CMD cursor-bin
        EDITOR_CMD="cursor"
        ;;
    "Zed")
        log_info "Installing Zed..."
        $INSTALL_CMD zed
        EDITOR_CMD="zeditor"
        ;;
    "VSCodium")
        log_info "Installing VSCodium..."
        $INSTALL_CMD vscodium-bin
        EDITOR_CMD="codium"
        ;;
    "Sublime Text")
        log_info "Installing Sublime Text..."
        $INSTALL_CMD sublime-text-4
        EDITOR_CMD="subl"
        ;;
    "Kate")
        log_info "Installing Kate..."
        $INSTALL_CMD kate
        EDITOR_CMD="kate"
        ;;
    "Neovim (Terminal)")
        log_info "Setting Neovim as default editor..."
        $INSTALL_CMD neovim
        TERM_BIN="${TERMINAL_CHOICE:-ghostty}"
        [[ "$TERM_BIN" == "Skip" ]] && TERM_BIN="ghostty"
        EDITOR_CMD="${TERM_BIN} -e nvim"
        ;;
    *)
        log_warn "Skipped code editor installation."
        return 0 2>/dev/null || exit 0
        ;;
esac

if [[ -f "$BASE/hypr/modules/programs.lua" ]]; then
    sed -i "s|^editor = .*|editor = \"${EDITOR_CMD}\"|" "$BASE/hypr/modules/programs.lua"
fi

log_success "$EDITOR_CHOICE installed and set as default editor (SUPER + C)."
