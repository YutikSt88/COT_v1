from __future__ import annotations

import argparse
from pathlib import Path

import yaml
import pandas as pd

from src.common.paths import ProjectPaths
from src.common.logging import setup_logging
from src.common.markets_sync import sync_markets_from_contracts_meta, _clean_contract_code
from src.normalize.cot_parser import parse_deacot_zip
from src.normalize.qa_checks import (
    qa_uniqueness,
    qa_missing_dates,
    qa_open_interest,
    qa_comm_nc_mapping,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logger = setup_logging(args.log_level)
    paths = ProjectPaths(Path(args.root).resolve())

    sync_markets_from_contracts_meta(paths)

    cfg = yaml.safe_load((paths.configs / "markets.yaml").read_text(encoding="utf-8"))
    dataset = cfg["source"]["dataset"]

    # Read manifest to get latest OK snapshots per year
    from src.ingest.manifest import load_manifest
    manifest = load_manifest(paths.raw / "manifest.csv")
    ok_manifest = manifest[(manifest["dataset"] == dataset) & (manifest["status"] == "OK")].copy()
    
    if ok_manifest.empty:
        raise SystemExit(f"No OK snapshots found in manifest for dataset={dataset}")
    
    # Get latest snapshot per year
    ok_manifest["_downloaded_at_utc_parsed"] = pd.to_datetime(
        ok_manifest["downloaded_at_utc"], errors="coerce", utc=True
    )
    snapshots = []
    for year, group in ok_manifest.groupby("year"):
        parsed = group["_downloaded_at_utc_parsed"]
        if parsed.notna().any():
            latest = group.loc[parsed.idxmax()]
        else:
            latest = group.iloc[-1]
        snapshots.append({
            "year": year,
            "raw_path": paths.root / latest["raw_path"]
        })
    
    if not snapshots:
        raise SystemExit(f"No snapshots found for dataset={dataset}")

    frames = []
    
    # Build contract_code -> market_key mapping from config
    contract_to_market = {}
    for m in cfg["markets"]:
        market_key = m.get("market_key") or m.get("key")
        contract_code = _clean_contract_code(m.get("contract_code"))
        if market_key and contract_code:
            contract_to_market[contract_code] = market_key

    for snapshot in snapshots:
        zp = snapshot["raw_path"]
        year = snapshot["year"]
        
        if not zp.exists():
            logger.warning(f"[normalize] snapshot not found: {zp}, skipping")
            continue
        
        try:
            parsed = parse_deacot_zip(zp, year)
            df = parsed.df
        except Exception as e:
            logger.error(f"[normalize] failed to parse {zp.name}: {e}")
            continue

        def pick_first(cols: list[str]) -> str | None:
            for c in cols:
                if c in df.columns:
                    return c
            return None

        # Required columns (support both legacy ZIP and Excel-style headers)
        col_report_date = pick_first(
            [
                "Report_Date_as_MM_DD_YYYY",
                "As of Date in Form YYYY-MM-DD",
                "As of Date in Form YYMMDD",
            ]
        )
        col_contract_code = pick_first(
            ["CFTC_Contract_Market_Code", "CFTC Contract Market Code"]
        )
        col_oi = pick_first(["Open_Interest_All", "Open Interest (All)"])
        col_nc_long = pick_first(
            ["NonComm_Positions_Long_All", "Noncommercial Positions-Long (All)"]
        )
        col_nc_short = pick_first(
            ["NonComm_Positions_Short_All", "Noncommercial Positions-Short (All)"]
        )
        col_comm_long = pick_first(
            ["Comm_Positions_Long_All", "Commercial Positions-Long (All)"]
        )
        col_comm_short = pick_first(
            ["Comm_Positions_Short_All", "Commercial Positions-Short (All)"]
        )
        col_nr_long = pick_first(
            ["NonRept_Positions_Long_All", "Nonreportable Positions-Long (All)"]
        )
        col_nr_short = pick_first(
            ["NonRept_Positions_Short_All", "Nonreportable Positions-Short (All)"]
        )

        required_cols = {
            "report_date": col_report_date,
            "contract_code": col_contract_code,
            "open_interest": col_oi,
            "nc_long": col_nc_long,
            "nc_short": col_nc_short,
            "comm_long": col_comm_long,
            "comm_short": col_comm_short,
            "nr_long": col_nr_long,
            "nr_short": col_nr_short,
        }
        missing_cols = [k for k, v in required_cols.items() if v is None]
        if missing_cols:
            raise SystemExit(
                f"Missing required columns in {zp.name}: {', '.join(missing_cols)}"
            )

        # Normalize contract codes (keep letters/+ if present)
        code_raw = df[col_contract_code].astype(str).str.strip()
        code_raw = code_raw.str.replace(r"\.0$", "", regex=True)
        code_norm = code_raw.where(~code_raw.str.isdigit(), code_raw.str.zfill(6))
        df[col_contract_code] = code_norm

        # Filter to markets in config
        allowed_codes = set(contract_to_market.keys())
        df = df[df[col_contract_code].isin(allowed_codes)].copy()
        
        if df.empty:
            logger.warning(f"[normalize] {zp.name}: no rows after contract-code filter")
            continue

        # Parse report_date based on column format
        if col_report_date == "Report_Date_as_MM_DD_YYYY":
            report_date = pd.to_datetime(
                df[col_report_date], format="%m/%d/%Y", errors="coerce"
            )
        elif col_report_date == "As of Date in Form YYYY-MM-DD":
            report_date = pd.to_datetime(
                df[col_report_date], format="%Y-%m-%d", errors="coerce"
            )
        else:
            report_date = pd.to_datetime(
                df[col_report_date].astype(str), format="%y%m%d", errors="coerce"
            )
        if report_date.isna().all():
            report_date = pd.to_datetime(df[col_report_date], errors="coerce")

        out = pd.DataFrame(
            {
                "contract_code": df[col_contract_code],
                "report_date": report_date.dt.tz_localize(None),
                "open_interest_all": pd.to_numeric(df[col_oi], errors="coerce"),
                "nc_long": pd.to_numeric(df[col_nc_long], errors="coerce"),
                "nc_short": pd.to_numeric(df[col_nc_short], errors="coerce"),
                "comm_long": pd.to_numeric(df[col_comm_long], errors="coerce"),
                "comm_short": pd.to_numeric(df[col_comm_short], errors="coerce"),
                "nr_long": pd.to_numeric(df[col_nr_long], errors="coerce"),
                "nr_short": pd.to_numeric(df[col_nr_short], errors="coerce"),
                "raw_source_year": year,
                "raw_source_file": parsed.source_file,
            }
        )

        out["market_key"] = out["contract_code"].map(contract_to_market)
        out = out[out["market_key"].notna()].copy()

        # Fill missing numeric values with 0 (requested behavior)
        numeric_cols = [
            "open_interest_all",
            "nc_long",
            "nc_short",
            "comm_long",
            "comm_short",
            "nr_long",
            "nr_short",
        ]
        out[numeric_cols] = out[numeric_cols].fillna(0.0)

        # Merge duplicates by summing numeric values
        group_keys = ["market_key", "report_date", "contract_code"]
        agg_cols = {c: "sum" for c in numeric_cols}
        agg_cols.update({"raw_source_year": "first", "raw_source_file": "first"})
        out = out.groupby(group_keys, dropna=False, as_index=False).agg(agg_cols)

        # Calculate net positions after aggregation
        out["comm_net"] = out["comm_long"] - out["comm_short"]
        out["nc_net"] = out["nc_long"] - out["nc_short"]
        out["nr_net"] = out["nr_long"] - out["nr_short"]

        frames.append(out)

    if not frames:
        raise SystemExit("No rows produced during normalization (frames empty). Check raw files & filters.")

    canonical = pd.concat(frames, ignore_index=True)
    canonical = canonical.sort_values(["market_key", "report_date"]).reset_index(drop=True)

    # QA
    errors = []
    warnings = []
    errs, warns = qa_uniqueness(canonical)
    errors += errs
    warnings += warns
    errs, warns = qa_missing_dates(canonical)
    errors += errs
    warnings += warns
    errs, warns = qa_open_interest(canonical)
    errors += errs
    warnings += warns
    errs, warns = qa_comm_nc_mapping(canonical)
    errors += errs
    warnings += warns

    qa_path = paths.canonical / "qa_report.txt"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    if errors or warnings:
        lines = []
        lines += [f"ERROR: {e}" for e in errors]
        lines += [f"WARN: {w}" for w in warnings]
        qa_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        qa_path.write_text("OK", encoding="utf-8")

    if errors:
        logger.error("[normalize] QA FAILED:\n" + "\n".join(errors))
        raise SystemExit("Normalization QA failed. See data/canonical/qa_report.txt")

    # Write canonical_full (used by compute)
    out_path = paths.canonical / "cot_weekly_canonical_full.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canonical.to_parquet(out_path, index=False)
    logger.info(f"[normalize] wrote {out_path} rows={len(canonical)}")


if __name__ == "__main__":
    main()
