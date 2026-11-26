#!/usr/bin/env bash

set -euo pipefail

# --- Configuration ---
CFG_DIR="$HOME/.config"
BASE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="$HOME/Github"
BKUP_DIR="$HOME/.dotfiles_backup"

mkdir -p "$CFG_DIR" "$DOWNLOADS" "$BKUP_DIR" "$HOME/.local/bin" "$HOME/.local/share" "$HOME/.local/share/icons"

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

# --- 2. Interactive Terminal, Browser & Editor Selection ---
print_step "2/8" "Default Terminal, Browser & Editor Selection"
source "$BASE/modules/terminal.sh"
source "$BASE/modules/browser.sh"
source "$BASE/modules/editor.sh"

# --- 3. Core Hyprland Setup Packages ---
print_step "3/8" "Installing Core Hyprland Packages"
PACKAGES=(
    # Hyprland & Wayland core
    "hyprland"
    "hyprlock"
    "hypridle"
    "hyprpaper"
    "swaybg"
    "hyprshot"
    "imagemagick"
    "hyprpolkitagent"
    "hyprland-guiutils"
    "xdg-desktop-portal-hyprland"

    # Bar, Shell UI, Launcher & Notifications
    "waybar"
    "gtk4"
    "gtk4-layer-shell"
    "python-gobject"
    "swaync"
    "rofi"
    "wlogout"
    "matugen-bin"
    "cava"

    # File Manager & System Tools
    "thunar"
    "tumbler"
    "ffmpegthumbnailer"
    "gvfs"
    "thunar-archive-plugin"
    "file-roller"
    "adw-gtk-theme"
    "papirus-icon-theme"
    "qt6ct"
    "breeze"
    "btop"
    "fastfetch"
    "neovim"
    "tmux"
    "ripgrep"
    "fzf"
    "psmisc"
    "libnotify"
    "github-cli"
    "yt-dlp"
    "vlc"
    "cmatrix"

    # Clipboard, Brightness, Media, Audio & Network
    "wl-clipboard"
    "wl-clip-persist"
    "cliphist"
    "xsel"
    "brightnessctl"
    "playerctl"
    "pavucontrol"
    "pipewire"
    "pipewire-pulse"
    "wireplumber"
    "bluez"
    "bluez-utils"
    "blueman"
    "networkmanager"
    "nm-connection-editor"

    # Shell & Prompt
    "zsh"
    "zsh-syntax-highlighting"
    "zsh-autosuggestions"
    "zsh-theme-powerlevel10k"
    "zoxide"
    "atuin"
    "eza"

    # Cursor & Fonts
    "miku-cursor-theme"
    "ttf-firacode-nerd"
    "ttf-jetbrains-mono-nerd"
    "noto-fonts-emoji"
)

log_info "Installing ${#PACKAGES[@]} core packages via ${HELPER}..."
$INSTALL_CMD "${PACKAGES[@]}"

# Optional / AUR extras (best-effort so missing AUR packages never abort install)
log_info "Installing optional desktop & theme extras..."
for extra_pkg in "pokemon-colorscripts-git" "localsend-bin" "antigravity-ide"; do
    $INSTALL_CMD "$extra_pkg" 2>/dev/null || log_warn "Optional package skipped: $extra_pkg"
done
for old_fm in dolphin nautilus; do
    if pacman -Qi "$old_fm" &>/dev/null; then
        log_info "Removing old file manager ($old_fm)..."
        sudo pacman -Rns --noconfirm "$old_fm" || true
    fi
done
log_success "Core Hyprland packages installed."

# --- 4. Symlink Hyprland & Desktop Configs ---
print_step "4/8" "Linking Desktop & Hyprland Configs"
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
    "rofi"
    "swaync"
    "waybar"
    "wlogout"
)

for dir in "${LN_DIRS[@]}"; do
    [[ -d "$BASE/$dir" ]] || continue
    link_config "$BASE/$dir" "$CFG_DIR/$dir" "$dir"
done

if [[ -f "$CFG_DIR/qt6ct/qt6ct.conf" ]]; then
    sed -i "s|/home/[^/]*/.config/qt6ct|$CFG_DIR/qt6ct|g" "$CFG_DIR/qt6ct/qt6ct.conf"
fi

if command -v xdg-mime &>/dev/null; then
    xdg-mime default thunar.desktop inode/directory || true
fi

if command -v gsettings &>/dev/null; then
    gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' 2>/dev/null || true
    gsettings set org.gnome.desktop.interface gtk-theme 'adw-gtk3-dark' 2>/dev/null || true
    gsettings set org.gnome.desktop.interface icon-theme 'Matugen-Folders' 2>/dev/null || true
fi

# --- 5. Symlink Home Dotfiles & Local Scripts ---
print_step "5/8" "Linking Shell Dotfiles & Local Scripts"
link_config "$BASE/.zshrc" "$HOME/.zshrc" ".zshrc"
link_config "$BASE/.p10k.zsh" "$HOME/.p10k.zsh" ".p10k.zsh"
link_config "$BASE/.gitconfig" "$HOME/.gitconfig" ".gitconfig"
link_config "$BASE/.tmux.conf" "$HOME/.tmux.conf" ".tmux.conf"

if [[ -d "$BASE/local-bin" ]]; then
    for bin_file in "$BASE/local-bin/"*; do
        [[ -e "$bin_file" ]] || continue
        name="$(basename "$bin_file")"
        chmod +x "$bin_file"
        link_config "$bin_file" "$HOME/.local/bin/$name" "local-bin-$name"
    done
fi

if [[ -d "$BASE/scripts" ]]; then
    chmod +x "$BASE/scripts/"* 2>/dev/null || true
    link_config "$BASE/scripts" "$HOME/.scripts" "scripts"
fi

# Enable essential system & user services
sudo systemctl enable --now NetworkManager bluetooth 2>/dev/null || true
systemctl --user enable --now pipewire.socket pipewire-pulse.socket wireplumber.service 2>/dev/null || true

# Set Zsh as default login shell
if command -v zsh &>/dev/null && [[ "${SHELL:-}" != "$(command -v zsh)" ]]; then
    chsh -s "$(command -v zsh)" || log_warn "Could not change default shell to zsh automatically."
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

chmod +x "$BASE/matugen/"*.sh "$BASE/waybar/scripts/"*.py "$BASE/waybar/scripts/"*.sh "$BASE/hypr/scripts/"* 2>/dev/null || true

if [[ -f "$WP_DIR/wall.jpg" ]] && command -v matugen &> /dev/null; then
    sed -i "s|/home/[^/]*/Wallpapers|$HOME/Wallpapers|g" "$CFG_DIR/hypr/hyprpaper.conf" 2>/dev/null || true
    if matugen -c "$CFG_DIR/matugen/config.toml" image "$WP_DIR/wall.jpg" -m dark --source-color-index 0; then
        log_success "Matugen theme generated from wall.jpg."
    else
        log_warn "Matugen theme generation finished with warnings."
    fi
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
