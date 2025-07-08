# cclog.plugin.zsh - Zsh plugin wrapper for cclog
# This file sources the main script for Zsh users via plugin managers

# Get the directory where this plugin is installed
local plugin_dir="${0:h}"

# Source the main script
source "${plugin_dir}/cclog.sh"

# The following functions are now available:
# - cclog: Browse Claude Code sessions for current directory
# - cclog-projects: Browse all Claude Code projects sorted by recent activity
# - ccproject: Shorter alias for cclog-projects
# - cclog_view: View a specific session file
# - cclog_info: Show info about a specific session file
