#!/usr/bin/env python3
"""30 günlük backtest — forecast isabet oranı ve dengesizlik maliyeti özeti."""

from __future__ import annotations

import sys
import time
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.logger import get_logger
from modules.forecast.production.models.wind_model import WindPowerModel
from modules.forecast.production.services import ProductionForecastService
from modules.performance.service import PerformanceMonitoringService
from modules.risk.scoring import RiskScoringService

BALIKESIR_LAT = 39.64
BALIKESIR_LON = 27.88
BACKTEST_DAYS = 30
REQUEST_DELAY_SECONDS = 0.5

logger = get_logger("scripts.backtest")


@dataclass
class BacktestAccumulator:
    """Backtest metriklerini toplar."""

    days_processed: int = 0
    days_failed: int = 0
    hourly_mape_values: list[float] = field(default_factory=list)
    total_imbalance_cost_tl: float = 0.0
    risk_scores: list[int] = field(default_factory=list)
    failed_dates: list[date] = field(default_factory=list)


def build_date_range(anchor: date, days: int) -> list[date]:
    """Bugünden geriye doğru `days` günlük tarih listesi (bugün dahil)."""
    return [anchor - timedelta(days=offset) for offset in range(days)]


def hourly_absolute_percentage_error(actual_mw: float, forecast_mw: float) -> float | None:
    """Saatlik mutlak yüzde hata: |actual - forecast| / actual."""
    if actual_mw <= 0:
        return None
    return abs(actual_mw - forecast_mw) / actual_mw


def run_backtest(anchor_date: date | None = None) -> BacktestAccumulator:
    """30 günlük risk backtest döngüsünü çalıştırır."""
    anchor = anchor_date or date.today()
    dates = build_date_range(anchor, BACKTEST_DAYS)
    service = RiskScoringService()
    production = ProductionForecastService(wind_model=WindPowerModel(capacity_mw=50.0))
    performance = PerformanceMonitoringService()
    accumulator = BacktestAccumulator()

    logger.info("Backtest basladi: anchor=%s gun_sayisi=%s", anchor, BACKTEST_DAYS)

    for index, target_date in enumerate(dates, start=1):
        try:
            forecast = production.forecast_daily_production(
                BALIKESIR_LAT,
                BALIKESIR_LON,
                target_date,
            )
            performance_data = performance.evaluate_performance(
                forecast.model_dump(mode="json")
            )
            result = service.calculate_daily_risk(target_date, performance_data)
        except Exception as exc:
            accumulator.days_failed += 1
            accumulator.failed_dates.append(target_date)
            logger.error(
                "Gun atlandi (%s/%s): target_date=%s error=%s",
                index,
                BACKTEST_DAYS,
                target_date,
                exc,
            )
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        for hour in result.hours:
            mape = hourly_absolute_percentage_error(hour.actual_mw, hour.forecast_mw)
            if mape is not None:
                accumulator.hourly_mape_values.append(mape)

        accumulator.total_imbalance_cost_tl += result.total_imbalance_cost_tl
        accumulator.risk_scores.append(result.risk_score)
        accumulator.days_processed += 1

        logger.info(
            "Gun tamamlandi (%s/%s): date=%s risk_score=%s cost=%.2f",
            index,
            BACKTEST_DAYS,
            target_date,
            result.risk_score,
            result.total_imbalance_cost_tl,
        )
        time.sleep(REQUEST_DELAY_SECONDS)

    return accumulator


def print_summary(accumulator: BacktestAccumulator) -> None:
    """Konsola özet tablo basar."""
    if accumulator.hourly_mape_values:
        avg_mape_pct = (sum(accumulator.hourly_mape_values) / len(accumulator.hourly_mape_values)) * 100
    else:
        avg_mape_pct = 0.0

    if accumulator.risk_scores:
        avg_risk_score = sum(accumulator.risk_scores) / len(accumulator.risk_scores)
    else:
        avg_risk_score = 0.0

    print()
    print("=" * 58)
    print("  AeroVantage — 30 Gunluk Backtest Ozeti (Balikesir RES)")
    print("=" * 58)
    print(f"  Incelenen Gun Sayisi              : {accumulator.days_processed}")
    print(f"  Ortalama MAPE (Hata Payi)         : %{avg_mape_pct:.2f}")
    print(f"  Toplam Dengesizlik Maliyeti       : {accumulator.total_imbalance_cost_tl:,.2f} TL")
    print(f"  Ortalama Gunluk Risk Skoru        : {avg_risk_score:.1f} / 100")
    if accumulator.days_failed:
        print(f"  Atlanan Gun Sayisi                : {accumulator.days_failed}")
    print("=" * 58)
    print()


def save_summary(accumulator: BacktestAccumulator) -> None:
    if accumulator.hourly_mape_values:
        avg_mape_pct = (sum(accumulator.hourly_mape_values) / len(accumulator.hourly_mape_values)) * 100
    else:
        avg_mape_pct = 0.0
    if accumulator.risk_scores:
        avg_risk_score = sum(accumulator.risk_scores) / len(accumulator.risk_scores)
    else:
        avg_risk_score = 0.0
    summary = {
        "days_processed": accumulator.days_processed,
        "days_failed": accumulator.days_failed,
        "average_mape_pct": round(avg_mape_pct, 4),
        "average_risk_score": round(avg_risk_score, 4),
        "total_imbalance_cost_tl": round(accumulator.total_imbalance_cost_tl, 2),
        "failed_dates": [d.isoformat() for d in accumulator.failed_dates],
    }
    output = ROOT / "data" / "models" / "backtest_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Backtest özeti kaydedildi: %s", output)


def main() -> int:
    accumulator = run_backtest()
    print_summary(accumulator)
    save_summary(accumulator)

    if accumulator.days_processed == 0:
        logger.error("Backtest tamamlanamadi: hicbir gun islenemedi.")
        return 1

    logger.info("Backtest tamamlandi: processed=%s failed=%s", accumulator.days_processed, accumulator.days_failed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
