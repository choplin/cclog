#!/bin/bash
# Browse Claude Code logs with fzf

# Get the full path to this script at the top level
CCLOG_SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
# Resolve to absolute path
if [[ ! "$CCLOG_SCRIPT_PATH" =~ ^/ ]]; then
    CCLOG_SCRIPT_PATH="$(cd "$(dirname "$CCLOG_SCRIPT_PATH")" && pwd)/$(basename "$CCLOG_SCRIPT_PATH")"
fi

# Find Python executable once
CCLOG_PYTHON=""
if command -v python3 >/dev/null 2>&1; then
    CCLOG_PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    # Check if it's Python 3
    if python -c "import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)" 2>/dev/null; then
        CCLOG_PYTHON="python"
    fi
fi

# Get the helper script path
CCLOG_HELPER_SCRIPT="$(dirname "$CCLOG_SCRIPT_PATH")/cclog_helper.py"

# Function to format Claude Code chat logs with colors
cclog_view() {
    if [ $# -eq 0 ]; then
        echo "Error: cclog_view requires a file argument" >&2
        return 1
    fi

    local file="$1"

    # Use Python helper if available
    if [ -f "$CCLOG_HELPER_SCRIPT" ] && [ -n "$CCLOG_PYTHON" ]; then
        "$CCLOG_PYTHON" "$CCLOG_HELPER_SCRIPT" view "$file"
    else
        echo "Error: Python 3 is required for cclog_view" >&2
        return 1
    fi
}

# Function to format duration from seconds
__cclog_format_duration() {
    local duration=$1

    if [ "$duration" -lt 60 ]; then
        echo "${duration}s"
    elif [ "$duration" -lt 3600 ]; then
        echo "$((duration / 60))m"
    elif [ "$duration" -lt 86400 ]; then
        local hours=$((duration / 3600))
        local minutes=$(((duration % 3600) / 60))
        if [ "$minutes" -gt 0 ]; then
            echo "${hours}h ${minutes}m"
        else
            echo "${hours}h"
        fi
    else
        local days=$((duration / 86400))
        local hours=$(((duration % 86400) / 3600))
        if [ "$hours" -gt 0 ]; then
            echo "${days}d ${hours}h"
        else
            echo "${days}d"
        fi
    fi
}

# Function to generate session list (internal)
__cclog_generate_list() {
    local claude_projects_dir="$1"

    # Use Python helper if available
    if [ -f "$CCLOG_HELPER_SCRIPT" ] && [ -n "$CCLOG_PYTHON" ]; then
        "$CCLOG_PYTHON" "$CCLOG_HELPER_SCRIPT" list "$claude_projects_dir"
    else
        echo "Error: Python 3 is required for cclog" >&2
        return 1
    fi
}

# Function to show session info
cclog_info() {
    if [ $# -eq 0 ]; then
        echo "Error: cclog_info requires a file argument" >&2
        return 1
    fi

    local file="$1"

    # Use Python helper if available
    if [ -f "$CCLOG_HELPER_SCRIPT" ] && [ -n "$CCLOG_PYTHON" ]; then
        "$CCLOG_PYTHON" "$CCLOG_HELPER_SCRIPT" info "$file"
    else
        echo "Error: Python 3 is required for cclog_info" >&2
        return 1
    fi
}

# Function to browse logs with fzf
cclog() {
    # Convert "/" to "-" and "." to "-" for project directory name
    local project_dir=$(pwd | sed 's/\//-/g; s/\./-/g')

    local claude_projects_dir="$HOME/.claude/projects/$project_dir"

    # Check if the directory exists
    if [ ! -d "$claude_projects_dir" ]; then
        echo "No Claude logs found for this project: $(pwd)" >&2
        return 1
    fi

    # Create a simpler preview command using the Python helper directly
    local preview_cmd="$CCLOG_PYTHON $CCLOG_HELPER_SCRIPT info '$claude_projects_dir/{-1}.jsonl' && echo && $CCLOG_PYTHON $CCLOG_HELPER_SCRIPT view '$claude_projects_dir/{-1}.jsonl'"

    # Use fzf with formatted list - stream directly from function
    local result=$(__cclog_generate_list "$claude_projects_dir" | fzf \
        --header-lines=4 \
        --delimiter=$'\t' \
        --with-nth="1" \
        --preview "$preview_cmd" \
        --preview-window="down:60%:nowrap" \
        --height="100%" \
        --ansi \
        --bind "ctrl-r:execute(claude -r {-1})+abort" \
        --expect="ctrl-v,ctrl-p")

    # Process result
    if [ -n "$result" ]; then
        local key=$(echo "$result" | head -1)
        local selected=$(echo "$result" | tail -n +2)

        if [ -n "$selected" ]; then
            local full_id=$(echo "$selected" | awk -F$'\t' '{print $NF}')

            case "$key" in
            ctrl-v)
                # View the log
                local selected_file="$claude_projects_dir/${full_id}.jsonl"
                if [ -n "$PAGER" ]; then
                    cclog_view "$selected_file" | $PAGER
                else
                    cclog_view "$selected_file" | less -R
                fi
                ;;
            ctrl-p)
                # Return file path
                echo "$claude_projects_dir/${full_id}.jsonl"
                ;;
            *)
                # Default: return session ID
                echo "$full_id"
                ;;
            esac
        fi
    fi
}

# Execute the function if script is run directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    cclog
fi
