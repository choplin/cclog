# cclog - Claude Code Session Browser

Browse and view Claude Code session logs using fzf.

https://github.com/user-attachments/assets/5019c393-8082-4cbc-b2b5-ec0549585681

The demo shows:
1. Opening the session list with `cclog`
2. Navigating through sessions with real-time preview
3. Resuming a Claude Code session with `Ctrl-R`

## Installation

### Using Sheldon (Recommended)

Add to your `~/.config/sheldon/plugins.toml`:

```toml
[plugins.cclog]
github = "choplin/cclog"
```

Then run:

```bash
sheldon lock --update
```

### Manual Installation (bash/zsh)

Works with both bash and zsh:

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

<details>
<summary>Other Plugin Managers</summary>

> **Note:** These methods haven't been tested but should work thanks to the standard `.plugin.zsh` file structure. Please open an issue if you encounter any problems!

#### Oh-My-Zsh

```bash
git clone https://github.com/choplin/cclog ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/cclog
```

Then add `cclog` to the plugins array in your `~/.zshrc`:

```bash
plugins=(... cclog)
```

#### Zinit

```bash
zinit load choplin/cclog
```

#### Zplug

```bash
zplug "choplin/cclog"
```

#### Antigen

```bash
antigen bundle choplin/cclog
```

#### Zgen

```bash
zgen load choplin/cclog
```

#### Antibody

```bash
antibody bundle choplin/cclog
```

</details>

## Usage

### List sessions with fzf

```bash
cclog
```

**Key bindings:**

- `Enter`: Return the session ID
- `Ctrl-V`: View the full log in your pager
- `Ctrl-P`: Return the file path
- `Ctrl-R`: Resume the conversation with `claude -r`

### View a specific log file

```bash
cclog_view ~/.claude/projects/*/session-id.jsonl
```

### Show session information

```bash
cclog_info ~/.claude/projects/*/session-id.jsonl
```

## Requirements

- `fzf` - Fuzzy finder
- `python3` - Python 3.x (for performance optimization)
- `claude` - Claude Code CLI (for resume functionality)

## Features

- Color-coded messages (User: Cyan, Assistant: White, Tool: Gray)
- Session information display (file, messages count, start time, duration)
- Interactive browsing with fzf
- Resume conversations directly from the browser
- Performance optimized with Python helper script for large conversation histories
- Stream-based processing for efficient memory usage
- Duration and message count columns in the conversation list

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
