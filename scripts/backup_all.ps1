# COT_v1 Complete Backup Script
# Runs both code and data backup scripts
# Run from repository root

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "COT_v1 Complete Backup (v1.1.1)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set version tag
$VersionTag = "v1.1.1"
$DateTag = (Get-Date).ToString("yyyy-MM-dd")

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

# Change to repo root
Set-Location $repoRoot

# Create _backup directory if missing
$backupDir = "_backup"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Write-Host "Created directory: $backupDir" -ForegroundColor Green
}

# Run code backup
Write-Host "Step 1: Code Backup" -ForegroundColor Yellow
Write-Host "-------------------" -ForegroundColor Yellow
$codeResult = & "$scriptDir\backup_code.ps1" -DateTag $DateTag -VersionTag $VersionTag 2>&1
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    Write-Host "ERROR: Code backup failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Run data backup
Write-Host "Step 2: Data Backup" -ForegroundColor Yellow
Write-Host "-------------------" -ForegroundColor Yellow
$dataResult = & "$scriptDir\backup_data.ps1" -DateTag $DateTag -VersionTag $VersionTag 2>&1
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    Write-Host "ERROR: Data backup failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Verify backup files exist and are not empty
$codeZip = Join-Path $backupDir "COT_v1_code_${DateTag}__${VersionTag}.zip"
$dataZip = Join-Path $backupDir "COT_v1_data_${DateTag}__${VersionTag}.zip"

if (-not (Test-Path $codeZip)) {
    Write-Host "ERROR: Code backup file not found: $codeZip" -ForegroundColor Red
    exit 1
}

if ((Get-Item $codeZip).Length -eq 0) {
    Write-Host "ERROR: Code backup file is empty: $codeZip" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $dataZip)) {
    Write-Host "ERROR: Data backup file not found: $dataZip" -ForegroundColor Red
    exit 1
}

if ((Get-Item $dataZip).Length -eq 0) {
    Write-Host "ERROR: Data backup file is empty: $dataZip" -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "Backup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Code backup: $codeZip" -ForegroundColor White
Write-Host "Data backup: $dataZip" -ForegroundColor White
Write-Host ""
