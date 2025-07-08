#!/usr/bin/env python3
"""
Helper script for cclog to handle performance-critical operations
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class SessionSummary:
    """Summary data for a session - used by both list and info views"""

    session_id: str
    file_path: Path
    start_timestamp: datetime
    first_user_message: str
    modification_time: float
    file_size: int

    # Optional fields - only populated when needed
    last_timestamp: Optional[datetime] = None
    line_count: Optional[int] = None
    matched_summaries: Optional[list] = None

    @property
    def duration_seconds(self) -> int:
        """Calculate duration if last_timestamp is available"""
        if self.last_timestamp and self.start_timestamp:
            return int((self.last_timestamp - self.start_timestamp).total_seconds())
        return 0

    @property
    def formatted_time(self) -> str:
        """Format start time for display"""
        return self.start_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def formatted_duration(self) -> str:
        """Format duration for display"""
        return format_duration(self.duration_seconds)

    @property
    def formatted_summary(self) -> str:
        """Format first user message for display"""
        return format_summary(self.first_user_message)

    @property
    def formatted_modified(self) -> str:
        """Format modification time as relative time"""
        return format_relative_time(self.modification_time)


def format_duration(seconds):
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days}d"


def format_relative_time(modification_time: float) -> str:
    """Format modification time as relative time (e.g., '6m ago')"""
    current_time = time.time()
    diff = int(current_time - modification_time)

    if diff < 60:
        return f"{diff}s ago"
    elif diff < 3600:
        return f"{diff // 60}m ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours}h ago"
    elif diff < 604800:  # 7 days
        days = diff // 86400
        return f"{days}d ago"
    elif diff < 2592000:  # 30 days
        weeks = diff // 604800
        return f"{weeks}w ago"
    else:
        months = diff // 2592000
        return f"{months}mo ago"


def parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime"""
    if not timestamp_str:
        return None
    try:
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def extract_user_message(data: dict) -> str:
    """Extract user message from JSON data"""
    if data.get("type") == "user":
        content = data.get("message", {}).get("content")
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Handle array of content objects
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    if text:
                        return text
    return ""


def extract_timestamp(data: dict) -> Optional[datetime]:
    """Extract and parse timestamp from JSON data"""
    timestamp_str = data.get("timestamp")
    if timestamp_str:
        return parse_timestamp(timestamp_str)
    return None


def parse_session_minimal(
    file_path: Path, summary_index: Optional[dict] = None
) -> Optional[SessionSummary]:
    """
    Parse session file efficiently
    - Find first line with timestamp
    - Parse first 20 lines to find user message
    - Count all lines
    - Keep last line to parse for timestamp
    """
    try:
        stat = file_path.stat()
        session_id = file_path.stem

        start_timestamp = None
        first_user_msg = ""
        last_line = None
        line_count = 0
        matched_summaries = []
        assistant_uuids_checked = set()  # Track checked UUIDs to avoid duplicates

        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line_count = line_num
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                # Keep track of last non-empty line
                last_line = stripped_line

                # Try to parse JSON from this line
                try:
                    data = json.loads(stripped_line)

                    # Look for first timestamp
                    if not start_timestamp:
                        ts = extract_timestamp(data)
                        if ts:
                            start_timestamp = ts

                    # Look for first user message (within first 20 lines)
                    if line_num <= 20 and not first_user_msg:
                        msg = extract_user_message(data)
                        if msg:
                            first_user_msg = msg

                    # Check for assistant message UUIDs in summary index
                    if summary_index and data.get("type") == "assistant":
                        msg_uuid = data.get("uuid")
                        if msg_uuid and msg_uuid not in assistant_uuids_checked:
                            assistant_uuids_checked.add(msg_uuid)
                            if msg_uuid in summary_index:
                                matched_summaries.append(summary_index[msg_uuid])

                except json.JSONDecodeError:
                    # Skip lines that aren't valid JSON
                    continue

        if not start_timestamp:
            return None

        # Parse last line for timestamp
        last_timestamp = start_timestamp  # Default to start if can't parse last
        if last_line:
            try:
                data = json.loads(last_line)
                ts = extract_timestamp(data)
                if ts:
                    last_timestamp = ts
            except json.JSONDecodeError:
                pass

        return SessionSummary(
            session_id=session_id,
            file_path=file_path,
            start_timestamp=start_timestamp,
            first_user_message=first_user_msg or "no user message",
            modification_time=stat.st_mtime,
            file_size=stat.st_size,
            last_timestamp=last_timestamp,
            line_count=line_count,
            matched_summaries=matched_summaries if matched_summaries else None,
        )
    except Exception:
        return None


def format_summary(first_user_msg):
    """Format the first user message for display"""
    if not first_user_msg:
        return "no user message"

    # Replace newlines with \n string
    return first_user_msg.replace("\n", "\\n").replace("\r", "\\r")


def build_summary_index(project_dir):
    """Build an index of leafUuid -> summary mappings from all summary files"""
    summary_index = {}

    try:
        for file_path in Path(project_dir).glob("*.jsonl"):
            # Quick check if it might be a summary file (small size)
            try:
                stat = file_path.stat()
                # Skip large files (likely conversation files)
                if stat.st_size > 10000:  # 10KB threshold
                    continue

                # Check if file contains summaries
                with open(file_path, "r") as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if data.get("type") == "summary":
                                leaf_uuid = data.get("leafUuid")
                                summary_text = data.get("summary", "")
                                if leaf_uuid and summary_text:
                                    summary_index[leaf_uuid] = summary_text
                        except json.JSONDecodeError:
                            continue
            except (OSError, IOError):
                continue

    except Exception:
        # If indexing fails, return empty index
        pass

    return summary_index


def get_terminal_width():
    """Get terminal width, with fallback to 80"""
    # Check COLUMNS environment variable first (for testing and some terminals)
    columns_env = os.environ.get("COLUMNS")
    if columns_env:
        try:
            return int(columns_env)  # Use exact value from environment
        except ValueError:
            pass

    try:
        # Try to get terminal size
        columns = os.get_terminal_size().columns
        return columns
    except (OSError, AttributeError):
        # Fallback if not in a terminal
        return 80


def get_session_list(project_dir):
    """Generate list of sessions for fzf - streaming output for fast first results"""
    # Build summary index first
    summary_index = build_summary_index(project_dir)

    # Get all session files with their modification times (fast)
    files_with_mtime = []
    for file_path in Path(project_dir).glob("*.jsonl"):
        try:
            stat = file_path.stat()
            files_with_mtime.append((file_path, stat.st_mtime))
        except OSError:
            continue

    # Sort by modification time (newest first)
    files_with_mtime.sort(key=lambda x: x[1], reverse=True)

    # Print all headers (will be made non-searchable by --header-lines=4)
    print(f"Claude Code Sessions for: {Path.cwd()}")
    print("Enter: Return session ID, Ctrl-v: View log")
    print("Ctrl-p: Return path, Ctrl-r: Resume conversation")
    print("CREATED             MODIFIED DURATION MESSAGES  FIRST_MESSAGE")

    # Get terminal width for proper truncation
    terminal_width = get_terminal_width()

    # Calculate available width for message
    # Since fzf uses --with-nth="1", only the first field (before tab) is displayed
    # So we only need to fit the visible part in the terminal
    # TIMESTAMP(19) + Duration(8) + Messages(8) + Modified(8) + spacing(8)
    fixed_width = 51
    available_for_message = max(
        terminal_width - fixed_width - 2, 20
    )  # -2 for small margin

    # Parse and print each file one by one (streaming output)
    for file_path, _ in files_with_mtime:
        summary = parse_session_minimal(file_path, summary_index)
        if summary:
            # Use matched summary if available, otherwise use first user message
            if summary.matched_summaries:
                # Use first matched summary with a prefix
                display_msg = "📑 " + summary.matched_summaries[0]
            else:
                display_msg = summary.formatted_summary

            # Truncate message to fit terminal width
            formatted_msg = format_summary(display_msg)
            if len(formatted_msg) > available_for_message:
                formatted_msg = formatted_msg[: available_for_message - 3] + "..."

            # Use Unit Separator (0x1F) as delimiter - non-printable ASCII character
            print(
                f"{summary.formatted_time:<19} {summary.formatted_modified:>8} {summary.formatted_duration:>8} {summary.line_count:>8}  {formatted_msg}\x1f{summary.session_id}"
            )


def get_session_info(file_path):
    """Get detailed info about a session for preview"""
    # Build summary index for the project directory
    project_dir = Path(file_path).parent
    summary_index = build_summary_index(project_dir)

    summary = parse_session_minimal(Path(file_path), summary_index)
    if not summary:
        print(f"Error: Could not read file {file_path}")
        return

    print(f"{'Session:':<10} {summary.session_id}")
    print(f"{'Messages:':<10} {summary.line_count}")
    print(f"{'Started:':<10} {summary.formatted_time}")
    if summary.last_timestamp and summary.last_timestamp != summary.start_timestamp:
        print(
            f"{'Finished:':<10} {summary.last_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    if summary.duration_seconds > 0:
        print(f"{'Duration:':<10} {summary.formatted_duration}")

    # Display matched summaries if available
    if summary.matched_summaries:
        print(f"\n{'Topics:':<10}")
        for i, topic in enumerate(summary.matched_summaries[:5]):  # Show max 5 topics
            print(f"  • {topic}")


def format_message_line(data):
    """Format a single message line for display"""
    msg_type = data.get("type", "")
    if msg_type not in ["user", "assistant"]:
        return None

    # Extract timestamp
    timestamp = data.get("timestamp", "")
    time_str = format_timestamp_as_time(timestamp)

    # Extract message content
    content = data.get("message", {}).get("content", "")
    is_tool, message_text = parse_message_content(msg_type, content)

    # Choose color based on message type
    color = get_message_color(msg_type, is_tool)
    reset = "\033[0m"

    # Format type label
    type_label = "User      " if msg_type == "user" else "Assistant "

    # Clean up message
    message_text = message_text.replace("\n", " ")

    return f"{color}{type_label}{time_str}  {message_text}{reset}"


def format_timestamp_as_time(timestamp):
    """Convert ISO timestamp to HH:MM:SS format"""
    if not timestamp:
        return "00:00:00"

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return "00:00:00"


def parse_message_content(msg_type, content):
    """Parse message content and determine if it's a tool message"""
    # Handle string content
    if isinstance(content, str):
        return False, content

    # Handle list content
    if not isinstance(content, list) or not content:
        return False, str(content)

    first_item = content[0]

    # Check for tool messages
    if msg_type == "user" and first_item.get("type") == "tool_result":
        return True, f"Tool: {first_item.get('tool_use_id', 'unknown')}"

    if msg_type == "assistant" and first_item.get("type") == "tool_use":
        return True, f"Tool: {first_item.get('name', 'unknown')}"

    # Handle text content
    if first_item.get("type") == "text":
        return False, first_item.get("text", "")

    return False, str(content)


def get_message_color(msg_type, is_tool):
    """Get ANSI color code for message type"""
    if is_tool:
        return "\033[38;5;244m"  # Medium Gray
    elif msg_type == "user":
        return "\033[36m"  # Cyan
    else:
        return "\033[37m"  # White


def view_session(file_path):
    """View session with formatting (like cclog_view but in Python)"""
    try:
        with open(file_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    formatted_line = format_message_line(data)
                    if formatted_line:
                        print(formatted_line)
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Skip malformed lines
                    continue
    except Exception as e:
        print(f"Error reading file: {e}")


# Cache for path lookups to avoid repeated filesystem checks
_path_cache = {}


def decode_project_path(encoded_name):
    """Decode project directory name back to original path"""
    # Claude encodes:
    # "/" -> "-"
    # "." -> "-"
    # "_" -> "-"

    # Decoding algorithm:
    # 1. Process encoded path from left to right
    # 2. For each "-", first try interpreting it as "/"
    # 3. Check if the path up to that point exists
    # 4. If path exists, continue from there
    # 5. If path doesn't exist or would create "//", the "-" cannot be "/"
    # 6. Collect segments as "unmatched" and look for next "-"
    # 7. When finding next "-", try all combinations of ".", "_", and "-" for unmatched segments
    # 8. Continue from any matched path
    # 9. Number of candidates grows as 3^n where n is number of unmatched "-"

    # Check cache first
    if encoded_name in _path_cache:
        return _path_cache[encoded_name]

    if not encoded_name.startswith("-"):
        # Relative path (shouldn't happen)
        _path_cache[encoded_name] = encoded_name
        return encoded_name

    # Build path progressively
    result = decode_path_progressive(encoded_name[1:])  # Remove leading "-"
    _path_cache[encoded_name] = result
    return result


def decode_path_progressive(encoded):
    """Decode path by progressively building and checking segments"""
    current_path = ""
    unmatched_segments = []
    i = 0

    while i < len(encoded):
        # Find next dash
        next_dash = encoded.find("-", i)

        if next_dash == -1:
            # No more dashes, add last segment
            segment = encoded[i:]
            if unmatched_segments or not segment:
                # Have unmatched segments or empty segment
                if segment:
                    unmatched_segments.append(segment)
                # Try all combinations
                result = try_segment_combinations(current_path, unmatched_segments)
                return (
                    result
                    if result
                    else current_path + "/" + "-".join(unmatched_segments)
                )
            else:
                # Simple case: just append
                return current_path + "/" + segment

        # Get segment up to the dash
        segment = encoded[i:next_dash]

        # If we have unmatched segments, we need to try combinations
        if unmatched_segments:
            # Add this segment and try combinations
            if segment:  # Don't add empty segments
                unmatched_segments.append(segment)

            # Try all combinations up to this point
            result = try_segment_combinations(current_path, unmatched_segments)
            if result:
                # Found a match, reset and continue
                current_path = result
                unmatched_segments = []
                i = next_dash + 1
            else:
                # No match, continue collecting segments
                i = next_dash + 1
        else:
            # No unmatched segments yet
            if segment and os.path.exists(current_path + "/" + segment):
                # This segment matches
                current_path = current_path + "/" + segment
                i = next_dash + 1
            else:
                # This segment doesn't match, start collecting
                if not segment:
                    # Empty segment means we have --, which means the previous dash cannot be /
                    # We need to look back and reinterpret
                    # For now, just add empty segment as a marker
                    unmatched_segments.append("")
                else:
                    unmatched_segments.append(segment)
                i = next_dash + 1

    return current_path


def try_segment_combinations(base_path, segments):
    """Try all combinations of joining segments with -, ., or _"""
    import itertools

    if not segments:
        return None

    # Handle special case where first segment is empty (from --)
    if segments[0] == "":
        # This means we have a leading -, which must be . or -
        remaining_segments = segments[1:] if len(segments) > 1 else []

        # Try . first (for hidden files/dirs), then _, then -
        for prefix in [".", "_", "-"]:
            if remaining_segments:
                # Continue with remaining segments
                prefixed_segments = [
                    prefix + remaining_segments[0]
                ] + remaining_segments[1:]
                result = try_segment_combinations(base_path, prefixed_segments)
                if result:
                    return result
            else:
                # Just the prefix
                test_path = os.path.join(base_path, prefix)
                if os.path.exists(test_path):
                    return test_path
        return None

    if len(segments) == 1:
        # Single segment, just try it
        test_path = os.path.join(base_path, segments[0])
        return test_path if os.path.exists(test_path) else None

    # Multiple segments, try all combinations of -, ., and _
    # n-1 positions between n segments
    for separators in itertools.product(["-", ".", "_"], repeat=len(segments) - 1):
        # Build the combined segment
        combined = segments[0]
        for i, sep in enumerate(separators):
            combined += sep + segments[i + 1]

        test_path = os.path.join(base_path, combined)
        if os.path.exists(test_path):
            return test_path

    return None


def get_project_last_activity(project_dir):
    """Get the most recent modification time from all sessions in a project"""
    latest_time = 0
    session_count = 0

    try:
        for file_path in Path(project_dir).glob("*.jsonl"):
            try:
                stat = file_path.stat()
                if stat.st_mtime > latest_time:
                    latest_time = stat.st_mtime
                session_count += 1
            except OSError:
                continue
    except Exception:
        pass

    return latest_time, session_count


def get_projects_list():
    """Generate list of all projects sorted by recent activity"""
    claude_projects_base = Path.home() / ".claude" / "projects"

    if not claude_projects_base.exists():
        print("No Claude projects found")
        return

    # Collect all projects with their last activity time
    projects = []

    for project_dir in claude_projects_base.iterdir():
        if project_dir.is_dir():
            last_activity, session_count = get_project_last_activity(project_dir)
            if session_count > 0:  # Only include projects with sessions
                project_path = decode_project_path(project_dir.name)
                projects.append(
                    {
                        "encoded_name": project_dir.name,
                        "path": project_path,
                        "last_activity": last_activity,
                        "session_count": session_count,
                    }
                )

    # Sort by last activity (newest first)
    projects.sort(key=lambda x: x["last_activity"], reverse=True)

    # Print headers
    print("Claude Code Projects (sorted by recent activity)")
    print("Enter: cd to project directory, Ctrl-o: Open cclog for project")
    print("LAST_ACTIVE    SESSIONS  PROJECT_PATH")

    # Get terminal width for proper truncation
    terminal_width = get_terminal_width()

    # Calculate available width for path
    # Since fzf uses --with-nth="1", only the first field (before Unit Separator) is displayed
    # LAST_ACTIVE(14) + space(1) + SESSIONS(8) + spacing(2) = 25
    fixed_width = 25
    available_for_path = max(
        terminal_width - fixed_width - 2, 20
    )  # -2 for small margin

    # Print each project
    for project in projects:
        last_active = format_relative_time(project["last_activity"])
        path = project["path"]

        # Truncate path if necessary
        if len(path) > available_for_path:
            # Show the end of the path which usually has the most specific info
            path = "..." + path[-(available_for_path - 3) :]

        # Use Unit Separator as delimiter
        # Send the actual decoded path (not encoded name) after the delimiter
        print(
            f"{last_active:<14} {project['session_count']:>8}  {path}\x1f{project['path']}"
        )


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: cclog_helper.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list" and len(sys.argv) >= 3:
        get_session_list(sys.argv[2])
    elif command == "info" and len(sys.argv) >= 3:
        get_session_info(sys.argv[2])
    elif command == "view" and len(sys.argv) >= 3:
        view_session(sys.argv[2])
    elif command == "projects":
        get_projects_list()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
