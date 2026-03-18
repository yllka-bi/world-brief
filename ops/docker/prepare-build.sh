#!/bin/bash
# Helper script to prepare Docker build environment
# Creates necessary directories if they don't exist

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." &> /dev/null && pwd )"

# Create .temp directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/.temp"

# Create .ssh directory if it doesn't exist (or copy from ~/.ssh if available)
if [ ! -d "$SCRIPT_DIR/.temp/.ssh" ]; then
    if [ -d "$HOME/.ssh" ]; then
        echo "Copying SSH keys from ~/.ssh"
        cp -r "$HOME/.ssh" "$SCRIPT_DIR/.temp/.ssh"
    else
        echo "Creating empty .ssh directory (no SSH keys found)"
        mkdir -p "$SCRIPT_DIR/.temp/.ssh"
        touch "$SCRIPT_DIR/.temp/.ssh/.gitkeep"
    fi
fi

echo "Build environment prepared. You can now run: docker compose build"

