# COT_v1 Data Backup Script
# Creates a versioned ZIP archive of data files
# Run from repository root
# Parameters: -DateTag (YYYY-MM-DD), -VersionTag (e.g., v1.1)

param(
    [Parameter(Mandatory=$true)]
    [string]$DateTag,
    
    [Parameter(Mandatory=$true)]
    [string]$VersionTag
)

$ErrorActionPreference = "Stop"

$backupDir = "_backup"
$zipName = "COT_v1_data_${DateTag}__${VersionTag}.zip"
$zipPath = Join-Path $backupDir $zipName

# Create backup directory if missing
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Write-Host "Created directory: $backupDir" -ForegroundColor Green
}

# Build list of items to backup (only if they exist)
$items = @()

# Data directories
if (Test-Path "data\compute") {
    $items += "data\compute"
} else {
    Write-Host "WARNING: data\compute not found, skipping..." -ForegroundColor Yellow
}

if (Test-Path "data\canonical") {
    $items += "data\canonical"
} else {
    Write-Host "WARNING: data\canonical not found, skipping..." -ForegroundColor Yellow
}

if (Test-Path "data\registry") {
    $items += "data\registry"
} else {
    Write-Host "INFO: data\registry not found, skipping..." -ForegroundColor Gray
}

# Note: data\raw\ is NOT backed up (too large, optional)

# Check if we have anything to backup
if ($items.Count -eq 0) {
    Write-Host "WARNING: No data directories found to backup!" -ForegroundColor Yellow
    Write-Host "  Expected: data\compute\* and/or data\canonical\*" -ForegroundColor Gray
    exit 0
}

# Create ZIP archive
Write-Host "Creating data backup..." -ForegroundColor Cyan
Write-Host "  Items to backup: $($items.Count)" -ForegroundColor Gray
Write-Host "  Output: $zipPath" -ForegroundColor Gray

try {
    Compress-Archive -Path $items -DestinationPath $zipPath -Force
    
    # Verify the archive was created and is not empty
    if (-not (Test-Path $zipPath)) {
        throw "Archive file was not created"
    }
    
    $fileSize = (Get-Item $zipPath).Length
    if ($fileSize -eq 0) {
        throw "Archive file is empty"
    }
    
    Write-Host "SUCCESS: Data backup created" -ForegroundColor Green
    Write-Host "  Path: $zipPath" -ForegroundColor White
    Write-Host "  Size: $([math]::Round($fileSize / 1MB, 2)) MB" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Failed to create backup: $_" -ForegroundColor Red
    exit 1
}
