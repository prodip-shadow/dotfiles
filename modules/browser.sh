#!/usr/bin/env bash

# Interactive browser selection using the chosen AUR helper (paru/yay)
BROWSER_CHOICE=$(get_selection "Select Browser to Install" \
    "Brave (Recommended)" \
    "Google Chrome" \
    "Firefox" \
    "Zen Browser" \
    "Chromium" \
    "Vivaldi" \
    "Qutebrowser" \
    "Skip")

case "$BROWSER_CHOICE" in
    "Brave (Recommended)")
        log_info "Installing Brave browser..."
        $INSTALL_CMD brave-bin
        if [[ -f "$BASE/hypr/modules/programs.lua" ]]; then
            sed -i 's/^browser = .*/browser = "brave"/' "$BASE/hypr/modules/programs.lua"
        fi
        log_success "Brave installed and set as default Hyprland browser."
        ;;
    "Google Chrome")
        log_info "Installing Google Chrome..."
        $INSTALL_CMD google-chrome
        if [[ -f "$BASE/hypr/modules/programs.lua" ]]; then
            sed -i 's/^browser = .*/browser = "google-chrome-stable"/' "$BASE/hypr/modules/programs.lua"
        fi
        log_success "Google Chrome installed and set as default Hyprland browser."
        ;;
    "Firefox")
        log_info "Installing Firefox..."
        $INSTALL_CMD firefox
        if [[ -f "$BASE/hypr/modules/programs.lua" ]]; then
            sed -i 's/^browser = .*/browser = "firefox"/' "$BASE/hypr/modules/programs.lua"
        fi
        log_success "Firefox installed and set as default Hyprland browser."
        ;;
    "Zen Browser")
        log_info "Installing Zen Browser..."
        $INSTALL_CMD zen-browser-bin
        if [[ -f "$BASE/hypr/modules/programs.lua" ]]; then
            sed -i 's/^browser = .*/browser = "zen-browser"/' "$BASE/hypr/modules/programs.lua"
        fi
        log_success "Zen Browser installed and set as default Hyprland browser."
        ;;
    "Chromium")
        log_info "Installing Chromium..."
        $INSTALL_CMD chromium
        if [[ -f "$BASE/hypr/modules/programs.lua" ]]; then
            sed -i 's/^browser = .*/browser = "chromium"/' "$BASE/hypr/modules/programs.lua"
        fi
        log_success "Chromium installed and set as default Hyprland browser."
        ;;
    "Vivaldi")
        log_info "Installing Vivaldi..."
        $INSTALL_CMD vivaldi
        if [[ -f "$BASE/hypr/modules/programs.lua" ]]; then
            sed -i 's/^browser = .*/browser = "vivaldi-stable"/' "$BASE/hypr/modules/programs.lua"
        fi
        log_success "Vivaldi installed and set as default Hyprland browser."
        ;;
    "Qutebrowser")
        log_info "Installing Qutebrowser..."
        $INSTALL_CMD qutebrowser
        if [[ -f "$BASE/hypr/modules/programs.lua" ]]; then
            sed -i 's/^browser = .*/browser = "qutebrowser"/' "$BASE/hypr/modules/programs.lua"
        fi
        log_success "Qutebrowser installed and set as default Hyprland browser."
        ;;
    *)
        log_warn "Skipped browser installation."
        ;;
esac
