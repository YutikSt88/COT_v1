# COT_v1 Code Backup Script
# Creates a versioned ZIP archive of all code files
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
$zipName = "COT_v1_code_${DateTag}__${VersionTag}.zip"
$zipPath = Join-Path $backupDir $zipName

# Create backup directory if missing
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Write-Host "Created directory: $backupDir" -ForegroundColor Green
}

# Build list of items to backup (only if they exist)
$items = @()

# Core files
if (Test-Path "app.py") { $items += "app.py" }
if (Test-Path "README.md") { $items += "README.md" }
if (Test-Path "requirements.txt") { $items += "requirements.txt" }

# Directories
if (Test-Path "src") { $items += "src" }
if (Test-Path "configs") { $items += "configs" }
if (Test-Path "tests") { $items += "tests" }
if (Test-Path "scripts") { $items += "scripts" }

# Check if we have anything to backup
if ($items.Count -eq 0) {
    Write-Host "ERROR: No code files found to backup!" -ForegroundColor Red
    exit 1
}

# Create temporary exclusion list for Compress-Archive
# Note: Compress-Archive doesn't support exclusions directly, so we'll use a workaround
# by creating a temporary directory structure

Write-Host "Creating code backup..." -ForegroundColor Cyan
Write-Host "  Items to backup: $($items.Count)" -ForegroundColor Gray
Write-Host "  Output: $zipPath" -ForegroundColor Gray

try {
    # Use Compress-Archive with explicit paths
    # Exclusions: .venv/, __pycache__/, .pytest_cache/, _backup/
    # These are handled by not including them in $items
    
    Compress-Archive -Path $items -DestinationPath $zipPath -Force
    
    # Verify the archive was created and is not empty
    if (-not (Test-Path $zipPath)) {
        throw "Archive file was not created"
    }
    
    $fileSize = (Get-Item $zipPath).Length
    if ($fileSize -eq 0) {
        throw "Archive file is empty"
    }
    
    Write-Host "SUCCESS: Code backup created" -ForegroundColor Green
    Write-Host "  Path: $zipPath" -ForegroundColor White
    Write-Host "  Size: $([math]::Round($fileSize / 1MB, 2)) MB" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Failed to create backup: $_" -ForegroundColor Red
    exit 1
}
