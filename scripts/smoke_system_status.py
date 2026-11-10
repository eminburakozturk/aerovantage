"""Tüm kaynak canlılık kontrolü — weather / epias / scada / gemini."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import get_settings
from core.health import HealthMonitor


def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    print("=== System Live Status ===")
    print(f"EPIAS_USE_MOCK={settings.epias_use_mock}")
    print(f"WEATHER_USE_MOCK={settings.weather_use_mock}")
    print(f"SCADA_USE_MOCK={settings.scada_use_mock}")
    print(f"LLM_PROVIDER={settings.llm_provider}")
    print()

    status = HealthMonitor().get_overall_status()
    print(f"overall={status['status']}")
    failures = 0
    for name, hub in status["data_hub"].items():
        mode = hub.get("mode")
        live = hub.get("live")
        label = hub.get("label") or mode
        st = hub.get("status")
        mark = "OK"
        # Beklenen MVP: weather/epias/gemini live; scada simulated
        if name in ("weather", "epias") and mode != "live":
            mark = "WARN"
            failures += 1
        elif name == "scada" and mode not in ("simulated", "live"):
            mark = "WARN"
            failures += 1
        elif name == "gemini" and mode != "live":
            mark = "WARN"
            failures += 1
        elif st != "ok":
            mark = "WARN"
            failures += 1
        print(f"[{mark}] {name}: status={st} mode={mode} live={live} label={label}")

    print()
    if failures:
        print(f"SONUÇ: {failures} kaynak beklenen canlı/simüle durumda değil")
        return 1
    print("SONUÇ: weather/epias/gemini live · scada simulated — sıkıntı yok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
