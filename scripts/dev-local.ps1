# Local Development Launcher for WordQuest 9 (Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv (Join-Path $Root "backend\.venv")
    & $Py -m pip install -r (Join-Path $Root "backend\requirements.txt")
}

$env:PYTHONPATH = Join-Path $Root "backend\shared"
$env:DATA_DIR = Join-Path $Root "data"
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "sqlite:///$((Join-Path $Root 'wordquest9_local.db') -replace '\\', '/')"
}

Write-Host "Seeding / UPSERTing 12 Units of Tiếng Anh 9 data..." -ForegroundColor Green
& $Py (Join-Path $Root "backend\scripts\import_notebook_data.py") --data-dir $env:DATA_DIR

Write-Host "Starting API Gateway (embedded mode on http://localhost:8000)..." -ForegroundColor Cyan
$env:GATEWAY_MODE = "embedded"
Start-Process -NoNewWindow -FilePath $Py -ArgumentList "-m", "uvicorn", "main:app", "--app-dir", (Join-Path $Root "backend\services\api_gateway"), "--host", "0.0.0.0", "--port", "8000"

Write-Host "Starting MCP Server (http://localhost:8005/mcp)..." -ForegroundColor Cyan
$env:MCP_TRANSPORT = "streamable-http"
Start-Process -NoNewWindow -FilePath $Py -ArgumentList (Join-Path $Root "backend\mcp_server\server.py")

Write-Host "Starting Next.js Frontend (http://localhost:3000)..." -ForegroundColor Cyan
Set-Location (Join-Path $Root "frontend")
npm run dev
