#!/usr/bin/env bash

# --- Color Palette ---
CYAN='\033[1;36m'
MAGENTA='\033[1;35m'
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
GRAY='\033[0;90m'
BOLD='\033[1m'
NC='\033[0m'

# --- Stylish Banner & Step Headers ---
print_banner() {
    local subtitle="${1:-Custom Hyprland Dotfiles Installer}"
    clear
    echo -e "${CYAN}"
    cat << "EOF"
    ___         __    __                     ____        __  _____ __         
   /   |  _____/ /_  / /_  ____  _________  / __ \____  / /_/ __(_) /__  _____
  / /| | / ___/ __ \/ __ \/ __ \/ ___/ __ \/ / / / __ \/ __/ /_/ / / _ \/ ___/
 / ___ |(__  ) / / / /_/ / /_/ / /  / / / / /_/ / /_/ / /_/ __/ / /  __(__  ) 
/_/  |_/____/_/ /_/_.___/\____/_/  /_/ /_/_____/\____/\__/_/ /_/_/\___/____/  
EOF
    echo -e "${NC}"
    echo -e "${MAGENTA}  ✦ ${BOLD}${subtitle}${NC}"
    echo -e "${GRAY}  ─────────────────────────────────────────────────────────────────────────${NC}\n"
}

print_step() {
    local step_num="$1"
    local title="$2"
    echo ""
    echo -e "${BLUE}╭─[${MAGENTA}${step_num}${BLUE}]─[${CYAN}${title}${BLUE}]${NC}"
}

# --- Logging Helpers ---
log_info()    { printf "${BLUE}│ ℹ${NC}  %s\n" "$1"; }
log_success() { printf "${GREEN}│ ✓${NC}  %s\n" "$1"; }
log_warn()    { printf "${YELLOW}│ ⚠${NC}  %s\n" "$1"; }
log_error()   { printf "${RED}│ ✗${NC}  %s\n" "$1" >&2; }

# --- Interactive Prompts (Gum with graceful fallback) ---
ask_choice() {
    local prompt="$1"
    if command -v gum &> /dev/null; then
        gum confirm "$prompt" \
            --default=true \
            --affirmative "Yes" \
            --negative "No" \
            --prompt.foreground="212" \
            --selected.background="212" \
            --selected.foreground="0"
    else
        local reply
        read -r -p "$prompt [Y/n]: " reply
        reply="${reply:-Y}"
        [[ "$reply" =~ ^[Yy]$ ]]
    fi
}

get_selection() {
    local prompt="$1"
    shift
    local choices=("$@")
    gum choose \
        --header "✦ $prompt" \
        --header.foreground="87" \
        --cursor="❯ " \
        --cursor.foreground="212" \
        --selected.foreground="87" \
        "${choices[@]}"
}

detect_package_manager() {
    if command -v pacman &> /dev/null; then
        echo "pacman"
    elif command -v apt &> /dev/null; then
        echo "apt"
    elif command -v dnf &> /dev/null; then
        echo "dnf"
    elif command -v zypper &> /dev/null; then
        echo "zypper"
    elif command -v apk &> /dev/null; then
        echo "apk"
    else
        echo "unknown"
    fi
}

# --- Safe Symlink & Restore Helpers ---
link_config() {
    local src="$1"
    local dest="$2"
    local bkup_name="$3"

    if [[ ! -e "$src" ]]; then
        log_warn "Source missing, skipping: $src"
        return 0
    fi

    if [[ -e "$dest" || -L "$dest" ]]; then
        rm -rf "${BKUP_DIR:?}/$bkup_name"
        mv "$dest" "$BKUP_DIR/$bkup_name"
    fi

    mkdir -p "$(dirname "$dest")"
    ln -snf "$(realpath "$src")" "$dest"
    log_success "Linked $(basename "$dest") → $dest"
}

unlink_config() {
    local src="$1"
    local dest="$2"
    local bkup_name="$3"

    local real_src
    real_src="$(realpath "$src" 2>/dev/null || echo "$src")"

    if [[ -L "$dest" ]]; then
        local target
        target="$(realpath "$dest" 2>/dev/null || readlink "$dest")"
        if [[ "$target" == "$real_src" ]]; then
            rm -f "$dest"
            log_success "Removed symlink: $dest"
            if [[ -e "$BKUP_DIR/$bkup_name" || -L "$BKUP_DIR/$bkup_name" ]]; then
                mv "$BKUP_DIR/$bkup_name" "$dest"
                log_info "Restored backup: $dest"
            fi
        else
            log_warn "Skipped $dest (points elsewhere: $target)"
        fi
    else
        log_warn "Not a symlink, skipped: $dest"
    fi
}
