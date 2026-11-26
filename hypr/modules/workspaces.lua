------------------------------
--- WINDOWS AND WORKSPACES ---
------------------------------

for i = 1, 4 do
	hl.workspace_rule({
		workspace = i,
		persistent = true,
	})
end
