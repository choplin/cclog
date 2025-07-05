#!/usr/bin/env python3
"""
Helper script for cclog to handle performance-critical operations
"""

import json
import os
import sys
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


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
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


def parse_session_minimal(file_path: Path) -> Optional[SessionSummary]:
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
        )
    except Exception:
        return None


def format_summary(first_user_msg):
    """Format the first user message for display"""
    if not first_user_msg:
        return "no user message"

    # Replace newlines with \n string
    return first_user_msg.replace("\n", "\\n").replace("\r", "\\r")


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
    print("TIMESTAMP           Duration Messages  FIRST_MESSAGE")

    # Get terminal width for proper truncation
    terminal_width = get_terminal_width()

    # Calculate available width for message
    # Since fzf uses --with-nth="1", only the first field (before tab) is displayed
    # So we only need to fit the visible part in the terminal
    fixed_width = 41  # TIMESTAMP(19) + Duration(8) + Messages(8) + spacing(6)
    available_for_message = max(
        terminal_width - fixed_width - 2, 20
    )  # -2 for small margin

    # Parse and print each file one by one (streaming output)
    for file_path, _ in files_with_mtime:
        summary = parse_session_minimal(file_path)
        if summary:
            # Truncate message to fit terminal width
            formatted_msg = summary.formatted_summary
            if len(formatted_msg) > available_for_message:
                formatted_msg = formatted_msg[: available_for_message - 3] + "..."

            # Use Unit Separator (0x1F) as delimiter - non-printable ASCII character
            print(
                f"{summary.formatted_time:<19} {summary.formatted_duration:>8} {summary.line_count:>8}  {formatted_msg}\x1f{summary.session_id}"
            )


def get_session_info(file_path):
    """Get detailed info about a session for preview"""
    summary = parse_session_minimal(Path(file_path))
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
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
