"""Create versioned backup ZIP files (code + data)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

# Version to backup
VERSION = "v1.2.1"
TODAY = date.today().strftime("%Y-%m-%d")

# Paths
ROOT = Path(".").resolve()
BACKUP_DIR = ROOT / "_backup"
CODE_ZIP = BACKUP_DIR / f"COT_v1_code_{TODAY}__{VERSION}.zip"
DATA_ZIP = BACKUP_DIR / f"COT_v1_data_{TODAY}__{VERSION}.zip"

# Code backup paths (check existence before adding)
# Note: root app.py removed (canonical entrypoint is src/app/app.py)
CODE_PATHS = [
    "src",
    "configs",
    "docs",
    "scripts",
    "tests",
    "requirements.txt",
    "pyproject.toml",
    "README.md",
    "_backup/RESTORE.md",
    # "app.py" removed - canonical entrypoint is src/app/app.py
]

# Data backup paths (only specific directories and files)
DATA_PATHS = [
    "data/canonical",
    "data/compute",
    "data/registry",
    "data/raw/manifest.csv",
]

# Exclude patterns
EXCLUDE_PATTERNS = {
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".pytest_cache",
    "data",  # exclude from code zip
    "_backup",  # exclude from both
}


def should_exclude(path: Path, is_code_zip: bool = False, is_data_zip: bool = False) -> bool:
    """Check if path should be excluded from backup.
    
    Args:
        path: Path to check
        is_code_zip: If True, also exclude data/ directory (for code zip)
        is_data_zip: If True, exclude data/ml/ and data/raw/* except manifest.csv
    """
    # Always exclude _backup
    if "_backup" in path.parts:
        return True
    
    # Always exclude common patterns
    for exclude in (".venv", ".git", "__pycache__", ".pytest_cache", ".streamlit", "*.log"):
        if exclude in path.parts or path.name.endswith(".log"):
            return True
    
    # For code zip, exclude data/ directory
    if is_code_zip:
        if "data" in path.parts:
            try:
                relative = path.relative_to(ROOT)
                if relative.parts[0] == "data":
                    return True
            except ValueError:
                pass
    
    # For data zip, exclude temporary directories and raw ZIPs (keep only manifest.csv)
    if is_data_zip:
        try:
            relative = path.relative_to(ROOT)
            parts = relative.parts
            
            # Exclude data/ml/ (temporary ML data)
            if len(parts) >= 2 and parts[0] == "data" and parts[1] == "ml":
                return True
            
            # Exclude data/raw/* except manifest.csv
            if len(parts) >= 2 and parts[0] == "data" and parts[1] == "raw":
                # Allow only manifest.csv (data/raw/manifest.csv)
                if len(parts) == 3 and parts[1] == "raw" and parts[2] == "manifest.csv":
                    return False
                # Exclude everything else in raw/ (ZIP files, subdirectories)
                return True
            
        except ValueError:
            pass
    
    return False


def create_zip(zip_path: Path, source_paths: list[str | Path], is_code_zip: bool = False, is_data_zip: bool = False) -> int:
    """Create ZIP archive from source paths.
    
    Args:
        zip_path: Destination ZIP file path
        source_paths: List of paths to include (checked for existence)
        is_code_zip: If True, exclude data/ and _backup/ (for code zip)
        is_data_zip: If True, exclude data/ml/ and data/raw/* except manifest.csv
        
    Returns:
        Number of files added
    """
    # Ensure backup directory exists
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    
    files_added = 0
    
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zipf:
        for source in source_paths:
            source_path = ROOT / source
            
            # Check if path exists
            if not source_path.exists():
                print(f"[WARN] Skipping non-existent: {source}")
                continue
            
            # Add file or directory
            if source_path.is_file():
                # Add single file (check exclusions)
                if should_exclude(source_path, is_code_zip=is_code_zip, is_data_zip=is_data_zip):
                    continue
                
                # For data zip, preserve directory structure (e.g., data/raw/manifest.csv)
                if is_data_zip:
                    try:
                        arcname = source_path.relative_to(ROOT)
                    except ValueError:
                        arcname = source_path.name
                else:
                    arcname = source_path.name
                
                zipf.write(source_path, arcname)
                files_added += 1
            elif source_path.is_dir():
                # Add directory recursively
                dir_files = 0
                for item in source_path.rglob("*"):
                    if item.is_file():
                        # Check exclusions
                        if should_exclude(item, is_code_zip=is_code_zip, is_data_zip=is_data_zip):
                            continue
                        
                        # Calculate relative path for archive
                        try:
                            arcname = item.relative_to(ROOT)
                        except ValueError:
                            # If path is outside root, use just the name
                            arcname = item.name
                        
                        zipf.write(item, arcname)
                        files_added += 1
                        dir_files += 1
                if dir_files > 0:
                    print(f"  [OK] Added directory: {source} ({dir_files} files)")
                elif source_path.is_dir():
                    print(f"  [WARN] Directory empty or all files excluded: {source}")
    
    return files_added


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def main() -> None:
    """Create backup ZIP files."""
    print(f"[BACKUP] Creating backup ZIP files (version {VERSION}, date {TODAY})")
    print(f"   Root: {ROOT}")
    print(f"   Backup dir: {BACKUP_DIR}\n")
    
    # Filter code paths to only include existing ones
    existing_code_paths = [p for p in CODE_PATHS if (ROOT / p).exists()]
    
    if not existing_code_paths:
        print("[ERROR] No code paths found to backup!")
        sys.exit(1)
    
    print("[CODE ZIP] Creating code ZIP...")
    print(f"   Destination: {CODE_ZIP.name}")
    print(f"   Sources: {', '.join(existing_code_paths)}")
    files_in_code = create_zip(CODE_ZIP, existing_code_paths, is_code_zip=True)
    
    if CODE_ZIP.exists():
        code_size = CODE_ZIP.stat().st_size
        print(f"[OK] Code ZIP created: {CODE_ZIP.name}")
        print(f"   Files: {files_in_code}")
        print(f"   Size: {format_size(code_size)}\n")
    else:
        print("[ERROR] Code ZIP was not created!")
        sys.exit(1)
    
    # Check data paths exist
    existing_data_paths = [p for p in DATA_PATHS if (ROOT / p).exists()]
    
    if not existing_data_paths:
        print("[WARN] No data paths found to backup!")
        print("   Skipping data ZIP creation.")
    else:
        print("[DATA ZIP] Creating data ZIP...")
        print(f"   Destination: {DATA_ZIP.name}")
        print(f"   Sources: {', '.join(existing_data_paths)}")
        files_in_data = create_zip(DATA_ZIP, existing_data_paths, is_code_zip=False, is_data_zip=True)
        
        if DATA_ZIP.exists():
            data_size = DATA_ZIP.stat().st_size
            print(f"[OK] Data ZIP created: {DATA_ZIP.name}")
            print(f"   Files: {files_in_data}")
            print(f"   Size: {format_size(data_size)}\n")
        else:
            print("[ERROR] Data ZIP was not created!")
            sys.exit(1)
    
    # Verify ZIPs are not empty
    print("[VERIFY] Verifying ZIP files...")
    all_ok = True
    
    if CODE_ZIP.exists():
        code_size = CODE_ZIP.stat().st_size
        if code_size == 0:
            print(f"[ERROR] Code ZIP is empty: {CODE_ZIP.name}")
            all_ok = False
        else:
            print(f"[OK] Code ZIP OK: {CODE_ZIP.name} ({format_size(code_size)})")
    else:
        print(f"[ERROR] Code ZIP does not exist: {CODE_ZIP.name}")
        all_ok = False
    
    if DATA_ZIP.exists():
        data_size = DATA_ZIP.stat().st_size
        if data_size == 0:
            print(f"[ERROR] Data ZIP is empty: {DATA_ZIP.name}")
            all_ok = False
        else:
            print(f"[OK] Data ZIP OK: {DATA_ZIP.name} ({format_size(data_size)})")
    else:
        if existing_data_paths:
            print(f"[ERROR] Data ZIP does not exist: {DATA_ZIP.name}")
            all_ok = False
    
    if not all_ok:
        print("\n[ERROR] Backup verification failed!")
        sys.exit(1)
    
    print("\n[SUCCESS] Backup completed successfully!")
    print(f"   Code ZIP: {CODE_ZIP.name}")
    if DATA_ZIP.exists():
        print(f"   Data ZIP: {DATA_ZIP.name}")


if __name__ == "__main__":
    main()
