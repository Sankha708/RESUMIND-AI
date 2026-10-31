$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $ProjectRoot 'frontend'
Set-Location $Frontend
if (-not (Test-Path 'node_modules')) { throw 'Frontend dependencies missing. Run scripts\setup-frontend.ps1 first.' }
npm run dev -- --hostname 127.0.0.1
