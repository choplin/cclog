# cclog.plugin.zsh - Zsh plugin wrapper for cclog

# Get the directory where this plugin is installed
local plugin_dir="${0:h}"

# Source the main script
source "${plugin_dir}/cclog.sh"

# The following functions are now available:
# - cclog: Browse Claude Code conversation history
# - cclog projects: Browse all Claude Code projects
