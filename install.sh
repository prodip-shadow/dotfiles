#!/usr/bin/env bash

set -euo pipefail

# --- Configuration ---
CFG_DIR="$HOME/.config"
BASE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="$HOME/Github"
BKUP_DIR="$HOME/.dotfiles_backup"

mkdir -p "$CFG_DIR" "$DOWNLOADS" "$BKUP_DIR" "$HOME/.local/bin"

# --- Helpers ---
source "$BASE/modules/func.sh"
print_banner "Arch Linux + Hyprland Dotfiles Installer"

# --- Package Manager Check ---
PKG_MANAGER=$(detect_package_manager)
if [[ "$PKG_MANAGER" != "pacman" ]]; then
    log_error "Unsupported package manager: $PKG_MANAGER! Arch Linux (pacman) is required."
    exit 1
fi

# --- 1. Prerequisites & AUR Helper Selection First ---
print_step "1/8" "Prerequisites & AUR Helper"
source "$BASE/modules/prereq.sh"
print_banner "Arch Linux + Hyprland Dotfiles Installer"
print_step "1/8" "AUR Helper & System Update"
source "$BASE/modules/aur.sh"
source "$BASE/modules/update.sh"

# --- 2. Interactive Terminal & Browser Selection ---
print_step "2/8" "Default Terminal & Browser Selection"
source "$BASE/modules/terminal.sh"
source "$BASE/modules/browser.sh"

# --- 3. Core Hyprland Setup Packages ---
print_step "3/8" "Installing Core Hyprland Packages"
PACKAGES=(
    # Hyprland & Wayland core
    "hyprland"
    "hyprlock"
    "hypridle"
    "hyprpaper"
    "hyprshot"
    "hyprpolkitagent"
    "hyprland-guiutils"
    "xdg-desktop-portal-hyprland"

    # Bar, Shell UI, Launcher & Notifications
    "waybar"
    "quickshell"
    "swaync"
    "wofi"
    "rofi"
    "wlogout"
    "matugen-bin"
    "cava"

    # File Manager & System Tools
    "nautilus"
    "btop"
    "fastfetch"

    # Clipboard, Brightness, Media, Audio & Network
    "wl-clipboard"
    "wl-clip-persist"
    "cliphist"
    "xsel"
    "brightnessctl"
    "playerctl"
    "pipewire"
    "wireplumber"
    "bluez"
    "bluez-utils"
    "blueman"
    "networkmanager"

    # Shell & Prompt
    "zsh"
    "zsh-syntax-highlighting"
    "zsh-autosuggestions"
    "zoxide"
    "atuin"
    "eza"

    # Cursor & Fonts
    "miku-cursor-theme"
    "ttf-firacode-nerd"
    "ttf-jetbrains-mono-nerd"
)

log_info "Installing ${#PACKAGES[@]} core packages via ${HELPER}..."
$INSTALL_CMD "${PACKAGES[@]}"
log_success "Core Hyprland packages installed."

# --- 4. Symlink Hyprland & Desktop Configs ---
print_step "4/8" "Linking Desktop & Hyprland Configs"
LN_DIRS=(
    "alacritty"
    "btop"
    "fastfetch"
    "ghostty"
    "gtk-3.0"
    "hypr"
    "kitty"
    "matugen"
    "quickshell"
    "swaync"
    "waybar"
    "wlogout"
    "wofi"
)

for dir in "${LN_DIRS[@]}"; do
    link_config "$BASE/$dir" "$CFG_DIR/$dir" "$dir"
done

# --- 5. Symlink Home Dotfiles & Local Scripts ---
print_step "5/8" "Linking Shell Dotfiles & Local Scripts"
link_config "$BASE/.zshrc" "$HOME/.zshrc" ".zshrc"
link_config "$BASE/.tmux.conf" "$HOME/.tmux.conf" ".tmux.conf"
link_config "$BASE/.profile" "$HOME/.profile" ".profile"

if [[ -d "$BASE/local-bin" ]]; then
    for bin_file in "$BASE/local-bin/"*; do
        [[ -e "$bin_file" ]] || continue
        name="$(basename "$bin_file")"
        chmod +x "$bin_file"
        link_config "$bin_file" "$HOME/.local/bin/$name" "local-bin-$name"
    done
fi

# --- 6. Fonts ---
print_step "6/8" "Installing Custom Fonts"
source "$BASE/modules/fonts.sh"

# --- 7. Wallpapers & Matugen Theme ---
print_step "7/8" "Wallpapers & Matugen Color Theme"
WP_DIR="$HOME/Wallpapers"
mkdir -p "$WP_DIR"

if [[ -d "$BASE/wallpapers" ]] && compgen -G "$BASE/wallpapers/*" > /dev/null; then
    cp -a "$BASE/wallpapers/." "$WP_DIR/"
    log_success "Wallpapers copied to $WP_DIR."
else
    log_warn "Wallpaper directory is empty or missing."
fi

if [[ -f "$WP_DIR/wall.jpg" ]] && command -v matugen &> /dev/null; then
    matugen image "$WP_DIR/wall.jpg"
    log_success "Matugen theme generated from wall.jpg."
fi

# --- 8. Rofi Themes (used by SUPER + Space launcher) ---
print_step "8/8" "Rofi Launcher Themes"
if [[ ! -d "$CFG_DIR/rofi/launchers/type-6" ]]; then
    log_info "Installing Rofi launcher themes..."
    (
        cd "$DOWNLOADS" || exit 1
        if [[ ! -d "rofi" ]]; then
            git clone --depth=1 https://github.com/adi1090x/rofi.git
        fi
        if [[ -f "rofi/setup.sh" ]]; then
            cd rofi && chmod +x setup.sh && ./setup.sh
        fi
    )
    log_success "Rofi themes configured."
else
    log_info "Rofi launcher themes already present, skipping."
fi

# --- Finish ---
source "$BASE/modules/welcome.sh"
