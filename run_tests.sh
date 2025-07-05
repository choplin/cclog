#!/bin/bash
# Simple test runner for cclog

echo "Running cclog tests..."

# Check if pytest is installed
if ! command -v pytest &>/dev/null; then
    echo "Error: pytest is not installed."
    echo "Please install pytest with: pip install pytest"
    exit 1
fi

# Run tests
pytest tests/ -v

# Return exit code
exit $?
