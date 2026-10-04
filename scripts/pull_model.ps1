# Installs Ollama (if missing) and pulls the Qwen2.5 14B model locally.
$ErrorActionPreference = "Stop"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama not found. Opening download page (https://ollama.com/download/windows)..."
    Start-Process "https://ollama.com/download/windows"
    Write-Host "Install Ollama, then re-run this script."
    exit 1
}

Write-Host "Pulling qwen2.5:14b (this downloads several GB, may take a while)..."
ollama pull qwen2.5:14b

Write-Host "Done. Model is stored locally by Ollama and ready to use."
