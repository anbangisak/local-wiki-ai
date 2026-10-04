# Creates a virtual environment and installs Python dependencies.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
Pop-Location

Write-Host "Setup complete. Edit config/config.yaml (wiki_db.path) then run scripts/start.ps1"
