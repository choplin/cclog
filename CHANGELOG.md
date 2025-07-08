# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2025-07-08

### Added

- New subcommand support for `cclog`
- `cclog projects` to browse all Claude Code projects
- Conversation topics shown with 📑 prefix

### Changed

- `cclog_view` and `cclog_info` functions are now subcommands: `cclog view` and `cclog info`

## [0.3.0] - 2025-07-05

### Added

- Modified time column showing relative time (e.g., "6m ago") in conversation list
- Terminal width detection and automatic line truncation to prevent horizontal scrolling in fzf
- Comprehensive test suite with fixtures for various session file formats
- Test runner script (run_tests.sh)

### Changed

- Renamed TIMESTAMP column to CREATED and made all column headers uppercase for consistency
- Reordered columns to group time-related information (CREATED, MODIFIED) together

### Fixed

- Fixed parsing of session files with summary format (now correctly shows all sessions)
- Fixed parse_session_minimal to find first timestamp regardless of position in the file
- Fixed parsing of user messages when content is an array of objects (Claude Code format)
- Fixed intermittent issue where both full line and session ID were printed
- Fixed session ID extraction when messages contain tabs or newlines by using Unit Separator (0x1F) as delimiter

## [0.2.0] - 2025-07-04

### Added

- Python helper script for improved performance
- Duration and Messages columns to conversation list

### Changed

- Stream output directly to fzf for faster initial display

## [0.1.0] - 2025-07-03

### Added

- Interactive conversation browser using fzf with real-time preview
- Full log viewer with `Ctrl-v` using system pager
- Resume conversation feature with `Ctrl-r`
- Project-specific log filtering based on current directory
- Color-coded message display (user: cyan, assistant: white, tools: gray)
- Session metadata display (ID, timestamp, message count, duration)
- Return session ID with `Enter` or file path with `Ctrl-p`
