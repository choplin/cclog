# Claude Projects JSONL File Specification

Based on empirical observation of files in `~/.claude/projects/`

## Overview

Claude Code stores conversation and metadata files in `~/.claude/projects/` using the JSONL (JSON Lines) format. Each directory corresponds to a project path with special character encoding.

## Directory Naming Convention

Project directories are named by converting the absolute path:

- `/` → `-`
- `.` → `-`

Example: `/Users/username/workspace/my-project/.amux/workspaces/workspace-feature-branch-1750399353-9b977c1c/worktree`
→ `-Users-username-workspace-my-project--amux-workspaces-workspace-feature-branch-1750399353-9b977c1c-worktree/`

## File Types

### 1. Conversation Files

- **Filename**: `{uuid}.jsonl` where UUID may or may not match the sessionId inside
- **Content**: Full conversation history with timestamps
- **Size**: Can be very large (1000+ lines)
- **Characteristics**:
  - Every entry has a `timestamp` field
  - Contains `user` and `assistant` message types
  - Includes tool use entries
  - Has `sessionId` field in each entry

### 2. Summary Files

- **Filename**: `{uuid}.jsonl` (indistinguishable from conversation files by name alone)
- **Content**: Topic summaries only
- **Size**: Small (typically 1-10 lines)
- **Characteristics**:
  - No `timestamp` fields
  - Only `type: "summary"` entries
  - Each entry contains:
    - `type`: Always "summary"
    - `summary`: Brief topic description
    - `leafUuid`: References a specific assistant message UUID in a conversation file

### 3. Mixed Files

- **Filename**: `{uuid}.jsonl` (indistinguishable from other types by name alone)
- **Content**: Starts with summary entries, followed by conversation entries
- **Size**: Variable, can be large
- **Characteristics**:
  - Initial lines contain `type: "summary"` entries
  - Followed by regular conversation entries with timestamps
  - Most common file type in some directories (e.g., 113 out of 149 files)
  - Used when resuming or continuing previous conversations

## Entry Types

### Conversation Entries

#### User Message

```json
{
  "parentUuid": "previous-message-uuid" | null,
  "isSidechain": false,
  "userType": "external",
  "cwd": "/path/to/working/directory",
  "sessionId": "session-uuid",
  "version": "1.0.35",
  "type": "user",
  "message": {
    "role": "user",
    "content": "string" | [{type: "text", text: "string"}, ...]
  },
  "uuid": "unique-message-uuid",
  "timestamp": "2025-07-02T08:44:42.908Z"
}
```

#### Assistant Message

```json
{
  "parentUuid": "previous-message-uuid",
  "isSidechain": false,
  "userType": "external",
  "cwd": "/path/to/working/directory",
  "sessionId": "session-uuid",
  "version": "1.0.35",
  "message": {
    "id": "msg_...",
    "type": "message",
    "role": "assistant",
    "model": "claude-opus-4-20250514",
    "content": [{"type": "text", "text": "response"}, ...],
    "stop_reason": null,
    "stop_sequence": null,
    "usage": {
      "input_tokens": 4,
      "cache_creation_input_tokens": 26078,
      "cache_read_input_tokens": 0,
      "output_tokens": 1,
      "service_tier": "standard"
    }
  },
  "requestId": "req_...",
  "type": "assistant",
  "uuid": "unique-message-uuid",
  "timestamp": "2025-07-02T08:44:46.656Z"
}
```

#### Tool Use (Assistant)

```json
{
  "parentUuid": "previous-message-uuid",
  "isSidechain": false,
  "userType": "external",
  "cwd": "/path/to/working/directory",
  "sessionId": "session-uuid",
  "version": "1.0.35",
  "message": {
    "id": "msg_...",
    "type": "message",
    "role": "assistant",
    "model": "claude-opus-4-20250514",
    "content": [{
      "type": "tool_use",
      "id": "toolu_...",
      "name": "tool_name",
      "input": {...}
    }],
    "stop_reason": null,
    "stop_sequence": null,
    "usage": {...}
  },
  "requestId": "req_...",
  "type": "assistant",
  "uuid": "unique-message-uuid",
  "timestamp": "2025-07-02T08:44:46.656Z"
}
```

#### Tool Result (User)

```json
{
  "parentUuid": "tool-use-message-uuid",
  "isSidechain": false,
  "userType": "external",
  "cwd": "/path/to/working/directory",
  "sessionId": "session-uuid",
  "version": "1.0.35",
  "type": "user",
  "message": {
    "role": "user",
    "content": [
      {
        "tool_use_id": "toolu_...",
        "type": "tool_result",
        "content": [
          {
            "type": "text",
            "text": "tool execution result"
          }
        ]
      }
    ]
  },
  "uuid": "unique-message-uuid",
  "timestamp": "2025-07-02T08:44:47.123Z",
  "toolUseResult": [
    {
      "type": "text",
      "text": "tool execution result"
    }
  ]
}
```

### Summary Entries

```json
{
  "type": "summary",
  "summary": "Brief topic description",
  "leafUuid": "uuid-of-assistant-message"
}
```

## Important Observations

### 1. Filename vs SessionId Mismatch

- The filename UUID doesn't always match the sessionId inside the file
- Example: File `e72e32a7-ce78-4c89-97da-7f0177271330.jsonl` contains:
  - 446 entries with sessionId `e72e32a7-ce78-4c89-97da-7f0177271330`
  - 8 entries with sessionId `58b61b9c-932c-4786-abac-ee02be57f0cb`
- The filename appears to match the MAJORITY sessionId in the file

### 2. Session Interleaving

- A single file can contain entries from multiple sessions
- Sessions can be interleaved (not necessarily in chronological order)
- This happens during session resumption or continuation

### 3. LeafUuid Purpose

- `leafUuid` in summary files points to specific assistant message UUIDs
- Used to create topic indices linking summaries to specific conversation points
- The referenced messages can be in any conversation file within the project

### 4. Identifying File Types

To distinguish between file types:

- **Summary files**: Only contain entries with `type: "summary"` and no timestamps
- **Conversation files**: Start with entries containing timestamps
- **Mixed files**: Start with summary entries, then have conversation entries
- Check first ~20 lines to determine type, as mixed files transition early
- File size alone is not reliable (mixed files can be very large)

## Implications for Tools

### Searching for Messages by UUID

1. Cannot rely on filename matching sessionId
2. Must search across all conversation files
3. Summary files can be skipped for message searches
4. Use efficient tools like `grep` or `ripgrep` for UUID searches

### Listing Conversations

1. Filter out summary-only files (no timestamps)
2. Parse first valid timestamp and user message
3. Count total lines for message count
4. Handle files with multiple sessionIds appropriately

## File Organization Example

```
~/.claude/projects/-Users-username-workspace-my-project/
├── 4a32ac02-d074-4e93-87b3-acbb14590f78.jsonl  # Summary file (2 lines)
├── 58b61b9c-932c-4786-abac-ee02be57f0cb.jsonl  # Conversation (1710 lines)
├── 67cf720e-ecd1-44b8-9b80-71ce7de51be1.jsonl  # Summary file (1 line)
├── 077cf5fd-bccc-40f2-ba29-48ac90386509.jsonl  # Mixed file (1988 lines: 2 summaries + conversation)
├── c6cbbc83-fad6-46d7-a4b0-7413cfef1448.jsonl  # Summary file (7 lines)
└── e72e32a7-ce78-4c89-97da-7f0177271330.jsonl  # Conversation (212 lines, multi-session)
```

## Key Fields

### Common Fields (All Conversation Entries)

- `type`: Entry type ("user", "assistant", "summary")
- `uuid`: Unique identifier for the message
- `parentUuid`: Reference to previous message (null for first message)
- `timestamp`: ISO 8601 timestamp
- `sessionId`: Session identifier (may not match filename)
- `isSidechain`: Boolean, always observed as `false`
- `userType`: Always "external" in observed data
- `cwd`: Current working directory
- `version`: Claude Code version (e.g., "1.0.35")

### Assistant-Specific Fields

- `requestId`: Unique request identifier (format: "req\_...")
- `message.id`: Message identifier (format: "msg\_...")
- `message.model`: Model used (e.g., "claude-opus-4-20250514")
- `message.usage`: Token usage statistics

### Tool-Related Fields

- Tool use: `message.content[].type: "tool_use"` with `id`, `name`, `input`
- Tool result: `message.content[].type: "tool_result"` with `tool_use_id`
- `toolUseResult`: Additional field in user entries with tool results

## Notes

- This specification is based on observation and may not cover all cases
- Claude Code's internal implementation may change
- Summary files appear to be used for context tracking and topic indexing
- The JSONL format allows for streaming and incremental updates
- File type distribution varies by project:
  - In active projects, mixed files can be the majority (e.g., 76% in one observed case)
  - Mixed files are created when resuming or continuing previous sessions
- Entry counts observed in one large directory: ~33K assistant, ~21K user, ~600 summary entries
