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
if ok and type(custom_shortcuts) == "table" then
	local orig_bind = hl.bind
	hl.bind = function(key, ...)
		return orig_bind(custom_shortcuts[key] or key, ...)
	end
end

require("modules.binds")
require("modules.workspaces")
