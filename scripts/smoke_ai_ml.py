"""Sprint G — AI/ML ops smoke testi.

Kullanım:
  python scripts/smoke_ai_ml.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import get_settings
from modules.ai.assistant import AIDecisionAssistant
from modules.ml_registry.registry import list_registry_entries


def main() -> int:
    settings = get_settings()
    print("=== AeroVantage AI/ML Ops Smoke ===")
    print(f"LLM_PROVIDER={settings.llm_provider}")
    print(f"LLM_API_KEY configured={bool(settings.llm_api_key.get_secret_value())}")
    print()

    failures = 0

    assistant = AIDecisionAssistant(settings=settings)
    playbook_count = len(assistant._playbook)
    if playbook_count < 1:
        print("[FAIL] Playbook boş")
        failures += 1
    else:
        print(f"[OK] Playbook entries={playbook_count}")

    sample_risk = {
        "risk_score": 80,
        "total_imbalance_cost_tl": 5000.0,
        "forecast_mw": 40.0,
        "avg_forecast_mw": 20.0,
        "avg_ptf_price": 2500.0,
        "wind_speed_mps": 12.0,
        "asset_id": "RES-BAL-01",
        "mape_percentage": 25.0,
    }
    try:
        response = assistant.generate_explanation(sample_risk)
        has_plan = bool(getattr(response, "action_plan", None))
        source = getattr(response, "source", "unknown")
        print(f"[OK] AI insight: source={source} action_plan={has_plan}")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] AI insight: {exc}")
        failures += 1

    try:
        entries = list_registry_entries(limit=5)
        print(f"[OK] Model registry readable: recent={len(entries)}")
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Model registry: {exc}")

    live_ready = settings.llm_provider in ("openai", "gemini") and bool(
        settings.llm_api_key.get_secret_value()
    )
    if live_ready:
        print("[OK] LLM live-ready (provider+key)")
    else:
        print("[INFO] LLM playbook mode (expected without LLM_API_KEY)")
        print("       Cutover: LLM_PROVIDER=openai|gemini + LLM_API_KEY, restart backend")

    print()
    if failures:
        print(f"SONUÇ: {failures} kontrol başarısız")
        return 1
    print("SONUÇ: AI/ML ops smoke OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
