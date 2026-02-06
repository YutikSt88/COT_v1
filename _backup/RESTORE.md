# COT_v1 Restore Guide (v1.2.9)

This guide explains how to restore the COT_v1 project from backup ZIP files.

## Prerequisites
- PowerShell (Windows) or compatible shell
- Python 3.11+
- Unzip utility (built into Windows)

## Restore Steps

### 1) Restore Code Backup

1. Locate the code backup in `_backup/`:
   - Format: `COT_v1_code_YYYY-MM-DD__v1.2.9.zip`
   - Example: `COT_v1_code_2026-01-20__v1.2.9.zip`

2. Extract the ZIP file to the repository root:
   ```powershell
   Expand-Archive -Path "_backup\COT_v1_code_YYYY-MM-DD__v1.2.9.zip" -DestinationPath "." -Force
   ```

3. Verify restored files:
   - `src/`, `tests/`, `configs/`, `scripts/`
   - `requirements.txt`, `README.md`, `app.py`

### 2) Restore Data Backup

1. Locate the data backup in `_backup/`:
   - Format: `COT_v1_data_YYYY-MM-DD__v1.2.9.zip`
   - Example: `COT_v1_data_2026-01-20__v1.2.9.zip`

2. Extract the ZIP file:
   ```powershell
   Expand-Archive -Path "_backup\COT_v1_data_YYYY-MM-DD__v1.2.9.zip" -DestinationPath "." -Force
   ```

3. Verify restored data:
   - `data/compute/metrics_weekly.parquet`
   - `data/canonical/` (if backed up)

### 3) Set Up Python Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4) Verify Installation

```powershell
pytest -q
```

### 5) Run the Application

```powershell
streamlit run src/app/app.py --server.port 8510
```

Open: `http://localhost:8510`

## Required Data Files
At minimum:
- `data/compute/metrics_weekly.parquet`

If missing:
```powershell
python -m src.compute.run_compute --root . --log-level INFO
```

## Backup File Naming (v1.2.9)
`COT_v1_code_YYYY-MM-DD__v1.2.9.zip`  
`COT_v1_data_YYYY-MM-DD__v1.2.9.zip`

## Notes
- Raw ZIPs in `data/raw/` are not backed up (too large).
- `.venv/`, `.pytest_cache/`, and `__pycache__/` are not backed up.
