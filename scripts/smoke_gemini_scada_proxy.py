"""Canlı Gemini + SCADA EPİAŞ-simulator smoke."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import get_settings
from modules.ai.assistant import AIDecisionAssistant
from modules.data_hub.scada import ScadaClient


def main() -> int:
    # Settings cache'i taze .env için temizle
    get_settings.cache_clear()
    settings = get_settings()
    print("=== Live Gemini + EPİAŞ-SCADA Proxy Smoke ===")
    print(f"LLM_PROVIDER={settings.llm_provider}")
    print(f"LLM_KEY={bool(settings.llm_api_key.get_secret_value())}")
    print(f"EPIAS_USE_MOCK={settings.epias_use_mock}")
    print(f"SCADA_USE_MOCK={settings.scada_use_mock} (fiziksel yok -> EPIAS simulator)")
    print()

    failures = 0
    target = (date.today() - timedelta(days=1)).isoformat()

    scada = ScadaClient(settings=settings)
    try:
        data = scada.fetch_actual_generation("RES-BAL-01", target)
        meta = scada.get_last_fetch_meta()
        print(
            f"[{'OK' if meta.get('mode') == 'simulated' else 'WARN'}] SCADA simulator: "
            f"mode={meta.get('mode')} reason={meta.get('reason')} "
            f"source={meta.get('source')} confidence={meta.get('confidence')} "
            f"live={meta.get('live')} label={meta.get('label')} "
            f"hours={len(data)} sample_00={data.get('00:00')}"
        )
        if meta.get("mode") != "simulated" or meta.get("source") != "simulated_from_epias":
            failures += 1
        if meta.get("live") not in (False, "false"):
            failures += 1
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] SCADA/proxy: {exc}")
        failures += 1

    assistant = AIDecisionAssistant(settings=settings)
    try:
        response = assistant.generate_explanation(
            {
                "risk_score": 55,
                "total_imbalance_cost_tl": 4200.0,
                "forecast_mw": 30.0,
                "avg_forecast_mw": 18.0,
                "avg_ptf_price": 2600.0,
                "wind_speed_mps": 9.5,
                "asset_id": "RES-BAL-01",
                "mape_percentage": 12.0,
            }
        )
        source = getattr(response, "source", "")
        ok = source == "gemini"
        print(
            f"[{'OK' if ok else 'WARN'}] Gemini insight: source={source} "
            f"action_plan={bool(response.action_plan)}"
        )
        if not ok:
            failures += 1
            print(f"  insight preview: {str(response.insight)[:120]}")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Gemini: {exc}")
        failures += 1

    print()
    if failures:
        print(f"SONUÇ: {failures} kontrol başarısız")
        return 1
    print("SONUÇ: Gemini canlı + SCADA EPİAŞ simulator OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
