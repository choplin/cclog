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

# Function to get session stats efficiently
__cclog_get_session_stats() {
    local file="$1"

    # Try to get timestamp from first line
    local start_time=$(head -1 "$file" | jq -r '.timestamp' 2>/dev/null)

    # If first line doesn't have a valid timestamp, search first 10 lines
    if [ "$start_time" = "null" ] || [ -z "$start_time" ]; then
        start_time=$(head -10 "$file" | jq -r 'select(.type == "user" or .type == "assistant") | .timestamp' 2>/dev/null | head -1)
    fi

    # Try to get timestamp from last line
    local end_time=$(tail -1 "$file" | jq -r '.timestamp' 2>/dev/null)

    # If last line doesn't have a valid timestamp, search last 10 lines
    if [ "$end_time" = "null" ] || [ -z "$end_time" ]; then
        end_time=$(tail -10 "$file" | jq -r 'select(.type == "user" or .type == "assistant") | .timestamp' 2>/dev/null | tail -1)
    fi

    # Calculate duration in seconds
    local duration_seconds=0
    if [ -n "$start_time" ] && [ "$start_time" != "null" ] && [ -n "$end_time" ] && [ "$end_time" != "null" ]; then
        local start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${start_time%%.*}" "+%s" 2>/dev/null || date -d "${start_time}" "+%s" 2>/dev/null)
        local end_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${end_time%%.*}" "+%s" 2>/dev/null || date -d "${end_time}" "+%s" 2>/dev/null)

        if [ -n "$start_epoch" ] && [ -n "$end_epoch" ]; then
            duration_seconds=$((end_epoch - start_epoch))
        fi
    fi

    # Try to get first user message from first few lines
    local first_user_msg=$(head -10 "$file" | jq -r 'select(.type == "user" and (.message.content | type) == "string") | .message.content' 2>/dev/null | head -1)

    # Return values
    echo "$start_time|$duration_seconds|$first_user_msg"
}

# Function to generate session list (internal)
__cclog_generate_list() {
    local claude_projects_dir="$1"

    # Temporary file to collect session data
    local temp_file=$(mktemp)

    while IFS= read -r -d '' file; do
        local basename=$(basename "$file")
        local full_session_id="${basename%.jsonl}"

        # Get session stats (timestamp, duration, and first user message)
        local stats=$(__cclog_get_session_stats "$file")
        IFS='|' read -r start_time duration_seconds first_user_msg <<<"$stats"

        if [ -n "$start_time" ] && [ "$start_time" != "null" ]; then
            # Format duration
            local duration=$(__cclog_format_duration $duration_seconds)

            # Count all lines (much faster than parsing JSON)
            local msg_count=$(wc -l <"$file" | tr -d ' ')

            # Get first user message for summary
            local summary="${first_user_msg:-"no user message"}"
            if [ -z "$first_user_msg" ]; then
                # If first line wasn't a user message, we need to find it
                summary=$(jq -r 'select(.type == "user" and (.message.content | type) == "string") | .message.content' "$file" 2>/dev/null | head -1)
                [ -z "$summary" ] && summary="no user message"
            fi

            # Format timestamp as "YYYY-MM-DD HH:MM:SS"
            local formatted_time=$(echo "$start_time" | sed 's/T/ /' | cut -d'.' -f1)

            # Get timestamp for sorting
            local timestamp_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${start_time%%.*}" "+%s" 2>/dev/null || date -d "${start_time}" "+%s" 2>/dev/null)

            # Store session info with epoch timestamp for sorting
            echo "${timestamp_epoch:-0}|$formatted_time|$duration|$msg_count|$summary|$full_session_id" >>"$temp_file"
        fi
    done < <(find "$claude_projects_dir" -maxdepth 1 -name "*.jsonl" -print0)

    # Generate formatted output
    printf "%-19s %-8s %-8s  %s\n" "TIMESTAMP" "Duration" "Messages" "FIRST_MESSAGE"

    # Sort by timestamp (newest first) and display
    while IFS='|' read -r timestamp_epoch formatted_time duration msg_count summary full_id; do
        printf "%-19s %8s %8d  %s\t%s\n" "$formatted_time" "$duration" "$msg_count" "$summary" "$full_id"
    done < <(sort -t'|' -k1,1 -rn "$temp_file")

    rm -f "$temp_file"
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

    # Reuse the stats function to get timestamps and duration
    local stats=$(__cclog_get_session_stats "$file")
    IFS='|' read -r start_time duration_seconds first_user_msg <<<"$stats"

    if [ -n "$start_time" ] && [ "$start_time" != "null" ]; then
        # Format start time
        local formatted_start=$(echo "$start_time" | sed 's/T/ /' | cut -d'.' -f1)
        printf "%-10s %s\n" "Started:" "$formatted_start"

        # Format duration using existing function
        if [ "$duration_seconds" -gt 0 ]; then
            local duration_str=$(__cclog_format_duration $duration_seconds)
            printf "%-10s %s\n" "Duration:" "$duration_str"
        fi
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

    session_id={2}
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
    local result=$(echo "$session_list" | fzf \
        --header-lines="1" \
        --header "Claude Code Sessions for: $(pwd)"$'\nEnter: Return session ID, Ctrl-v: View log\nCtrl-p: Return path, Ctrl-r: Resume conversation' \
        --delimiter=$'\t' \
        --with-nth="1" \
        --preview "$preview_cmd" \
        --preview-window="down:60%:nowrap" \
        --height="100%" \
        --ansi \
        --bind "ctrl-r:execute(claude -r {2})+abort" \
        --expect="ctrl-v,ctrl-p")

    # Process result
    if [ -n "$result" ]; then
        local key=$(echo "$result" | head -1)
        local selected=$(echo "$result" | tail -n +2)

        if [ -n "$selected" ]; then
            local full_id=$(echo "$selected" | awk -F$'\t' '{print $2}')

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
