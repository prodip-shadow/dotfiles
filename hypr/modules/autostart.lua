-------------------
---- AUTOSTART ----
-------------------

hl.on("hyprland.start", function()
	hl.exec_cmd("wl-paste --type text --watch cliphist store")
	hl.exec_cmd("wl-paste --type image --watch cliphist store")
	hl.exec_cmd("wl-clip-persist --clipboard regular")
	hl.exec_cmd("hypridle")
	hl.exec_cmd("waybar")
	hl.exec_cmd("sh -c 'command -v ghostty >/dev/null && ghostty --gtk-single-instance=true --initial-window=false'")
	hl.exec_cmd("~/.config/waybar/scripts/wifi-menu.py --daemon")
	hl.exec_cmd("~/.config/waybar/scripts/bluetooth-menu.py --daemon")
	hl.exec_cmd("swaync")
	hl.exec_cmd("hyprpaper")

	hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-theme 'miku-cursor-linux'")
	hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-size 24")

	hl.exec_cmd("hyprctl setcursor miku-cursor-linux 24")
	hl.exec_cmd("systemctl --user start hyprpolkitagent")
end)
