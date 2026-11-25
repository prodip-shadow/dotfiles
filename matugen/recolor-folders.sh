#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="$HOME/.config/matugen/folder-colors.env"
[[ -f "$ENV_FILE" ]] || exit 0
# shellcheck source=/dev/null
source "$ENV_FILE"

THEME_DIR="$HOME/.local/share/icons/Matugen-Folders"
PLACES_DIR="$THEME_DIR/scalable/places"
P16="$THEME_DIR/16x16/places"
D16="$THEME_DIR/16x16/devices"
P24="$THEME_DIR/24x24/places"
D24="$THEME_DIR/24x24/devices"
mkdir -p "$PLACES_DIR" "$P16" "$D16" "$P24" "$D24"

cat > "$THEME_DIR/index.theme" << 'EOF'
[Icon Theme]
Name=Matugen-Folders
Comment=Dynamic Matugen colored folders with clean monochrome sidepanel icons
Inherits=Papirus-Dark,Adwaita,hicolor
Directories=16x16/places,16x16/devices,24x24/places,24x24/devices,scalable/places

[16x16/places]
Size=16
Type=Fixed

[16x16/devices]
Size=16
Type=Fixed

[24x24/places]
Size=24
Type=Fixed

[24x24/devices]
Size=24
Type=Fixed

[scalable/places]
Size=64
MinSize=32
MaxSize=256
Type=Scalable
EOF

write_folder() {
    local name="$1"
    local emblem="$2"
    cat > "$PLACES_DIR/${name}.svg" << EOF
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="fg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${PRIMARY}" stop-opacity="1"/>
      <stop offset="100%" stop-color="${DARK}" stop-opacity="0.95"/>
    </linearGradient>
  </defs>
  <path d="M8 15c0-2.8 2.2-5 5-5h12.2c1.6 0 3.1.8 4 2.1L31.5 15H51c2.8 0 5 2.2 5 5v28c0 2.8-2.2 5-5 5H13c-2.8 0-5-2.2-5-5V15z" fill="${DARK}"/>
  <rect x="11" y="17.5" width="42" height="8" rx="2.5" fill="#ffffff" opacity="0.16"/>
  <path d="M6 23c0-2.8 2.2-5 5-5h42c2.8 0 5 2.2 5 5v25c0 3.3-2.7 6-6 6H12c-3.3 0-6-2.7-6-6V23z" fill="url(#fg)"/>
  <path d="M11 18.5h42c2.5 0 4.5 2 4.5 4.5v.5c0-2.5-2-4-4.5-4H11c-2.5 0-4.5 1.5-4.5 4V23c0-2.5 2-4.5 4.5-4.5z" fill="#ffffff" opacity="0.22"/>
  ${emblem}
</svg>
EOF
}

write_mono() {
    local dir16="$1"
    local dir24="$2"
    local name="$3"
    local body="$4"
    local svg="<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 16 16\">${body}</svg>"
    printf '%s\n' "$svg" > "${dir16}/${name}.svg"
    printf '%s\n' "$svg" > "${dir24}/${name}.svg"
    printf '%s\n' "$svg" > "${PLACES_DIR}/${name}-symbolic.svg"
}

# Main grid folder icons (32px+)
write_folder "folder" ""
write_folder "folder-open" ""
write_folder "user-home" '<path d="M32 28l-9.5 8.5h2.8v7.5h4.7v-4.8h4v4.8h4.7v-7.5h2.8z" fill="'"${ICON_FG}"'" opacity="0.88"/>'
write_folder "user-desktop" '<rect x="23" y="28.5" width="18" height="12.5" rx="2" fill="none" stroke="'"${ICON_FG}"'" stroke-width="2" opacity="0.88"/><path d="M27.5 44h9" stroke="'"${ICON_FG}"'" stroke-width="2" stroke-linecap="round" opacity="0.88"/>'
write_folder "folder-documents" '<path d="M25.5 28h9l4 4v12.5h-13zm8.5.8v3.7h3.7" fill="none" stroke="'"${ICON_FG}"'" stroke-width="2" stroke-linejoin="round" opacity="0.88"/>'
write_folder "folder-download" '<path d="M32 28v11m0 0l-4.5-4.5M32 39l4.5-4.5M24.5 43.5h15" fill="none" stroke="'"${ICON_FG}"'" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.88"/>'
write_folder "folder-music" '<path d="M29.5 41.5v-10l8.5-2v10" fill="none" stroke="'"${ICON_FG}"'" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.88"/><circle cx="27.2" cy="41.8" r="2.3" fill="'"${ICON_FG}"'" opacity="0.88"/><circle cx="35.7" cy="39.8" r="2.3" fill="'"${ICON_FG}"'" opacity="0.88"/>'
write_folder "folder-pictures" '<rect x="23.5" y="29" width="17" height="13.5" rx="2.2" fill="none" stroke="'"${ICON_FG}"'" stroke-width="2" opacity="0.88"/><circle cx="28.2" cy="33.5" r="1.6" fill="'"${ICON_FG}"'" opacity="0.88"/><path d="M24.5 40.5l4.5-4.5 3.5 3.5 2.8-2.8 4.2 3.8" fill="none" stroke="'"${ICON_FG}"'" stroke-width="1.8" stroke-linejoin="round" opacity="0.88"/>'
write_folder "folder-videos" '<rect x="23.5" y="29.5" width="17" height="12.5" rx="2.2" fill="none" stroke="'"${ICON_FG}"'" stroke-width="2" opacity="0.88"/><polygon points="30,32.8 35.5,35.8 30,38.8" fill="'"${ICON_FG}"'" opacity="0.88"/>'
write_folder "folder-publicshare" '<circle cx="32" cy="32.5" r="3" fill="none" stroke="'"${ICON_FG}"'" stroke-width="2" opacity="0.88"/><path d="M25.5 43c0-3.2 2.9-5.5 6.5-5.5s6.5 2.3 6.5 5.5" fill="none" stroke="'"${ICON_FG}"'" stroke-width="2" stroke-linecap="round" opacity="0.88"/>'
write_folder "folder-templates" '<rect x="24.5" y="28.5" width="15" height="15" rx="2" fill="none" stroke="'"${ICON_FG}"'" stroke-width="2" stroke-dasharray="3 2" opacity="0.88"/>'

cp -f "$PLACES_DIR/folder.svg" "$PLACES_DIR/inode-directory.svg"
cp -f "$PLACES_DIR/user-desktop.svg" "$PLACES_DIR/folder-desktop.svg"

# Clean monochrome sidepanel icons (Places, Devices, Network) at 16px/24px
C="${SIDEBAR_FG:-#cdd6f4}"
write_mono "$P16" "$P24" "folder" '<path d="M2 3.5C2 2.7 2.7 2 3.5 2H6l1.5 1.5h5c.8 0 1.5.7 1.5 1.5v7.5c0 .8-.7 1.5-1.5 1.5h-9C2.7 14 2 13.3 2 12.5z" fill="none" stroke="'"$C"'" stroke-width="1.4" stroke-linejoin="round"/>'
write_mono "$P16" "$P24" "user-home" '<path d="M8 2L2 7.5h1.8V14h3v-3.5h2.4V14h3V7.5H14z" fill="none" stroke="'"$C"'" stroke-width="1.3" stroke-linejoin="round"/>'
write_mono "$P16" "$P24" "user-desktop" '<rect x="2" y="2.5" width="12" height="8.5" rx="1.2" fill="none" stroke="'"$C"'" stroke-width="1.3"/><path d="M5 13.5h6" stroke="'"$C"'" stroke-width="1.3" stroke-linecap="round"/>'
write_mono "$P16" "$P24" "folder-documents" '<path d="M4 2h5l3 3v9H4zm4.5 0v3.5H12" fill="none" stroke="'"$C"'" stroke-width="1.3" stroke-linejoin="round"/>'
write_mono "$P16" "$P24" "folder-download" '<path d="M8 2v8m0 0L5 7m3 3l3-3M3 13.5h10" fill="none" stroke="'"$C"'" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
write_mono "$P16" "$P24" "folder-music" '<path d="M6 11.5V4l6-1.5V10" fill="none" stroke="'"$C"'" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="4.5" cy="12" r="1.5" fill="'"$C"'"/><circle cx="10.5" cy="10.5" r="1.5" fill="'"$C"'"/>'
write_mono "$P16" "$P24" "folder-pictures" '<rect x="2" y="3" width="12" height="10" rx="1.2" fill="none" stroke="'"$C"'" stroke-width="1.3"/><circle cx="5.5" cy="6.2" r="1" fill="'"$C"'"/><path d="M3 11.5l3-3 2.5 2.5 2-2 2.5 2.5" fill="none" stroke="'"$C"'" stroke-width="1.2" stroke-linejoin="round"/>'
write_mono "$P16" "$P24" "folder-videos" '<rect x="2" y="3.5" width="12" height="9" rx="1.2" fill="none" stroke="'"$C"'" stroke-width="1.3"/><polygon points="6.5,5.8 10.5,8 6.5,10.2" fill="'"$C"'"/>'
write_mono "$P16" "$P24" "folder-publicshare" '<circle cx="8" cy="5.5" r="2" fill="none" stroke="'"$C"'" stroke-width="1.3"/><path d="M3.5 13.5c0-2.2 2-3.8 4.5-3.8s4.5 1.6 4.5 3.8" fill="none" stroke="'"$C"'" stroke-width="1.3" stroke-linecap="round"/>'
write_mono "$P16" "$P24" "folder-templates" '<rect x="2.5" y="2.5" width="11" height="11" rx="1.2" fill="none" stroke="'"$C"'" stroke-width="1.3" stroke-dasharray="2 1.5"/>'
write_mono "$P16" "$P24" "user-trash" '<path d="M3 4.5h10M6 4.5V3h4v1.5M4.5 4.5l.7 9h5.6l.7-9" fill="none" stroke="'"$C"'" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>'
write_mono "$P16" "$P24" "network-workgroup" '<circle cx="8" cy="8" r="5.5" fill="none" stroke="'"$C"'" stroke-width="1.3"/><ellipse cx="8" cy="8" rx="2.5" ry="5.5" fill="none" stroke="'"$C"'" stroke-width="1.2"/><path d="M2.8 8h10.4" stroke="'"$C"'" stroke-width="1.2"/>'
write_mono "$P16" "$P24" "folder-remote" '<path d="M2 3.5C2 2.7 2.7 2 3.5 2H6l1.5 1.5h5c.8 0 1.5.7 1.5 1.5v5.5c0 .8-.7 1.5-1.5 1.5h-9C2.7 12 2 11.3 2 10.5z" fill="none" stroke="'"$C"'" stroke-width="1.3" stroke-linejoin="round"/><path d="M4 14h8M8 12v2" stroke="'"$C"'" stroke-width="1.3" stroke-linecap="round"/>'

# Devices (harddisk, usb, computer)
write_mono "$D16" "$D24" "drive-harddisk" '<rect x="3" y="2.5" width="10" height="11" rx="1.5" fill="none" stroke="'"$C"'" stroke-width="1.3"/><path d="M3 10h10" stroke="'"$C"'" stroke-width="1.2"/><circle cx="10.5" cy="11.8" r=".8" fill="'"$C"'"/>'
write_mono "$D16" "$D24" "drive-removable-media" '<rect x="3" y="2.5" width="10" height="11" rx="1.5" fill="none" stroke="'"$C"'" stroke-width="1.3"/><path d="M6 6.5l2-2 2 2M5.5 9h5" fill="none" stroke="'"$C"'" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>'
write_mono "$D16" "$D24" "computer" '<rect x="2" y="2.5" width="12" height="8.5" rx="1.2" fill="none" stroke="'"$C"'" stroke-width="1.3"/><path d="M5 13.5h6M8 11v2.5" stroke="'"$C"'" stroke-width="1.3" stroke-linecap="round"/>'

for d in "$P16" "$P24"; do
    cp -f "$d/user-trash.svg" "$d/user-trash-full.svg"
    cp -f "$d/user-desktop.svg" "$d/folder-desktop.svg"
    cp -f "$d/network-workgroup.svg" "$d/network-server.svg"
    cp -f "$d/folder.svg" "$d/inode-directory.svg"
done

if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$THEME_DIR" &>/dev/null || true
fi
