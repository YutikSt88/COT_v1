"""FastAPI app for COT frontend."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.common.paths import ProjectPaths

app = FastAPI(title="COT API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_radar_df() -> pd.DataFrame:
    paths = ProjectPaths(_repo_root())
    radar_path = paths.data / "compute" / "market_radar_latest.parquet"
    if not radar_path.exists():
        raise HTTPException(status_code=404, detail="market_radar_latest.parquet not found")

    df = pd.read_parquet(radar_path)
    if df.empty:
        return df

    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        latest = df["report_date"].max()
        df = df[df["report_date"] == latest].copy()

    return df


def _load_metrics_df() -> pd.DataFrame:
    paths = ProjectPaths(_repo_root())
    metrics_path = paths.data / "compute" / "metrics_weekly.parquet"
    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="metrics_weekly.parquet not found")
    df = pd.read_parquet(metrics_path)
    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    return df


def _apply_range(df: pd.DataFrame, range_code: str) -> pd.DataFrame:
    if "report_date" not in df.columns or df.empty:
        return df

    out = df.copy()
    out = out[out["report_date"].notna()].copy()
    if out.empty:
        return out

    range_norm = (range_code or "12W").upper()
    if range_norm == "ALL":
        return out

    latest = out["report_date"].max()
    if pd.isna(latest):
        return out

    if range_norm == "4W":
        return out[out["report_date"] >= latest - pd.Timedelta(days=28)]
    if range_norm == "12W":
        return out[out["report_date"] >= latest - pd.Timedelta(days=84)]
    if range_norm == "1Y":
        return out[out["report_date"] >= latest - pd.Timedelta(days=365)]
    if range_norm == "YTD":
        year_start = pd.Timestamp(year=latest.year, month=1, day=1)
        return out[out["report_date"] >= year_start]

    return out


def _compute_signal_state(row: pd.Series) -> str:
    sig = pd.to_numeric(row.get("cot_traffic_signal"), errors="coerce")
    funds_z = pd.to_numeric(row.get("net_z_52w_funds"), errors="coerce")
    oi_risk = str(row.get("oi_risk_level") or "")
    if (pd.notna(funds_z) and abs(float(funds_z)) >= 2.0) or oi_risk == "High":
        return "extreme"
    if pd.notna(sig) and sig >= 1:
        return "bullish"
    if pd.notna(sig) and sig <= -1:
        return "bearish"
    return "neutral"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/signals")
def get_signals(
    signal: Literal["all", "extreme", "bullish", "bearish", "neutral"] = "all",
    category: str = Query(default="all"),
    conflict: Literal["all", "High", "Medium", "Low"] = "all",
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict:
    df = _load_radar_df()
    if df.empty:
        return {"items": [], "total": 0, "latest_report_date": None}

    df = df.copy()
    df["signal_state"] = df.apply(_compute_signal_state, axis=1)
    df["signal_abs"] = pd.to_numeric(df.get("cot_traffic_signal"), errors="coerce").abs()

    if category != "all":
        df = df[df["category"].astype(str).str.lower() == category.lower()]

    if signal != "all":
        df = df[df["signal_state"] == signal]

    if conflict != "all":
        df = df[df["conflict_level"] == conflict]

    df = df.sort_values(["signal_abs", "hot_score"], ascending=False, na_position="last")

    latest_report_date = None
    if "report_date" in df.columns and not df["report_date"].isna().all():
        latest_report_date = pd.to_datetime(df["report_date"].max()).strftime("%Y-%m-%d")

    keep_cols = [
        "market_id",
        "market_name",
        "category",
        "signal_state",
        "cot_traffic_signal",
        "hot_score",
        "conflict_level",
        "oi_risk_level",
        "net_z_52w_funds",
        "open_interest_chg_1w_pct",
        "is_hot",
    ]
    out = df[[c for c in keep_cols if c in df.columns]].head(limit).copy()
    out = out.where(pd.notna(out), None)

    return {
        "items": out.to_dict(orient="records"),
        "total": int(len(df)),
        "latest_report_date": latest_report_date,
    }


@app.get("/api/markets")
def get_markets() -> dict:
    df = _load_radar_df()
    if df.empty:
        return {"items": []}
    cols = [c for c in ["market_id", "market_name", "category"] if c in df.columns]
    out = df[cols].drop_duplicates().sort_values(["category", "market_name"], na_position="last")
    out = out.where(pd.notna(out), None)
    return {"items": out.to_dict(orient="records")}


@app.get("/api/dashboard")
def get_dashboard(
    signal: Literal["all", "extreme", "bullish", "bearish", "neutral"] = "all",
    category: str = Query(default="all"),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    df = _load_radar_df()
    if df.empty:
        return {
            "summary": {"bullish": 0, "bearish": 0, "extreme": 0, "neutral": 0},
            "items": [],
            "total": 0,
            "latest_report_date": None,
            "categories": [],
        }

    df = df.copy()
    df["signal_state"] = df.apply(_compute_signal_state, axis=1)
    df["signal_abs"] = pd.to_numeric(df.get("cot_traffic_signal"), errors="coerce").abs()

    categories = sorted(df["category"].dropna().astype(str).unique().tolist()) if "category" in df.columns else []

    if category != "all":
        df = df[df["category"].astype(str).str.lower() == category.lower()]
    if signal != "all":
        df = df[df["signal_state"] == signal]

    summary = {
        "bullish": int((df["signal_state"] == "bullish").sum()),
        "bearish": int((df["signal_state"] == "bearish").sum()),
        "extreme": int((df["signal_state"] == "extreme").sum()),
        "neutral": int((df["signal_state"] == "neutral").sum()),
    }

    df = df.sort_values(["signal_abs", "hot_score"], ascending=False, na_position="last")
    latest_report_date = None
    if "report_date" in df.columns and not df["report_date"].isna().all():
        latest_report_date = pd.to_datetime(df["report_date"].max()).strftime("%Y-%m-%d")

    keep_cols = [
        "market_id",
        "market_name",
        "category",
        "signal_state",
        "cot_traffic_signal",
        "hot_score",
        "conflict_level",
        "net_z_52w_funds",
        "open_interest_chg_1w_pct",
        "is_hot",
    ]
    out = df[[c for c in keep_cols if c in df.columns]].head(limit).copy()
    out = out.where(pd.notna(out), None)

    return {
        "summary": summary,
        "items": out.to_dict(orient="records"),
        "total": int(len(df)),
        "latest_report_date": latest_report_date,
        "categories": categories,
    }


@app.get("/api/market-detail")
def get_market_detail(
    market_id: str = Query(..., min_length=1),
    range: Literal["4W", "12W", "YTD", "1Y", "ALL"] = "12W",
) -> dict:
    df = _load_metrics_df()
    market = str(market_id).strip()
    m = df[df["market_key"].astype(str) == market].copy()
    if m.empty:
        raise HTTPException(status_code=404, detail=f"Market not found: {market}")

    m = m.sort_values("report_date")
    m_range = _apply_range(m, range)
    if m_range.empty:
        m_range = m.tail(1).copy()

    latest_row = m.iloc[-1]
    latest = {
        "market_id": market,
        "report_date": pd.to_datetime(latest_row.get("report_date")).strftime("%Y-%m-%d")
        if pd.notna(latest_row.get("report_date"))
        else None,
        "signal_state": _compute_signal_state(latest_row),
        "nc_net": float(latest_row.get("nc_net")) if pd.notna(latest_row.get("nc_net")) else None,
        "comm_net": float(latest_row.get("comm_net")) if pd.notna(latest_row.get("comm_net")) else None,
        "net_z_52w_funds": float(latest_row.get("net_z_52w_funds"))
        if pd.notna(latest_row.get("net_z_52w_funds"))
        else None,
        "net_z_52w_commercials": float(latest_row.get("net_z_52w_commercials"))
        if pd.notna(latest_row.get("net_z_52w_commercials"))
        else None,
        "open_interest": float(latest_row.get("open_interest")) if pd.notna(latest_row.get("open_interest")) else None,
        "open_interest_chg_1w": float(latest_row.get("open_interest_chg_1w"))
        if pd.notna(latest_row.get("open_interest_chg_1w"))
        else None,
    }

    series_cols = [
        "report_date",
        "nc_net",
        "comm_net",
        "open_interest",
        "net_z_52w_funds",
        "net_z_52w_commercials",
        "nc_net_chg_1w",
        "comm_net_chg_1w",
        "open_interest_chg_1w_pct",
    ]
    keep = [c for c in series_cols if c in m_range.columns]
    series = m_range[keep].copy()
    if "report_date" in series.columns:
        series["report_date"] = pd.to_datetime(series["report_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    series = series.where(pd.notna(series), None)

    # Recent rows for table (always from full history, newest first)
    table_cols = [
        "report_date",
        "nc_net",
        "comm_net",
        "net_z_52w_funds",
        "net_z_52w_commercials",
        "open_interest",
        "open_interest_chg_1w_pct",
    ]
    keep_tbl = [c for c in table_cols if c in m.columns]
    table_df = m[keep_tbl].sort_values("report_date", ascending=False).head(30).copy()
    if "report_date" in table_df.columns:
        table_df["report_date"] = pd.to_datetime(table_df["report_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    table_df = table_df.where(pd.notna(table_df), None)

    return {
        "latest": latest,
        "series": series.to_dict(orient="records"),
        "table": table_df.to_dict(orient="records"),
        "range": range,
        "points": int(len(series)),
    }
