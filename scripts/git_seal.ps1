# AeroVantage v0.1.0 Git mühürleme scripti
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path .git)) {
    git init
}

git add .

$env:GIT_AUTHOR_NAME = "AeroVantage"
$env:GIT_AUTHOR_EMAIL = "aerovantage@local.dev"
$env:GIT_COMMITTER_NAME = "AeroVantage"
$env:GIT_COMMITTER_EMAIL = "aerovantage@local.dev"

if (-not (git rev-parse HEAD 2>$null)) {
    git commit -m "feat: v0.1.0 MVP core modules (forecast, market, risk, api, dashboard) initialized"
}

git branch -M main

if (-not (git tag -l "v0.1.0")) {
    git tag v0.1.0
}

if (git show-ref --verify --quiet refs/heads/dev) {
    git checkout dev
} else {
    git checkout -b dev
}

Write-Host "inside_work_tree: $(git rev-parse --is-inside-work-tree)"
Write-Host "current_branch: $(git branch --show-current)"
Write-Host "tags: $(git tag -l)"
Write-Host "last_commit: $(git log -1 --oneline)"
