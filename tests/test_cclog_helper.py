#!/usr/bin/env python3
"""Tests for cclog_helper.py functions"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pytest

# Add parent directory to path to import cclog_helper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cclog_helper import (
    parse_session_minimal,
    extract_user_message,
    extract_timestamp,
    format_duration,
    parse_timestamp,
    SessionSummary,
    build_summary_index,
)


class TestParseSessionMinimal:
    """Tests for parse_session_minimal function"""

    def test_original_format(self):
        """Test parsing file with original format (timestamp in first line)"""
        file_path = Path("tests/fixtures/original_format.jsonl")
        summary = parse_session_minimal(file_path)

        assert summary is not None
        assert summary.session_id == "original_format"
        assert summary.start_timestamp.isoformat() == "2025-01-05T10:00:00+00:00"
        assert summary.first_user_message == "What is Python?"
        assert summary.line_count == 4
        assert summary.duration_seconds == 35

    def test_summary_format(self):
        """Test parsing file with summary format (summary in first line)"""
        file_path = Path("tests/fixtures/summary_format.jsonl")
        summary = parse_session_minimal(file_path)

        assert summary is not None
        assert summary.session_id == "summary_format"
        assert summary.start_timestamp.isoformat() == "2025-01-05T11:00:00+00:00"
        assert summary.first_user_message == "Help me understand decorators in Python"
        assert summary.line_count == 5
        assert summary.duration_seconds == 75

    def test_array_content_format(self):
        """Test parsing file with array-based content"""
        file_path = Path("tests/fixtures/array_content_format.jsonl")
        summary = parse_session_minimal(file_path)

        assert summary is not None
        assert summary.session_id == "array_content_format"
        assert summary.start_timestamp.isoformat() == "2025-01-05T12:00:00+00:00"
        assert summary.first_user_message == "Explain async/await in JavaScript"
        assert summary.line_count == 4
        assert summary.duration_seconds == 25

    def test_empty_file(self):
        """Test parsing empty file"""
        file_path = Path("tests/fixtures/empty_file.jsonl")
        summary = parse_session_minimal(file_path)

        assert summary is None

    def test_summary_only(self):
        """Test parsing file with only summary line (no timestamps)"""
        file_path = Path("tests/fixtures/summary_only.jsonl")
        summary = parse_session_minimal(file_path)

        assert summary is None  # Should return None as there's no timestamp

    def test_malformed_json(self):
        """Test parsing file with malformed JSON lines"""
        file_path = Path("tests/fixtures/malformed_json.jsonl")
        summary = parse_session_minimal(file_path)

        # Should skip malformed lines but still parse valid ones
        assert summary is not None
        assert summary.line_count == 3
        assert summary.start_timestamp.isoformat() == "2025-01-05T13:00:10+00:00"

    def test_no_timestamp(self):
        """Test parsing file without timestamps"""
        file_path = Path("tests/fixtures/no_timestamp.jsonl")
        summary = parse_session_minimal(file_path)

        assert summary is None  # Should return None as there's no timestamp

    def test_nonexistent_file(self):
        """Test parsing non-existent file"""
        file_path = Path("tests/fixtures/does_not_exist.jsonl")
        summary = parse_session_minimal(file_path)

        assert summary is None


class TestExtractFunctions:
    """Tests for extract_user_message and extract_timestamp functions"""

    def test_extract_user_message_string(self):
        """Test extracting user message from string content"""
        data = {"type": "user", "message": {"role": "user", "content": "Hello, world!"}}
        message = extract_user_message(data)
        assert message == "Hello, world!"

    def test_extract_user_message_array(self):
        """Test extracting user message from array content"""
        data = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "First message"},
                    {"type": "text", "text": "Second message"},
                ],
            },
        }
        message = extract_user_message(data)
        assert message == "First message"  # Should return first text

    def test_extract_user_message_tool_result(self):
        """Test extracting user message from tool result"""
        data = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "123"}],
            },
        }
        message = extract_user_message(data)
        assert message == ""  # Tool results aren't user messages

    def test_extract_user_message_assistant(self):
        """Test that assistant messages return empty string"""
        data = {
            "type": "assistant",
            "message": {"role": "assistant", "content": "I am assistant"},
        }
        message = extract_user_message(data)
        assert message == ""

    def test_extract_timestamp(self):
        """Test extracting timestamp"""
        data = {"timestamp": "2025-01-05T10:00:00.000Z"}
        ts = extract_timestamp(data)
        assert ts is not None
        assert ts.isoformat() == "2025-01-05T10:00:00+00:00"

    def test_extract_timestamp_missing(self):
        """Test extracting missing timestamp"""
        data = {"type": "user"}
        ts = extract_timestamp(data)
        assert ts is None


class TestHelperFunctions:
    """Tests for helper functions"""

    def test_parse_timestamp(self):
        """Test timestamp parsing"""
        ts = parse_timestamp("2025-01-05T10:00:00.000Z")
        assert ts is not None
        assert ts.isoformat() == "2025-01-05T10:00:00+00:00"

        # Test with +00:00 format
        ts = parse_timestamp("2025-01-05T10:00:00+00:00")
        assert ts is not None
        assert ts.isoformat() == "2025-01-05T10:00:00+00:00"

    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp"""
        assert parse_timestamp("") is None
        assert parse_timestamp("not a timestamp") is None
        assert parse_timestamp(None) is None

    def test_format_duration(self):
        """Test duration formatting"""
        assert format_duration(30) == "30s"
        assert format_duration(90) == "1m"
        assert format_duration(3600) == "1h"
        assert format_duration(3660) == "1h 1m"
        assert format_duration(86400) == "1d"
        assert format_duration(90000) == "1d 1h"
        assert format_duration(0) == "0s"


class TestSessionSummary:
    """Tests for SessionSummary dataclass"""

    def test_session_summary_properties(self):
        """Test SessionSummary computed properties"""
        summary = SessionSummary(
            session_id="test-123",
            file_path=Path("test.jsonl"),
            start_timestamp=datetime.fromisoformat("2025-01-05T10:00:00+00:00"),
            first_user_message="Test message\nwith newline",
            modification_time=1234567890.0,
            file_size=1024,
            last_timestamp=datetime.fromisoformat("2025-01-05T11:30:45+00:00"),
            line_count=100,
        )

        assert summary.duration_seconds == 5445  # 1h 30m 45s
        assert summary.formatted_time == "2025-01-05 10:00:00"
        assert summary.formatted_duration == "1h 30m"
        assert summary.formatted_summary == "Test message\\nwith newline"

    def test_session_summary_with_summaries(self):
        """Test SessionSummary with matched summaries"""
        summary = SessionSummary(
            session_id="test-456",
            file_path=Path("test.jsonl"),
            start_timestamp=datetime.fromisoformat("2025-01-05T10:00:00+00:00"),
            first_user_message="Test",
            modification_time=1234567890.0,
            file_size=1024,
            matched_summaries=["Topic 1", "Topic 2", "Topic 3"],
        )

        assert summary.matched_summaries == ["Topic 1", "Topic 2", "Topic 3"]
        assert summary.matched_summaries is not None
        assert len(summary.matched_summaries) == 3


class TestSummaryIndexing:
    """Tests for summary indexing functionality"""

    def test_build_summary_index_empty_dir(self, tmp_path):
        """Test building summary index from empty directory"""
        index = build_summary_index(str(tmp_path))
        assert index == {}

    def test_build_summary_index_no_summaries(self, tmp_path):
        """Test building summary index with no summary files"""
        # Create a large conversation file (should be skipped)
        conv_file = tmp_path / "conversation.jsonl"
        with open(conv_file, "w") as f:
            for i in range(100):
                f.write('{"type":"user","timestamp":"2025-01-01T00:00:00Z"}\n')

        index = build_summary_index(str(tmp_path))
        assert index == {}

    def test_build_summary_index_with_summaries(self, tmp_path):
        """Test building summary index with summary files"""
        # Create a summary file
        summary_file = tmp_path / "summaries.jsonl"
        with open(summary_file, "w") as f:
            f.write('{"type":"summary","summary":"Topic 1","leafUuid":"uuid-1"}\n')
            f.write('{"type":"summary","summary":"Topic 2","leafUuid":"uuid-2"}\n')
            f.write('{"type":"other","summary":"Not a summary"}\n')  # Should be ignored
            f.write('{"type":"summary","leafUuid":"uuid-3"}\n')  # No summary text

        index = build_summary_index(str(tmp_path))
        assert len(index) == 2
        assert index["uuid-1"] == "Topic 1"
        assert index["uuid-2"] == "Topic 2"
        assert "uuid-3" not in index  # No summary text

    def test_build_summary_index_mixed_files(self, tmp_path):
        """Test building summary index with mixed content files"""
        # Create a mixed file (summary + conversation)
        mixed_file = tmp_path / "mixed.jsonl"
        with open(mixed_file, "w") as f:
            f.write(
                '{"type":"summary","summary":"Mixed Topic","leafUuid":"uuid-mix"}\n'
            )
            f.write('{"type":"user","timestamp":"2025-01-01T00:00:00Z"}\n')
            f.write('{"type":"assistant","timestamp":"2025-01-01T00:00:01Z"}\n')

        index = build_summary_index(str(tmp_path))
        assert index["uuid-mix"] == "Mixed Topic"

    def test_build_summary_index_malformed_json(self, tmp_path):
        """Test building summary index with malformed JSON"""
        bad_file = tmp_path / "bad.jsonl"
        with open(bad_file, "w") as f:
            f.write('{"type":"summary","summary":"Valid","leafUuid":"uuid-valid"}\n')
            f.write("not valid json\n")
            f.write('{"type":"summary"  # incomplete json\n')
            f.write(
                '{"type":"summary","summary":"Also Valid","leafUuid":"uuid-valid2"}\n'
            )

        index = build_summary_index(str(tmp_path))
        assert len(index) == 2
        assert index["uuid-valid"] == "Valid"
        assert index["uuid-valid2"] == "Also Valid"

    def test_parse_session_with_summaries(self, tmp_path):
        """Test parsing session with summary matching"""
        # Create summary file
        summary_file = tmp_path / "summaries.jsonl"
        with open(summary_file, "w") as f:
            f.write(
                '{"type":"summary","summary":"Feature Implementation","leafUuid":"asst-123"}\n'
            )
            f.write(
                '{"type":"summary","summary":"Bug Fix Discussion","leafUuid":"asst-456"}\n'
            )

        # Create conversation file
        conv_file = tmp_path / "conversation.jsonl"
        with open(conv_file, "w") as f:
            f.write(
                '{"type":"user","uuid":"user-1","timestamp":"2025-01-01T10:00:00Z","message":{"content":"Help me"}}\n'
            )
            f.write(
                '{"type":"assistant","uuid":"asst-123","timestamp":"2025-01-01T10:00:05Z"}\n'
            )
            f.write(
                '{"type":"assistant","uuid":"asst-789","timestamp":"2025-01-01T10:00:10Z"}\n'
            )
            f.write(
                '{"type":"assistant","uuid":"asst-456","timestamp":"2025-01-01T10:00:15Z"}\n'
            )

        # Build index and parse
        index = build_summary_index(str(tmp_path))
        summary = parse_session_minimal(conv_file, index)

        assert summary is not None
        assert summary.matched_summaries == [
            "Feature Implementation",
            "Bug Fix Discussion",
        ]
        assert summary.first_user_message == "Help me"

    def test_parse_session_no_summaries(self, tmp_path):
        """Test parsing session without summary index"""
        conv_file = tmp_path / "conversation.jsonl"
        with open(conv_file, "w") as f:
            f.write(
                '{"type":"user","timestamp":"2025-01-01T10:00:00Z","message":{"content":"Test"}}\n'
            )
            f.write(
                '{"type":"assistant","uuid":"asst-123","timestamp":"2025-01-01T10:00:05Z"}\n'
            )

        # Parse without index
        summary = parse_session_minimal(conv_file, None)
        assert summary is not None
        assert summary.matched_summaries is None

        # Parse with empty index
        summary = parse_session_minimal(conv_file, {})
        assert summary is not None
        assert summary.matched_summaries is None

    def test_parse_session_duplicate_uuids(self, tmp_path):
        """Test parsing session with duplicate assistant UUIDs"""
        conv_file = tmp_path / "conversation.jsonl"
        with open(conv_file, "w") as f:
            f.write(
                '{"type":"user","timestamp":"2025-01-01T10:00:00Z","message":{"content":"Test"}}\n'
            )
            f.write(
                '{"type":"assistant","uuid":"asst-123","timestamp":"2025-01-01T10:00:05Z"}\n'
            )
            f.write(
                '{"type":"assistant","uuid":"asst-123","timestamp":"2025-01-01T10:00:10Z"}\n'
            )  # Duplicate

        index = {"asst-123": "Duplicate Topic"}
        summary = parse_session_minimal(conv_file, index)

        assert summary is not None
        assert summary.matched_summaries == [
            "Duplicate Topic"
        ]  # Should only appear once

    def test_summary_file_size_limit(self, tmp_path):
        """Test that large files are skipped when building index"""
        # Create a large file (>10KB)
        large_file = tmp_path / "large.jsonl"
        with open(large_file, "w") as f:
            # Write summaries that would total >10KB
            for i in range(200):
                f.write(
                    f'{{"type":"summary","summary":"Topic {i}" * 50,"leafUuid":"uuid-{i}"}}\n'
                )

        # Create a small summary file
        small_file = tmp_path / "small.jsonl"
        with open(small_file, "w") as f:
            f.write(
                '{"type":"summary","summary":"Small Topic","leafUuid":"uuid-small"}\n'
            )

        index = build_summary_index(str(tmp_path))

        # Should only contain the small file's summary
        assert "uuid-small" in index
        assert "uuid-0" not in index  # From large file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
