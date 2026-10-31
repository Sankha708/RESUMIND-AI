$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot 'backend'
Set-Location $Backend
$Python = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Backend venv missing. Run scripts\setup-backend.ps1 first.' }
& $Python -c "import uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Backend dependencies are missing. Run scripts\setup-backend.ps1 first.' }
if (-not $env:DEBUG) { $env:DEBUG = 'true' }
if (-not $env:APP_ENV) { $env:APP_ENV = 'development' }
Write-Host 'Starting RESUMIND AI API on http://127.0.0.1:8000 (Ctrl+C to stop).' -ForegroundColor Cyan
& $Python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
if ($LASTEXITCODE -ne 0) { throw "Backend stopped with exit code $LASTEXITCODE." }
