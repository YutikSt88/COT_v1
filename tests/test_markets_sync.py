"""Tests for contracts_meta -> markets.yaml sync."""

from __future__ import annotations

from pathlib import Path
import yaml

from src.common.paths import ProjectPaths
from src.common.markets_sync import sync_markets_from_contracts_meta


def test_sync_markets_from_contracts_meta(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)

    contracts_meta = {
        "contracts": [
            {
                "contract_code": "099741",
                "symbol": "EUR",
                "category": "FX",
                "enabled": True,
            },
            {
                "contract_code": "000000",
                "symbol": "IGNORED",
                "category": "FX",
                "enabled": False,
            },
        ]
    }
    (configs_dir / "contracts_meta.yaml").write_text(
        yaml.safe_dump(contracts_meta, sort_keys=False),
        encoding="utf-8",
    )

    markets_seed = {
        "source": {
            "dataset": "legacy_futures_only",
            "cftc_historical_zip_url_template": "https://example.test/deacot{year}.zip",
        },
        "markets": [],
    }
    (configs_dir / "markets.yaml").write_text(
        yaml.safe_dump(markets_seed, sort_keys=False),
        encoding="utf-8",
    )

    paths = ProjectPaths(tmp_path)
    sync_markets_from_contracts_meta(paths)

    updated = yaml.safe_load((configs_dir / "markets.yaml").read_text(encoding="utf-8"))
    assert updated["source"]["dataset"] == "legacy_futures_only"
    assert len(updated["markets"]) == 1
    assert updated["markets"][0]["market_key"] == "EUR"
    assert updated["markets"][0]["contract_code"] == "099741"
