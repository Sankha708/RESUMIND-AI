$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot 'backend'
Set-Location $Backend

if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    python -m venv .venv
}
$Python = '.\.venv\Scripts\python.exe'
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
& $Python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Alembic migration failed.' }
Write-Host 'Backend setup completed. Run scripts\test-backend.ps1 before relying on the application.' -ForegroundColor Green
