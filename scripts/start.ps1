# Starts the FastAPI backend (serves API + chat UI). Assumes Ollama is already running.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
. .\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --host 127.0.0.1 --port 8000
Pop-Location
