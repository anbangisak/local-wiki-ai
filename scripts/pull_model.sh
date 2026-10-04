#!/usr/bin/env bash
# Installs Ollama (if missing) and pulls the Qwen2.5 14B model locally.
set -e

if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama not found. Opening download page (https://ollama.com/download/windows)..."
    # Git Bash has no native "start"; delegate to cmd.exe's built-in.
    cmd.exe /c start "" "https://ollama.com/download/windows"
    echo "Install Ollama, then re-run this script."
    exit 1
fi

echo "Pulling qwen2.5:14b (this downloads several GB, may take a while)..."
ollama pull qwen2.5:14b

echo "Done. Model is stored locally by Ollama and ready to use."
