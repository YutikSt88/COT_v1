# Verify backup ZIP files
param(
    [string]$VersionTag = "v1.1.1"
)

$ErrorActionPreference = "Stop"

$DateTag = (Get-Date).ToString("yyyy-MM-dd")
$codeZip = "_backup\COT_v1_code_${DateTag}__${VersionTag}.zip"
$dataZip = "_backup\COT_v1_data_${DateTag}__${VersionTag}.zip"

Write-Host "Verifying backup files..." -ForegroundColor Cyan
Write-Host ""

# Check code ZIP
if (-not (Test-Path $codeZip)) {
    Write-Host "ERROR: Code ZIP not found: $codeZip" -ForegroundColor Red
    exit 1
}

$codeInfo = Get-Item $codeZip
if ($codeInfo.Length -eq 0) {
    Write-Host "ERROR: Code ZIP is empty: $codeZip" -ForegroundColor Red
    exit 1
}

Write-Host "Code ZIP OK: $($codeInfo.Length) bytes, Modified: $($codeInfo.LastWriteTime)" -ForegroundColor Green

# Check data ZIP
if (-not (Test-Path $dataZip)) {
    Write-Host "ERROR: Data ZIP not found: $dataZip" -ForegroundColor Red
    exit 1
}

$dataInfo = Get-Item $dataZip
if ($dataInfo.Length -eq 0) {
    Write-Host "ERROR: Data ZIP is empty: $dataZip" -ForegroundColor Red
    exit 1
}

Write-Host "Data ZIP OK: $($dataInfo.Length) bytes, Modified: $($dataInfo.LastWriteTime)" -ForegroundColor Green

Write-Host ""
Write-Host "Testing ZIP validity..." -ForegroundColor Cyan

# Test code ZIP
$tempDir = "_backup\temp_test"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

try {
    Expand-Archive -Path $codeZip -DestinationPath "$tempDir\code" -Force
    Write-Host "Code ZIP is valid" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Code ZIP validation failed: $_" -ForegroundColor Red
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    exit 1
}

# Test data ZIP
try {
    Expand-Archive -Path $dataZip -DestinationPath "$tempDir\data" -Force
    Write-Host "Data ZIP is valid" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Data ZIP validation failed: $_" -ForegroundColor Red
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    exit 1
}

# Cleanup
Remove-Item -Recurse -Force $tempDir

Write-Host ""
Write-Host "All backup files are valid!" -ForegroundColor Green
exit 0
