param(
    [ValidateSet("streamlit", "react")]
    [string]$Mode = "streamlit"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$clientDir = Join-Path $root "client"

if (-not (Test-Path $venvPython)) {
    Write-Error "Python venv not found: $venvPython"
}

if ($Mode -eq "streamlit") {
    Write-Host "Starting Streamlit UI..." -ForegroundColor Cyan
    & $venvPython -m streamlit run (Join-Path $root "app.py")
    exit $LASTEXITCODE
}

if (-not (Test-Path (Join-Path $clientDir "package.json"))) {
    Write-Error "Frontend package.json not found: $clientDir"
}

Write-Host "Starting API in a new PowerShell window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$root'; & '$venvPython' -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload"
)

Write-Host "Starting React frontend in a new PowerShell window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$clientDir'; npm install; npm run dev"
)

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "API:       http://127.0.0.1:8000/api/health"
Write-Host "Frontend:  http://localhost:5173"
