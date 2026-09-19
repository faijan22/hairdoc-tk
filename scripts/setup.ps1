$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"

$env:npm_config_cache = Join-Path $projectRoot ".npm-cache"
$env:PIP_CACHE_DIR = Join-Path $projectRoot ".pip-cache"

if (-not (Test-Path $pythonPath)) {
    python -m venv $venvPath
}

& $pythonPath -m pip install --disable-pip-version-check --no-input --quiet -r (Join-Path $projectRoot "apps\backend\requirements\development.txt")
& npm.cmd install --prefix (Join-Path $projectRoot "apps\mobile") --no-audit --no-fund
& $pythonPath (Join-Path $projectRoot "apps\backend\manage.py") migrate

Write-Host "Setup complete. Run: npm run dev" -ForegroundColor Green
