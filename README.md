# Custom Hyprland Dotfiles

Minimal, modular Arch Linux + Hyprland dotfiles built around the current desktop setup—without extra software bloat.

## What's Included

- **Window Manager**: `hypr/` (Lua-modularized Hyprland config, `hyprlock`, `hypridle`, `hyprpaper`, `hermes` IPC, clipboard script)
- **Status Bar & Shell UI**: `waybar/`, `quickshell/`, `swaync/`, `wlogout/`, `wofi/`
- **Theming**: `matugen/`, `gtk-3.0/`, `wallpapers/`, `fonts/`
- **Terminal & CLI**: `ghostty/`, `kitty/`, `alacritty/`, `fastfetch/`, `btop/`, `.zshrc`, `.tmux.conf`, `.profile`
- **Installer**: `install.sh` + `modules/` (AUR helper choice, core Hyprland dependencies, interactive **Brave** or **Firefox** browser selection, automatic backup to `~/.dotfiles_backup`)

## Installation

```bash
git clone <your-repo-url> ~/dotfiles
cd ~/dotfiles
chmod +x install.sh
./install.sh
```

During installation, you will be prompted to:
1. Select an AUR helper (`paru` or `yay`) and optionally update the system (`pacman -Syu`).
2. Select your default terminal (`ghostty`, `kitty`, or `alacritty`).
3. Choose your browser (`Brave (Recommended)`, `Google Chrome`, `Firefox`, `Zen Browser`, or `Skip`)—installed via your chosen AUR helper and configured in `hypr/modules/programs.lua`.

Existing configs in `~/.config`, `~/`, and `~/.local/bin` are safely backed up to `~/.dotfiles_backup` before symlinking.

## Uninstall

To unlink the dotfiles and restore your previous backups from `~/.dotfiles_backup`:

```bash
chmod +x uninstall.sh
./uninstall.sh
```
