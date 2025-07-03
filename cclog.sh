#!/bin/bash
# Browse Claude Code logs with fzf

# Get the full path to this script at the top level
CCLOG_SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
# Resolve to absolute path
if [[ ! "$CCLOG_SCRIPT_PATH" =~ ^/ ]]; then
    CCLOG_SCRIPT_PATH="$(cd "$(dirname "$CCLOG_SCRIPT_PATH")" && pwd)/$(basename "$CCLOG_SCRIPT_PATH")"
fi

# Function to format Claude Code chat logs with colors
cclog_view() {
    if [ $# -eq 0 ]; then
        echo "Error: cclog_view requires a file argument" >&2
        return 1
    fi

    local file="$1"

    local color_reset=$'\033[0m'
    local color_user=$'\033[36m'       # Cyan
    local color_assistant=$'\033[37m'  # White
    local color_tool=$'\033[38;5;244m' # Medium Gray

    # JQ query for formatting chat logs with fixed width
    read -r -d '' jq_query <<'EOF'
    select(.type == "user" or .type == "assistant") |

    # Check if this is a tool message
    (if .type == "user" and (.message.content | type) == "array" and .message.content[0].type == "tool_result" then true
     elif .type == "assistant" and (.message.content | type) == "array" and .message.content[0].type == "tool_use" then true
     else false end) as $is_tool |

    # Choose color for entire line
    (if $is_tool then $tool_color
     elif .type == "user" then $user_color
     else $assistant_color end) as $line_color |

    $line_color +

    # Type label with padding (10 chars)
    (if .type == "user" then "User" + (" " * 6) else "Assistant" + " " end) +

    # Timestamp
    (.timestamp | sub("\\.[0-9]+Z$"; "Z") | strptime("%Y-%m-%dT%H:%M:%SZ") | strftime("%H:%M:%S")) + "  " +

    # Message content
    (
      if .type == "user" then
        if .message.content | type == "string" then
          .message.content
        elif .message.content[0]? then
          if .message.content[0].type == "tool_result" then
            "Tool: " + .message.content[0].tool_use_id
          else
            .message.content | tostring
          end
        else
          .message.content | tostring
        end
      elif .type == "assistant" and .message.content[0]? then
        if .message.content[0].type == "text" then
          .message.content[0].text
        elif .message.content[0].type == "tool_use" then
          "Tool: " + .message.content[0].name
        else
          .message.content[0].type
        end
      else
        ""
      end
    ) | gsub("\n"; " ") +

    $reset
EOF

    jq -r --arg user_color "$color_user" \
        --arg assistant_color "$color_assistant" \
        --arg tool_color "$color_tool" \
        --arg reset "$color_reset" \
        "$jq_query" "$file"
}

# Function to generate session list (internal)
__cclog_generate_list() {
    local claude_projects_dir="$1"
    local session_list=$(printf "%-12s\t%-20s\t%-50s\tFULL_ID\n" "SESSION_ID" "TIMESTAMP" "FIRST_MESSAGE")

    while IFS= read -r -d '' file; do
        local basename=$(basename "$file")
        local full_session_id="${basename%.jsonl}"
        local short_session_id="${full_session_id:0:8}"

        # Get first timestamp and first user message
        local first_timestamp=$(jq -r 'select(.type == "user" or .type == "assistant") | .timestamp' "$file" 2>/dev/null | head -1)
        local first_user_msg=$(jq -r 'select(.type == "user" and (.message.content | type) == "string") | .message.content' "$file" 2>/dev/null | head -1)

        if [ -n "$first_timestamp" ]; then
            # Format timestamp
            local formatted_time=$(echo "$first_timestamp" | sed 's/T/ /' | cut -d'.' -f1)

            # Truncate message if needed
            local msg="${first_user_msg:-"no user message"}"
            [ ${#msg} -gt 50 ] && msg="${msg:0:50}..."

            session_list+=$(printf "\n%-12s\t%-20s\t%-50s\t%s" "${short_session_id}" "${formatted_time}" "${msg}" "${full_session_id}")
        else
            session_list+=$(printf "\n%-12s\t%-20s\t%-50s\t%s" "${short_session_id}" "unknown" "no messages" "${full_session_id}")
        fi
    done < <(find "$claude_projects_dir" -maxdepth 1 -name "*.jsonl" -print0)

    echo "$session_list"
}

# Function to show session info
cclog_info() {
    if [ $# -eq 0 ]; then
        echo "Error: cclog_info requires a file argument" >&2
        return 1
    fi

    local file="$1"
    local session_id=$(basename "$file" .jsonl)

    printf "%-10s %s\n" "File:" "${session_id}.jsonl"
    printf "%-10s %s\n" "Messages:" "$(wc -l <"$file" | tr -d " ")"

    # Get start and end timestamps
    local start_time=$(jq -r 'select(.type == "user" or .type == "assistant") | .timestamp' "$file" 2>/dev/null | head -1)
    local end_time=$(jq -r 'select(.type == "user" or .type == "assistant") | .timestamp' "$file" 2>/dev/null | tail -1)

    if [ -n "$start_time" ] && [ -n "$end_time" ]; then
        # Format start time
        local formatted_start=$(echo "$start_time" | sed 's/T/ /' | cut -d'.' -f1)
        printf "%-10s %s\n" "Started:" "$formatted_start"

        # Calculate duration
        local start_epoch=$(date -j -f "%Y-%m-%d %H:%M:%S" "${formatted_start}" "+%s" 2>/dev/null || date -d "${formatted_start}" "+%s" 2>/dev/null)
        local end_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${end_time%%.*}" "+%s" 2>/dev/null || date -d "${end_time}" "+%s" 2>/dev/null)

        if [ -n "$start_epoch" ] && [ -n "$end_epoch" ]; then
            local duration=$((end_epoch - start_epoch))
            local hours=$((duration / 3600))
            local minutes=$(((duration % 3600) / 60))
            local seconds=$((duration % 60))

            local duration_str=""
            [ $hours -gt 0 ] && duration_str="${hours}h "
            [ $minutes -gt 0 ] && duration_str="${duration_str}${minutes}m "
            duration_str="${duration_str}${seconds}s"
            printf "%-10s %s\n" "Duration:" "$duration_str"
        fi
    fi
}

# Function to browse logs with fzf
cclog() {
    # Convert "/" to "-" for project directory name
    local project_dir=$(pwd | sed 's/\//-/g')

    local claude_projects_dir="$HOME/.claude/projects/$project_dir"

    # Check if the directory exists
    if [ ! -d "$claude_projects_dir" ]; then
        echo "No Claude logs found for this project: $(pwd)" >&2
        return 1
    fi

    # Use the script path set at the top level
    local script_path="$CCLOG_SCRIPT_PATH"

    # Generate session list
    local session_list=$(__cclog_generate_list "$claude_projects_dir")

    # Prepare preview command - properly escape script path
    local preview_cmd="bash -c '
    # Source the script
    if [ -f \"$script_path\" ]; then
        source \"$script_path\"
    else
        echo \"Error: Script not found at $script_path\" >&2
        exit 1
    fi

    session_id={4}
    file=\"$claude_projects_dir/\${session_id}.jsonl\"

    # Check if functions are available
    if type cclog_info >/dev/null 2>&1; then
        cclog_info \"\$file\"
        echo
        cclog_view \"\$file\"
    else
        echo \"Error: Functions not loaded\" >&2
    fi
'"

    # Use fzf with formatted list
    local selected=$(echo "$session_list" | fzf \
        --header-lines="1" \
        --header "Claude Code Sessions for: $(pwd)"$'\nEnter: View log, Ctrl-r: Resume conversation' \
        --delimiter=$'\t' \
        --with-nth="1,2,3" \
        --preview "$preview_cmd" \
        --preview-window="down:60%:wrap" \
        --height="100%" \
        --ansi \
        --bind "ctrl-r:execute(claude -r {4})+abort")

    # Process selected session
    if [ -n "$selected" ]; then
        local full_id=$(echo "$selected" | awk -F$'\t' '{print $4}')
        local selected_file="$claude_projects_dir/${full_id}.jsonl"

        # Display the log with viewer
        cclog_view "$selected_file" | ${PAGER:-less -R}
    fi
}

# Execute the function if script is run directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    cclog
fi
