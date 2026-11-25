#!/usr/bin/env bash

set -euo pipefail

# --- Configuration ---
CFG_DIR="$HOME/.config"
BASE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BKUP_DIR="$HOME/.dotfiles_backup"

# --- Helpers ---
source "$BASE/modules/func.sh"
print_banner "Arch Linux + Hyprland Dotfiles Uninstaller"

log_warn "This will unlink all symlinks created by these dotfiles and restore backups from:"
log_info "$BKUP_DIR"
echo ""

if ! ask_choice "Proceed with uninstalling dotfiles symlinks?"; then
    log_info "Uninstall cancelled."
    exit 0
fi

# --- 1. Unlink Desktop & Hyprland Configs ---
print_step "1/3" "Removing Desktop & Hyprland Symlinks"
LN_DIRS=(
    "alacritty"
    "btop"
    "cava"
    "fastfetch"
    "ghostty"
    "gtk-3.0"
    "gtk-4.0"
    "hypr"
    "kitty"
    "matugen"
    "qt6ct"
    "qutebrowser"
    "rofi"
    "swaync"
    "waybar"
    "wlogout"
)

for dir in "${LN_DIRS[@]}"; do
    unlink_config "$BASE/$dir" "$CFG_DIR/$dir" "$dir"
done

# --- 2. Unlink Home Dotfiles & Local Scripts ---
print_step "2/3" "Removing Shell Dotfiles & Local Script Symlinks"
unlink_config "$BASE/.zshrc" "$HOME/.zshrc" ".zshrc"
unlink_config "$BASE/.p10k.zsh" "$HOME/.p10k.zsh" ".p10k.zsh"
unlink_config "$BASE/.gitconfig" "$HOME/.gitconfig" ".gitconfig"
unlink_config "$BASE/.tmux.conf" "$HOME/.tmux.conf" ".tmux.conf"
unlink_config "$BASE/.profile" "$HOME/.profile" ".profile"

if [[ -d "$BASE/local-bin" ]]; then
    for bin_file in "$BASE/local-bin/"*; do
        [[ -e "$bin_file" ]] || continue
        name="$(basename "$bin_file")"
        unlink_config "$bin_file" "$HOME/.local/bin/$name" "local-bin-$name"
    done
fi

# --- 3. Optional Cleanup ---
print_step "3/3" "Optional Cleanup"
if [[ -d "$HOME/Wallpapers" ]]; then
    if ask_choice "Remove ~/Wallpapers copied by dotfiles?"; then
        rm -rf "$HOME/Wallpapers"
        log_success "Removed ~/Wallpapers"
    else
        log_info "Kept ~/Wallpapers"
    fi
fi

echo ""
echo -e "${GREEN}${BOLD}  ✦ Uninstall complete!${NC}"
echo -e "${BLUE}  ::${NC} Any previous backups in ${BOLD}$BKUP_DIR${NC} were restored where present."
echo -e "${BLUE}  ::${NC} Installed packages were left untouched for system safety."
echo ""
