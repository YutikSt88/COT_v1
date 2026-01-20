"""Export metrics_weekly.parquet to JSON format for ML training."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


def main() -> None:
    """Export metrics_weekly.parquet to JSON."""
    parser = argparse.ArgumentParser(description="Export metrics_weekly.parquet to JSON")
    parser.add_argument("--root", type=str, default=".", help="Project root directory")
    parser.add_argument(
        "--input",
        type=str,
        default="data/compute/metrics_weekly.parquet",
        help="Input parquet file path (relative to root)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="data/ml/raw",
        help="Output directory (relative to root)",
    )
    
    args = parser.parse_args()
    
    root = Path(args.root).resolve()
    input_path = root / args.input
    out_dir = root / args.out_dir
    
    # Validate input file
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Create output directory if missing
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Read parquet
    df = pd.read_parquet(input_path)
    
    # Convert report_date to ISO string if present
    if "report_date" in df.columns:
        def format_date(x):
            """Convert date to ISO string format."""
            if pd.isna(x):
                return None
            if hasattr(x, "strftime"):
                return x.strftime("%Y-%m-%d")
            if isinstance(x, str):
                return x
            # Try to convert to datetime and format
            try:
                dt = pd.to_datetime(x)
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                return str(x)
        
        df["report_date"] = df["report_date"].apply(format_date)
    
    # Convert to records (list of dicts)
    records = df.to_dict(orient="records")
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"metrics_weekly_{timestamp}.json"
    output_path = out_dir / output_filename
    
    # Write JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    # Print results
    print(f"✓ Exported {len(records)} rows to: {output_path}")
    print(f"  Output directory: {out_dir}")
    print(f"  Columns: {len(df.columns)}")


if __name__ == "__main__":
    main()
