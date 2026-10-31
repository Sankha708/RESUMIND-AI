$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot 'backend'
Set-Location $Backend
$Python = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Backend venv missing. Run scripts\setup-backend.ps1 first.' }
& $Python -m compileall -q app tests
if ($LASTEXITCODE -ne 0) { throw 'Python compilation failed.' }

# Use a fresh, uniquely named pytest basetemp so runs never reuse a stale or
# permission-locked scratch directory left over from an interrupted session.
$BaseTemp = Join-Path $env:TEMP ("resumind-pytest-" + [guid]::NewGuid().ToString('N'))
try {
    & $Python -m pytest -q -p no:cacheprovider --basetemp=$BaseTemp
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed. Review the full pytest output above.' }
}
finally {
    Remove-Item -Recurse -Force $BaseTemp -ErrorAction SilentlyContinue
}
