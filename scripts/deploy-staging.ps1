$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$target = $env:HAIRDOC_DEPLOY_TARGET
$remotePath = $env:HAIRDOC_DEPLOY_PATH
$branch = if ($env:HAIRDOC_DEPLOY_BRANCH) { $env:HAIRDOC_DEPLOY_BRANCH } else { "main" }

if (-not $target -or $target -notmatch '^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$') {
    throw "Set HAIRDOC_DEPLOY_TARGET to the server SSH target, for example deploy@203.0.113.10."
}
if (-not $remotePath -or $remotePath -notmatch '^/[A-Za-z0-9._/-]+$') {
    throw "Set HAIRDOC_DEPLOY_PATH to the absolute server checkout, for example /opt/hairdoc-tk."
}
if ($branch -notmatch '^[A-Za-z0-9._/-]+$') {
    throw "HAIRDOC_DEPLOY_BRANCH contains unsupported characters."
}

Push-Location $projectRoot
try {
    $changes = @(git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect the Git working tree." }
    if ($changes.Count -gt 0) {
        throw "Commit the local changes before deployment. The deploy command only ships committed code."
    }

    git push origin $branch
    if ($LASTEXITCODE -ne 0) { throw "Git push failed." }

    $remoteCommand = "cd '$remotePath' && HAIRDOC_BRANCH='$branch' bash deploy/staging/deploy.sh"
    ssh $target $remoteCommand
    if ($LASTEXITCODE -ne 0) { throw "Remote staging deployment failed." }
} finally {
    Pop-Location
}

