# cclog - Claude Code Session Browser

Browse and view Claude Code session logs using fzf.

## Installation

### Using sheldon

Add to your `~/.config/sheldon/plugins.toml`:

```toml
[plugins.cclog]
github = "choplin/cclog"
```

Then run:

```bash
sheldon lock --update
```

### Manual Installation

```bash
git clone https://github.com/choplin/cclog.git
```

Add to your shell configuration:

```bash
# For bash/zsh
source /path/to/cclog/cclog.sh

# For zsh with plugin managers (oh-my-zsh, etc)
# The cclog.plugin.zsh will be loaded automatically
```

## Usage

### List sessions with fzf

```bash
cclog_list
```

**Key bindings:**

- `Enter`: View the full log in your pager (using `cclog_view`)
- `Ctrl-R`: Resume the conversation with `claude -r`

### View a specific log file

```bash
cclog_view ~/.claude/projects/*/session-id.jsonl
```

### Show session information

```bash
cclog_info ~/.claude/projects/*/session-id.jsonl session-id
```

## Requirements

- `fzf` - Fuzzy finder
- `jq` - JSON processor
- `claude` - Claude Code CLI (for resume functionality)

## Features

- Color-coded messages (User: Cyan, Assistant: White, Tool: Gray)
- Session information display (file, messages count, start time, duration)
- Interactive browsing with fzf
- Resume conversations directly from the browser

## License

MIT
