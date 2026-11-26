require("modules.monitors")
require("modules.programs")
require("modules.autostart")
require("modules.env")
require("modules.decorations")
require("modules.animations")
require("modules.windowrules")
require("modules.layout")
require("modules.misc")
require("modules.inputs")

local ok, custom_shortcuts = pcall(require, "modules.customShortcut")
local overrides = {}
if ok and type(custom_shortcuts) == "table" then
	overrides = type(custom_shortcuts.overrides) == "table" and custom_shortcuts.overrides or custom_shortcuts
	local orig_bind = hl.bind
	hl.bind = function(key, ...)
		return orig_bind(overrides[key] or key, ...)
	end
end

require("modules.binds")

if ok and type(custom_shortcuts) == "table" and type(custom_shortcuts.custom_binds) == "table" then
	for _, item in ipairs(custom_shortcuts.custom_binds) do
		if type(item.key) == "string" and type(item.command) == "string" and item.key ~= "" and item.command ~= "" then
			hl.bind(item.key, hl.dsp.exec_cmd(item.command))
		end
	end
end

require("modules.workspaces")
