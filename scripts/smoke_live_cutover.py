"""Sprint B — canlı EPİAŞ / Weather cutover smoke testi.

Kullanım (repo kökünden):
  python scripts/smoke_live_cutover.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import get_settings
from modules.data_hub.epias import EpiasClient
from modules.data_hub.epias_auth import EpiasAuthError, EpiasCasAuth
from modules.data_hub.weather import WeatherClient


def main() -> int:
    settings = get_settings()
    print("=== AeroVantage Live Cutover Smoke ===")
    print(f"APP_ENV={settings.app_env}")
    print(f"EPIAS_USE_MOCK={settings.epias_use_mock}")
    print(f"WEATHER_USE_MOCK={settings.weather_use_mock}")
    print(f"SCADA_USE_MOCK={settings.scada_use_mock}")
    print()

    failures = 0
    ptf_date = date.today() - timedelta(days=1)
    weather_date = date.today()

    auth = EpiasCasAuth(settings=settings)
    if not auth.has_credentials():
        print("[FAIL] EPİAŞ: username/password yok")
        failures += 1
    else:
        try:
            headers = auth.get_auth_headers()
            has_tgt = "TGT" in headers and str(headers["TGT"]).startswith("TGT-")
            print(f"[OK] EPİAŞ auth: TGT alındı={has_tgt}")
        except EpiasAuthError as exc:
            print(f"[FAIL] EPİAŞ auth: {exc.reason} — {exc}")
            failures += 1

    epias = EpiasClient(settings=settings)
    try:
        ptf = epias.fetch_day_ahead_ptf(ptf_date)
        meta = epias.get_last_fetch_meta()
        mode = meta.get("mode")
        reason = meta.get("reason")
        hour_count = len(ptf.hours) if ptf and getattr(ptf, "hours", None) else 0
        ok = mode == "live" and hour_count > 0
        status = "OK" if ok else "WARN"
        print(
            f"[{status}] EPİAŞ PTF ({ptf_date}): mode={mode} reason={reason} "
            f"hours={hour_count} source={getattr(ptf, 'source', None)}"
        )
        if not ok:
            failures += 1
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] EPİAŞ PTF: {exc}")
        failures += 1

    weather = WeatherClient(settings=settings)
    try:
        forecast = weather.fetch_hourly_forecast(39.9, 32.8, weather_date)
        meta = weather.get_last_fetch_meta()
        mode = meta.get("mode")
        reason = meta.get("reason")
        hour_count = len(forecast.hours) if forecast and forecast.hours else 0
        ok = mode == "live" and hour_count == 24
        status = "OK" if ok else "WARN"
        print(
            f"[{status}] Weather ({weather_date}): mode={mode} reason={reason} "
            f"hours={hour_count} source={getattr(forecast, 'source', None)}"
        )
        if not ok:
            failures += 1
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Weather: {exc}")
        failures += 1

    print()
    if failures:
        print(f"SONUÇ: {failures} kontrol başarısız / degraded")
        return 1
    print("SONUÇ: EPİAŞ + Weather canlı cutover OK (SCADA simulated beklenen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
