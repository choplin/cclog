# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

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

### Requirements

- fzf
- jq
- Claude Code CLI
