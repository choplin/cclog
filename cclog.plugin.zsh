# cclog.plugin.zsh - Zsh plugin wrapper for cclog
# This file sources the main script for Zsh users via plugin managers

# Get the directory where this plugin is installed
local plugin_dir="${0:h}"

# Source the main script
source "${plugin_dir}/cclog.sh"
