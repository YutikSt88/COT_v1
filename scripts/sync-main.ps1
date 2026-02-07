param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($currentBranch -ne "main") {
    Write-Host "Switching branch: $currentBranch -> main" -ForegroundColor Yellow
    git checkout main | Out-Host
}

if (-not $Force) {
    $dirty = git status --porcelain
    if ($dirty) {
        Write-Error "Working tree is not clean. Commit/stash changes, or rerun with -Force."
    }
}

Write-Host "Fetching origin..." -ForegroundColor Cyan
git fetch origin | Out-Host

if ($Force) {
    Write-Host "Hard-resetting to origin/main..." -ForegroundColor Yellow
    git reset --hard origin/main | Out-Host
} else {
    Write-Host "Fast-forward pull from origin/main..." -ForegroundColor Cyan
    git pull --ff-only origin main | Out-Host
}

Write-Host "Current HEAD:" -ForegroundColor Green
git log --oneline -1 | Out-Host
