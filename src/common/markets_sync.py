"""Sync markets.yaml from contracts_meta.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.common.paths import ProjectPaths


def _clean_contract_code(value: Any) -> str:
    code = "" if value is None else str(value).strip()
    if code.endswith(".0"):
        code = code[:-2]
    if code.isdigit():
        return code.zfill(6)
    return code


def sync_markets_from_contracts_meta(paths: ProjectPaths) -> None:
    """
    Sync configs/markets.yaml based on configs/contracts_meta.yaml.

    Only contracts with enabled=true are included.
    """
    contracts_path = paths.configs / "contracts_meta.yaml"
    markets_path = paths.configs / "markets.yaml"

    if not contracts_path.exists():
        return

    contracts_cfg = yaml.safe_load(contracts_path.read_text(encoding="utf-8")) or {}
    contracts = contracts_cfg.get("contracts", [])

    enabled_contracts = [c for c in contracts if c.get("enabled") is True]

    # Preserve source block from existing markets.yaml when possible.
    source_block = None
    if markets_path.exists():
        existing = yaml.safe_load(markets_path.read_text(encoding="utf-8")) or {}
        source_block = existing.get("source")

    if source_block is None:
        source_block = {
            "dataset": "legacy_futures_only",
            "cftc_historical_zip_url_template": "https://www.cftc.gov/files/dea/history/deacot{year}.zip",
        }

    markets = []
    seen = set()
    for c in enabled_contracts:
        market_key = c.get("symbol") or c.get("market_key") or c.get("key")
        contract_code = _clean_contract_code(c.get("contract_code"))
        category = c.get("category")
        if not market_key or not contract_code:
            continue
        key = (market_key, contract_code)
        if key in seen:
            continue
        seen.add(key)
        markets.append(
            {
                "market_key": str(market_key).strip(),
                "contract_code": contract_code,
                "category": str(category).strip() if category else None,
            }
        )

    # Remove None categories to keep output clean.
    for m in markets:
        if m.get("category") is None:
            m.pop("category", None)

    out = {
        "source": source_block,
        "markets": markets,
    }

    markets_path.write_text(
        yaml.safe_dump(out, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
