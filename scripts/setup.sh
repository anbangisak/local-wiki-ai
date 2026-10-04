#!/usr/bin/env bash
# Creates a virtual environment and installs Python dependencies.
set -e
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$root"
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
# Git Bash on Windows uses the Scripts/ layout, not bin/
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -r requirements.txt

echo "Setup complete. Edit config/config.yaml (wiki_db.path) then run scripts/start.sh"
