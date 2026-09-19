$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

function Assert-LastExitCode([string]$step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$step failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path $pythonPath)) {
    throw "Python environment is missing. Run 'npm run setup' first."
}

npm run lint --prefix (Join-Path $projectRoot "apps\mobile")
Assert-LastExitCode "Mobile lint"
npm run typecheck --prefix (Join-Path $projectRoot "apps\mobile")
Assert-LastExitCode "Mobile typecheck"
npm test --prefix (Join-Path $projectRoot "apps\mobile")
Assert-LastExitCode "Mobile tests"

$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
$env:DATABASE_URL = "sqlite:///:memory:"
& $pythonPath (Join-Path $projectRoot "apps\backend\manage.py") check
Assert-LastExitCode "Django check"
& $pythonPath (Join-Path $projectRoot "apps\backend\manage.py") makemigrations --check --dry-run
Assert-LastExitCode "Migration drift check"
& $pythonPath (Join-Path $projectRoot "apps\backend\manage.py") test apps.core apps.accounts apps.content apps.consultations apps.payments apps.messaging apps.notifications apps.video apps.coaching apps.progress
Assert-LastExitCode "Backend tests"

Write-Host "All project checks passed." -ForegroundColor Green
