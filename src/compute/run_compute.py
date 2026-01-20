"""CLI entrypoint for compute module."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml
import pandas as pd

from src.common.paths import ProjectPaths
from src.common.logging import setup_logging
from src.common.markets_sync import sync_markets_from_contracts_meta, _clean_contract_code
from src.compute.build_positions import build_positions
from src.compute.build_changes import build_changes
from src.compute.build_flows import build_flows_weekly
from src.compute.build_rolling import build_rolling
from src.compute.build_extremes import build_extremes
from src.compute.build_moves import build_moves_weekly
from src.compute.build_wide_metrics import build_wide_metrics
from src.compute.build_market_radar import build_market_radar_latest
from src.compute.build_market_positioning import build_market_positioning_latest
from src.compute.validations import (
    validate_canonical_exists,
    validate_required_columns,
    validate_output_rows,
    validate_pos_all,
    validate_pos_5y,
    validate_max_min_all,
    validate_max_min_5y,
    validate_chg_1w,
    validate_oi_metrics,
    warn_missing_weeks,
    warn_negative_open_interest,
    warn_duplicate_keys,
    warn_oi_missing_mid_history,
    info_oi_chg_pct_threshold,
    warn_oi_chg_pct_threshold,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    
    logger = setup_logging(args.log_level)
    
    # Debug: check sys.path to detect shadowing
    logger.info(f"[compute][debug] sys.path[0:5]={sys.path[0:5]}")
    
    paths = ProjectPaths(Path(args.root).resolve())

    sync_markets_from_contracts_meta(paths)
    
    # Read canonical_full parquet
    canonical_path = paths.canonical / "cot_weekly_canonical_full.parquet"
    validate_canonical_exists(str(canonical_path))
    
    logger.info(f"[compute] reading canonical: {canonical_path}")
    canonical = pd.read_parquet(canonical_path)
    logger.info(f"[compute] canonical rows: {len(canonical)}, cols: {len(canonical.columns)}")
    
    # Validate canonical has required columns
    required_cols = [
        "market_key",
        "report_date",
        "contract_code",
        "open_interest_all",
        "comm_long",
        "comm_short",
        "nc_long",
        "nc_short",
        "nr_long",
        "nr_short",
    ]
    col_errors = validate_required_columns(canonical, required_cols)
    if col_errors:
        for err in col_errors:
            logger.error(f"[compute] {err}")
        raise SystemExit("Canonical missing required columns")
    
    # Read markets.yaml
    markets_path = paths.configs / "markets.yaml"
    logger.info(f"[compute] reading markets config: {markets_path}")
    cfg = yaml.safe_load(markets_path.read_text(encoding="utf-8"))
    
    # Build market mappings and allowed pairs
    market_to_category = {}
    market_to_contract = {}
    market_to_name = {}
    allowed_pairs: set[tuple[str, str]] = set()
    for m in cfg["markets"]:
        market_key = m.get("market_key") or m.get("key")
        category = m.get("category")
        display_name = m.get("display_name")
        contract_code = _clean_contract_code(m.get("contract_code"))
        if market_key and contract_code:
            if category:
                market_to_category[str(market_key)] = category
            market_to_contract[str(market_key)] = contract_code
            market_to_name[str(market_key)] = display_name or str(market_key)
            allowed_pairs.add((str(market_key), contract_code))
    
    logger.info(f"[compute] loaded {len(market_to_category)} markets from config")

    # Filter canonical by (market_key, contract_code) from markets.yaml
    canonical["market_key"] = canonical["market_key"].astype(str)
    canonical["contract_code"] = canonical["contract_code"].map(_clean_contract_code)
    canonical_idx = pd.MultiIndex.from_arrays(
        [canonical["market_key"], canonical["contract_code"]]
    )
    allowed_idx = pd.MultiIndex.from_tuples(allowed_pairs, names=["market_key", "contract_code"])
    before_rows = len(canonical)
    canonical = canonical[canonical_idx.isin(allowed_idx)].copy()
    after_rows = len(canonical)
    logger.info(f"[compute] canonical filter by markets.yaml: {before_rows} -> {after_rows} rows")
    if canonical.empty:
        raise SystemExit("Canonical has 0 rows after markets.yaml filter (market_key + contract_code).")

    # Check canonical uniqueness after filtering
    dup_triplet = canonical.duplicated(subset=["market_key", "report_date", "contract_code"]).sum()
    if dup_triplet > 0:
        raise SystemExit(
            f"Canonical has {dup_triplet} duplicate (market_key, report_date, contract_code) rows after filter"
        )
    dup_pair = canonical.duplicated(subset=["market_key", "report_date"]).sum()
    if dup_pair > 0:
        raise SystemExit(
            f"Canonical has {dup_pair} duplicate (market_key, report_date) rows after filter"
        )
    
    # Prepare output directory
    output_dir = paths.data / "compute"
    output_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    infos: list[str] = []

    # QA warnings on canonical (post-filter)
    warnings.extend(warn_negative_open_interest(canonical))
    
    # Build semantic tables (positions, changes, rolling, extremes)
    logger.info("[compute] building semantic tables...")
    
    # Step 1: Build positions table
    logger.info("[compute] step 1/4: building positions...")
    positions = build_positions(canonical)
    
    # Validate positions
    if len(positions) == 0:
        raise SystemExit("Positions table is empty")
    if "market_key" not in positions.columns or "report_date" not in positions.columns:
        raise SystemExit("Positions table missing required columns: market_key, report_date")
    
    warnings.extend(warn_missing_weeks(positions))
    
    # Write positions
    positions_path = output_dir / "positions_weekly.parquet"
    positions.to_parquet(positions_path, index=False)
    logger.info(f"[compute] wrote {positions_path} rows={len(positions)}")
    
    # Step 2: Build changes table
    logger.info("[compute] step 2/4: building changes...")
    changes = build_changes(positions)
    
    # Validate changes
    if len(changes) == 0:
        raise SystemExit("Changes table is empty")
    if "market_key" not in changes.columns or "report_date" not in changes.columns:
        raise SystemExit("Changes table missing required columns: market_key, report_date")
    
    # Write changes
    changes_path = output_dir / "changes_weekly.parquet"
    changes.to_parquet(changes_path, index=False)
    logger.info(f"[compute] wrote {changes_path} rows={len(changes)}")
    
    # Step 2.5: Build flows table
    logger.info("[compute] step 2.5/6: building flows...")
    flows = build_flows_weekly(changes)
    
    # Validate flows
    if len(flows) == 0:
        raise SystemExit("Flows table is empty")
    if "market_key" not in flows.columns or "report_date" not in flows.columns:
        raise SystemExit("Flows table missing required columns: market_key, report_date")
    
    # Write flows
    flows_path = output_dir / "flows_weekly.parquet"
    flows.to_parquet(flows_path, index=False)
    logger.info(f"[compute] wrote {flows_path} rows={len(flows)}")
    
    # Step 3: Build rolling table
    logger.info("[compute] step 3/4: building rolling...")
    rolling = build_rolling(positions)
    
    # Validate rolling
    if len(rolling) == 0:
        raise SystemExit("Rolling table is empty")
    if "market_key" not in rolling.columns or "report_date" not in rolling.columns:
        raise SystemExit("Rolling table missing required columns: market_key, report_date")
    
    # Write rolling
    rolling_path = output_dir / "rolling_weekly.parquet"
    rolling.to_parquet(rolling_path, index=False)
    logger.info(f"[compute] wrote {rolling_path} rows={len(rolling)}")
    
    # Step 4: Build extremes table
    logger.info("[compute] step 4/4: building extremes...")
    extremes = build_extremes(positions)
    
    # Validate extremes
    if len(extremes) == 0:
        raise SystemExit("Extremes table is empty")
    if "market_key" not in extremes.columns or "report_date" not in extremes.columns:
        raise SystemExit("Extremes table missing required columns: market_key, report_date")
    
    # Write extremes
    extremes_path = output_dir / "extremes_weekly.parquet"
    extremes.to_parquet(extremes_path, index=False)
    logger.info(f"[compute] wrote {extremes_path} rows={len(extremes)}")
    
    # Step 6: Build moves table
    logger.info("[compute] step 6/7: building moves...")
    moves = build_moves_weekly(changes)
    
    # Validate moves
    if len(moves) == 0:
        raise SystemExit("Moves table is empty")
    if "market_key" not in moves.columns or "report_date" not in moves.columns:
        raise SystemExit("Moves table missing required columns: market_key, report_date")
    
    # Write moves
    moves_path = output_dir / "moves_weekly.parquet"
    moves.to_parquet(moves_path, index=False)
    logger.info(f"[compute] wrote {moves_path} rows={len(moves)}")
    
    logger.info("[compute] semantic tables DONE")
    
    # Build wide metrics_weekly as join of semantic tables
    logger.info("[compute] building wide metrics_weekly as join of semantic tables...")
    metrics = build_wide_metrics(
        positions=positions,
        changes=changes,
        flows=flows,
        rolling=rolling,
        extremes=extremes,
        moves=moves,
        canonical=canonical,
        market_to_category=market_to_category,
        market_to_contract=market_to_contract,
    )
    
    # Validate metrics
    errors = []
    
    # Check output rows
    errors.extend(validate_output_rows(metrics))
    
    # Warn on duplicate keys (do not stop compute here)
    warnings.extend(warn_duplicate_keys(metrics, ["market_key", "report_date"]))
    
    # Check 1:1 with positions (must have same row count)
    if len(metrics) != len(positions):
        errors.append(
            f"Metrics row count ({len(metrics)}) != positions row count ({len(positions)}). "
            f"Expected 1:1 join."
        )
    
    # Check pos_all (no NaN, in [0, 1])
    errors.extend(validate_pos_all(metrics))
    
    # Check pos_5y (NaN allowed, non-NaN in [0, 1])
    errors.extend(validate_pos_5y(metrics))
    
    # Check max != min for ALL window
    errors.extend(validate_max_min_all(metrics))
    
    # Check max != min for 5Y window (allow min==max for early data)
    errors.extend(validate_max_min_5y(metrics))
    
    # Check WoW change columns (chg_1w) - only basic columns from semantic tables
    errors.extend(validate_chg_1w(metrics))
    
    # Check basic net metrics (nc_net, comm_net exist)
    # Note: spec_vs_hedge_net_chg_1w and other derived metrics are optional
    if "nc_net" not in metrics.columns or "comm_net" not in metrics.columns:
        errors.append("Missing required net metrics columns: nc_net, comm_net")
    
    # Check basic OI (open_interest exists)
    # Note: open_interest_chg_1w and OI extremes are optional
    if "open_interest" not in metrics.columns:
        errors.append("Missing required OI column: open_interest")
    
    # Skip exposure_shares validation - these columns are not in semantic tables
    # If needed, they should be added to positions or changes tables
    
    # Validate OI metrics (full checks)
    errors.extend(validate_oi_metrics(metrics))

    # OI warnings/infos
    warnings.extend(warn_oi_missing_mid_history(metrics))
    infos.extend(info_oi_chg_pct_threshold(metrics, 0.35))
    warnings.extend(warn_oi_chg_pct_threshold(metrics, 0.50))
    
    logger.info(f"[compute] metrics rows: {len(metrics)}, cols: {len(metrics.columns)}")
    
    # Guard check: ensure comm_* and nc_* are not identical (mapping bug detection)
    if len(metrics) > 0:
        same_long = (metrics["nc_long"] == metrics["comm_long"]).fillna(False)
        same_short = (metrics["nc_short"] == metrics["comm_short"]).fillna(False)
        same_net = (metrics["nc_net"] == metrics["comm_net"]).fillna(False)
        same_all = same_long & same_short & same_net
        same_pct = same_all.mean()
        
        if same_pct > 0.999:
            errors.append(
                f"Invalid metrics: comm_* equals nc_* for {same_pct*100:.1f}% of rows (mapping bug). "
                f"Expected comm_* and nc_* to represent different player groups (Commercials vs Non-Commercials)."
            )
        logger.info(f"[compute] validation: comm_* vs nc_* same_pct={same_pct:.4f} (expected < 0.999)")
    
    # Write QA report (errors + warnings + infos)
    qa_path = output_dir / "qa_report.txt"
    if errors or warnings or infos:
        lines = []
        lines += [f"ERROR: {e}" for e in errors]
        lines += [f"INFO: {i}" for i in infos]
        lines += [f"WARN: {w}" for w in warnings]
        qa_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        qa_path.write_text("OK", encoding="utf-8")
    
    if warnings:
        logger.warning("[compute] QA WARNINGS:\n" + "\n".join(warnings))

    if infos:
        logger.info("[compute] QA INFOS:\n" + "\n".join(infos))
    
    if errors:
        for err in errors:
            logger.error(f"[compute] VALIDATION FAILED: {err}")
        raise SystemExit("Compute validations failed")
    
    # Write metrics_weekly output (wide view for UI)
    output_path = output_dir / "metrics_weekly.parquet"
    metrics.to_parquet(output_path, index=False)
    logger.info(f"[compute] wrote {output_path} rows={len(metrics)}")

    # Write market radar latest view
    radar = build_market_radar_latest(metrics, market_to_name)
    radar_path = output_dir / "market_radar_latest.parquet"
    radar.to_parquet(radar_path, index=False)
    logger.info(f"[compute] wrote {radar_path} rows={len(radar)}")

    positioning = build_market_positioning_latest(metrics, market_to_name)
    positioning_path = output_dir / "market_positioning_latest.parquet"
    positioning.to_parquet(positioning_path, index=False)
    logger.info(f"[compute] wrote {positioning_path} rows={len(positioning)}")
    
    logger.info("[compute] DONE")


if __name__ == "__main__":
    main()
