# Local development launcher with hot-reload
# Usage: .\run_dev.ps1
# Ctrl+C to stop

param(
    [int]$Port = 8000,
    [string]$Host = "127.0.0.1"
)

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ssZ"
Write-Host "[$timestamp] FastAPI Local Development Server" -ForegroundColor Cyan
Write-Host "Host: $Host | Port: $Port"
Write-Host "Docs: http://$Host`:$Port/docs"
Write-Host "ReDoc: http://$Host`:$Port/redoc"
Write-Host ""

# Check if venv exists, create if not
if (-not (Test-Path "venv")) {
    Write-Host "[$timestamp] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt --quiet
} else {
    .\venv\Scripts\Activate.ps1
}

Write-Host "[$timestamp] Starting uvicorn with --reload..." -ForegroundColor Green
uvicorn main:app --host $Host --port $Port --reload
