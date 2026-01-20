# COT_v1 Restore Guide (v1.2.9)

This guide explains how to restore the COT_v1 project from backup ZIP files.

## Prerequisites

- PowerShell (Windows) or compatible shell
- Python 3.11+ installed
- Unzip utility (built into Windows)

## Restore Steps

### 1. Restore Code Backup

1. Locate the code backup in `_backup/`:
   - Format: `COT_v1_code_dataYYYY-MM-DD_v1.2.9.zip`
   - Example: `COT_v1_code_data2026-01-20_v1.2.9.zip`

2. Extract the ZIP file to the repository root:
   ```powershell
   Expand-Archive -Path "_backup\COT_v1_code_dataYYYY-MM-DD_v1.2.9.zip" -DestinationPath "." -Force
   ```

   Or manually:
   - Right-click the ZIP file → Extract All
   - Extract to the repository root directory

3. Verify restored files:
   - `src/` directory should exist
   - `tests/` directory should exist
   - `configs/` directory should exist
   - `scripts/` directory should exist
   - `requirements.txt` should exist

### 2. Restore Data Backup

1. Locate the data backup in `_backup/`:
   - Format: `COT_v1_data_dataYYYY-MM-DD_v1.2.9.zip`
   - Example: `COT_v1_data_data2026-01-20_v1.2.9.zip`

2. Extract the ZIP file to preserve directory structure:
   ```powershell
   Expand-Archive -Path "_backup\COT_v1_data_dataYYYY-MM-DD_v1.2.9.zip" -DestinationPath "." -Force
   ```

   Or manually:
   - Right-click the ZIP file → Extract All
   - Extract to the repository root (it will create/update `data/` folder)

3. Verify restored data:
   - `data/compute/metrics_weekly.parquet` should exist
   - `data/canonical/` directory should exist (if backed up)
   - `data/registry/` directory may exist (if backed up)

### 3. Set Up Python Environment

#### Option A: Virtual Environment (Recommended)

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

#### Option B: Global Installation

```powershell
pip install -r requirements.txt
```

### 4. Verify Installation

Run smoke tests to verify everything works:

```powershell
pytest -q
```

Expected output: All tests should pass.

### 5. Run the Application

Start the Streamlit dashboard:

```powershell
python -m streamlit run src/app/app.py --server.port 8510
```

Then open in browser: `http://localhost:8510`

## Expected Behavior

After restore, you should be able to:

1. **Market Page**: Opens cleanly with sidebar navigation
2. **Overview Page**: 
   - Shows selected asset (e.g., "CAD") as large header
   - Week navigation (◀ Week: YYYY-MM-DD ▶) works
   - Tabs: Positions, Open Interest, Charts, Extremes
   - Positioning Snapshot cards with Funds, Commercials, Non-Reported
3. **Navigation**: 
   - Sidebar: Version, Pages (Market/Overview buttons), Category, Asset selectors
   - Market → Overview navigation works
   - Week navigation arrows work

## Required Data Files

The application requires at minimum:
- `data/compute/metrics_weekly.parquet` - Main metrics file for Overview page

If this file is missing, you'll see an error message. Run the compute pipeline:

```powershell
python -m src.compute.run_compute --root . --log-level INFO
```

## Troubleshooting

### "Metrics file not found" error
- Ensure `data/compute/metrics_weekly.parquet` exists
- If missing, restore from data backup or run compute pipeline

### Import errors
- Verify virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### Streamlit errors
- Check Python version: `python --version` (should be 3.11+)
- Verify Streamlit is installed: `pip list | findstr streamlit`

### Tests failing
- Ensure all dependencies are installed
- Check that data files are in place
- Verify project structure matches backup

## Backup File Naming (v1.2.9)

Backups use format: `COT_v1_code_dataYYYY-MM-DD_v1.2.9.zip` and `COT_v1_data_dataYYYY-MM-DD_v1.2.9.zip`
- Example: `COT_v1_code_data2026-01-20_v1.2.9.zip` = January 20, 2026, version 1.2.9
- Always use the most recent backup for restore

## Version History

### v1.2.9 - 2026-01-20

- Code: `COT_v1_code_data2026-01-20_v1.2.9.zip`
- Data: `COT_v1_data_data2026-01-20_v1.2.9.zip`
- Notes: Version bump, backups aligned to v1.2.9 naming

## Notes

- Code backups include: `app.py`, `src/`, `tests/`, `configs/`, `scripts/`, `requirements.txt`, `README.md`
- Data backups include: `data/compute/*`, `data/canonical/*`, `data/registry/*` (if exists)
- Raw data files (`data/raw/`) are NOT backed up (too large, optional)
- Git history is NOT backed up (use Git for version control)
- Virtual environments (`.venv/`) are NOT backed up (recreate after restore)
- Cache directories (`__pycache__/`, `.pytest_cache/`) are NOT backed up
