"""Pipeline history dedupe tests."""

from __future__ import annotations

import json
from pathlib import Path

from core.storage import PipelineStorage, dedupe_runs_by_asset_date


def test_dedupe_keeps_newest_first(tmp_path: Path) -> None:
    history = tmp_path / "h.jsonl"
    store = PipelineStorage(history_file=history)
    store.save_run({"asset_id": "RES-BAL-01", "target_date": "2026-07-10", "mape_percentage": 10})
    store.save_run({"asset_id": "RES-BAL-01", "target_date": "2026-07-10", "mape_percentage": 99})
    store.save_run({"asset_id": "RES-BND-02", "target_date": "2026-07-10", "mape_percentage": 12})
    store.save_run({"asset_id": "RES-BAL-01", "target_date": "2026-07-11", "mape_percentage": 8})

    runs = store.get_recent_runs(limit=10, dedupe=True)
    assert len(runs) == 3
    bal_10 = next(r for r in runs if r["asset_id"] == "RES-BAL-01" and r["target_date"] == "2026-07-10")
    assert bal_10["mape_percentage"] == 99

    only_bal = store.get_recent_runs(limit=10, asset_id="RES-BAL-01", dedupe=True)
    assert len(only_bal) == 2
    assert all(r["asset_id"] == "RES-BAL-01" for r in only_bal)


def test_dedupe_helper_order() -> None:
    rows = [
        {"asset_id": "A", "target_date": "2026-01-02", "n": 2},
        {"asset_id": "A", "target_date": "2026-01-02", "n": 1},
        {"asset_id": "A", "target_date": "2026-01-01", "n": 0},
    ]
    out = dedupe_runs_by_asset_date(rows)
    assert len(out) == 2
    assert out[0]["n"] == 2
