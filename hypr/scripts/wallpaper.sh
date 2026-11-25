#!/usr/bin/env bash
# Wallpaper picker using Rofi + Hyprpaper + Matugen (themes entire desktop)

set -euo pipefail

WP_DIR="${HOME}/Wallpapers"
HYPRPAPER_CONF="${HOME}/.config/hypr/hyprpaper.conf"
ROFI_THEME="${HOME}/.config/rofi/wallpaper.rasi"

if [[ ! -d "$WP_DIR" ]]; then
    notify-send "Wallpaper" "Directory not found: $WP_DIR" 2>/dev/null || true
    exit 1
fi

mapfile -t WALLPAPERS < <(find "$WP_DIR" -maxdepth 2 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) | sort)

if [[ ${#WALLPAPERS[@]} -eq 0 ]]; then
    notify-send "Wallpaper" "No wallpapers found in $WP_DIR" 2>/dev/null || true
    exit 1
fi

# Detect current wallpaper (live from hyprpaper first, fallback to hyprpaper.conf)
CURRENT_WP=""
if command -v hyprctl >/dev/null 2>&1; then
    CURRENT_WP=$(hyprctl hyprpaper listactive 2>/dev/null | head -n1 | sed -E 's/^[^=]*=\s*//' | xargs || true)
fi
if [[ -z "$CURRENT_WP" && -f "$HYPRPAPER_CONF" ]]; then
    CURRENT_WP=$(grep -E '^\s*(path|wallpaper)\s*=' "$HYPRPAPER_CONF" | head -n1 | sed -E 's/^\s*(path|wallpaper)\s*=\s*([^,]*,\s*)?//' | xargs || true)
fi
CURRENT_WP="${CURRENT_WP/#\~/$HOME}"

ROFI_ARGS=(-dmenu -i -p "󰸉 Wallpaper" -show-icons -theme "$ROFI_THEME")
ACTIVE_IDX=-1
for i in "${!WALLPAPERS[@]}"; do
    if [[ -n "$CURRENT_WP" ]] && [[ "${WALLPAPERS[$i]}" == "$CURRENT_WP" || "$(basename "${WALLPAPERS[$i]}")" == "$(basename "$CURRENT_WP")" ]]; then
        ACTIVE_IDX="$i"
        ROFI_ARGS+=(-selected-row "$i" -a "$i")
        break
    fi
done

ACTIVE_ICON=""
if [[ "$ACTIVE_IDX" -ge 0 ]] && command -v magick >/dev/null 2>&1; then
    ACTIVE_ICON="/tmp/rofi-active-wp.png"
    magick "${WALLPAPERS[$ACTIVE_IDX]}" -resize 260x260^ -gravity center -extent 260x260 \
        -fill "#22c55e44" -draw "rectangle 0,0 260,260" \
        -fill none -stroke "#4ade80" -strokewidth 6 -draw "roundrectangle 3,3 257,257 16,16" \
        -fill "#14532dCC" -stroke "#4ade80" -strokewidth 3 -draw "circle 130,130 130,96" \
        -fill "#ecfdf5" -stroke none -pointsize 42 -gravity center -annotate +0+2 "✓" \
        "$ACTIVE_ICON" 2>/dev/null || ACTIVE_ICON=""
fi

# Show 5x4 grid with thumbnail previews
CHOICE=$(
    for i in "${!WALLPAPERS[@]}"; do
        wp="${WALLPAPERS[$i]}"
        name="$(basename "$wp")"
        if [[ "$i" == "$ACTIVE_IDX" ]]; then
            icon="${ACTIVE_ICON:-$wp}"
            printf '✓ %s\0icon\x1f%s\n' "$name" "$icon"
        else
            printf '%s\0icon\x1f%s\n' "$name" "$wp"
        fi
    done | rofi "${ROFI_ARGS[@]}"
) || exit 0

CHOICE="${CHOICE#✓ }"

[[ -z "${CHOICE:-}" ]] && exit 0

SELECTED=""
for wp in "${WALLPAPERS[@]}"; do
    if [[ "$(basename "$wp")" == "$CHOICE" ]]; then
        SELECTED="$wp"
        break
    fi
done

[[ -z "$SELECTED" ]] && exit 0

# 1. Write hyprpaper.conf first so it applies now and persists across reboots
cat > "$HYPRPAPER_CONF" <<EOF
ipc = on
splash = false

wallpaper {
    monitor =
    path = ${SELECTED}
    fit_mode = fill
}
EOF

# 2. Restart hyprpaper cleanly with the new config
pkill -x hyprpaper 2>/dev/null || true
sleep 0.15
nohup hyprpaper >/dev/null 2>&1 &

# 3. Generate full system theme (Waybar, Rofi, Ghostty, Kitty, Alacritty, Hyprland, SwayNC, GTK4, Wlogout, Hyprlock)
if command -v matugen >/dev/null 2>&1; then
    matugen -c "${HOME}/.config/matugen/config.toml" image "$SELECTED" -m dark --source-color-index 0 >/dev/null 2>&1 || true
fi

notify-send "Wallpaper & Theme Updated" "$(basename "$SELECTED")" 2>/dev/null || true
