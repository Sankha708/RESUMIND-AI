$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $ProjectRoot 'frontend'
Set-Location $Frontend
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Node.js/npm not found. Install a supported Node.js LTS release first.' }
if (-not (Test-Path 'package-lock.json')) { throw 'package-lock.json is missing; refusing to regenerate it automatically.' }
npm ci
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend production build failed.' }
Write-Host 'Frontend dependencies installed and production build passed.' -ForegroundColor Green
