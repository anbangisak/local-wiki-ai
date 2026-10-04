#!/usr/bin/env bash
# Starts the FastAPI backend (serves API + chat UI). Assumes Ollama is already running.
set -e
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$root"
./.venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
