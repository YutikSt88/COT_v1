"""Parser for CFTC COT ZIP files."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import zipfile
import pandas as pd


@dataclass
class ParseResult:
    df: pd.DataFrame
    source_file: str


def parse_deacot_zip(zip_path: Path, year: int) -> ParseResult:
    """
    Parse CFTC COT ZIP file and extract annual.txt as DataFrame.
    
    Args:
        zip_path: Path to ZIP file
        year: Year for the data
        
    Returns:
        ParseResult with df (DataFrame) and source_file (str)
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Look for annual.txt in the ZIP
        annual_files = [f for f in zf.namelist() if "annual" in f.lower() and f.endswith(".txt")]
        if not annual_files:
            raise ValueError(f"No annual.txt found in {zip_path.name}")
        
        # Prefer file name containing the requested year if possible
        year_str = str(year)
        year_matches = [f for f in annual_files if year_str in f]
        source_file = year_matches[0] if year_matches else annual_files[0]
        with zf.open(source_file) as f:
            # Read CSV from annual.txt
            try:
                df = pd.read_csv(f, encoding="utf-8", low_memory=False)
            except UnicodeDecodeError:
                f.seek(0)
                df = pd.read_csv(f, encoding="latin-1", low_memory=False)
    
    return ParseResult(df=df, source_file=source_file)
