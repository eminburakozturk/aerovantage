"""Dashboard entegrasyon testi — API yanıtını dashboard fonksiyonlarıyla doğrular."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Fail-closed API key — test must set env before Settings cache / app import.
_TEST_KEY = "test-aerovantage-integration-key"
os.environ["API_SECRET_KEY"] = _TEST_KEY

from fastapi.testclient import TestClient  # noqa: E402

from core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from api.main import app  # noqa: E402
from dashboard.app import build_hourly_dataframe  # noqa: E402


def test_via_testclient() -> None:
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_TEST_KEY}"}
    response = client.get(
        "/api/v1/risk/daily",
        params={"lat": 39.64, "lon": 27.88, "target_date": "2026-07-05"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert "risk_score" in data
    assert "total_imbalance_cost_tl" in data
    assert len(data["hours"]) == 24

    df = build_hourly_dataframe(data["hours"])
    assert list(df.columns) == ["Saat", "Tahmin (MW)", "Gerçekleşen (MW)", "PTF (TL/MWh)"]
    assert len(df) == 24

    print("OK: API status=200, hours=24, chart_df columns valid")
    print(f"    risk_score={data['risk_score']}, total_cost={data['total_imbalance_cost_tl']}")


if __name__ == "__main__":
    test_via_testclient()
