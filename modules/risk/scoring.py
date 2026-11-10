"""Günlük risk skorlama servisi — PTF ve performans sapmasını birleştirir."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from core.logger import get_logger
from modules.data_hub.epias import EpiasClient
from modules.data_hub.ground_truth import scada_is_proxy
from modules.risk.schemas import DailyRiskScoreResponse, HourlyRiskData

_IMBALANCE_PENALTY_RATE = 0.03
_RISK_SCORE_COST_CAP_TL = 10_000.0


class RiskScoringService:
    """Performans sapması ile PTF verisini birleştirerek günlük risk skoru üretir."""

    def __init__(self, epias_client: Optional[EpiasClient] = None) -> None:
        self._epias_client = epias_client or EpiasClient()
        self._logger = get_logger("risk.scoring")

    def calculate_daily_risk(
        self,
        target_date: date,
        performance_data: dict[str, Any],
    ) -> DailyRiskScoreResponse:
        """Performance katmanından gelen sapma verisiyle dengesizlik maliyeti hesaplar.

        Gözlemlenmemiş (pad) saatler maliyete dahil edilmez.
        """
        self._logger.info(
            "Günlük risk hesabı başlatıldı: target_date=%s",
            target_date,
        )

        ptf_response = self._epias_client.fetch_day_ahead_ptf(target_date)
        ptf_by_hour = {
            hourly_ptf.hour: float(hourly_ptf.ptf) for hourly_ptf in ptf_response.hours
        }

        hours: list[HourlyRiskData] = []
        total_imbalance_cost_tl = 0.0
        scada_meta = performance_data.get("scada") or {}
        proxy = scada_is_proxy(scada_meta) or performance_data.get("evaluation_mode") == "simulation"

        for performance_hour in performance_data.get("hours", []):
            forecast_mw = float(performance_hour["forecast_mw"])
            actual_mw = float(performance_hour["actual_mw"])
            deviation_mw = float(performance_hour["deviation_mw"])
            is_observed = performance_hour.get("observed", True) is not False

            timestamp_raw = performance_hour["timestamp"]
            if isinstance(timestamp_raw, str):
                timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
            else:
                timestamp = timestamp_raw
            hour_index = timestamp.hour

            ptf_price = ptf_by_hour.get(hour_index, 0.0)
            # Pad / gözlemlenmemiş saatler maliyete 0 girer ama 24 saatlik şema korunur (DQ)
            imbalance_cost_tl = (
                round(abs(deviation_mw) * ptf_price * _IMBALANCE_PENALTY_RATE, 2)
                if is_observed
                else 0.0
            )

            hours.append(
                HourlyRiskData(
                    timestamp=timestamp,
                    forecast_mw=forecast_mw,
                    actual_mw=actual_mw,
                    ptf_price=ptf_price,
                    imbalance_cost_tl=imbalance_cost_tl,
                )
            )
            total_imbalance_cost_tl += imbalance_cost_tl

        total_imbalance_cost_tl = round(total_imbalance_cost_tl, 2)
        risk_score = self._normalize_risk_score(total_imbalance_cost_tl)

        self._logger.info(
            "Günlük risk hesabı tamamlandı: target_date=%s total_cost=%s risk_score=%s proxy=%s",
            target_date,
            total_imbalance_cost_tl,
            risk_score,
            proxy,
        )

        return DailyRiskScoreResponse(
            target_date=target_date,
            total_imbalance_cost_tl=total_imbalance_cost_tl,
            risk_score=risk_score,
            hours=hours,
            market_source=ptf_response.source,
        )

    @staticmethod
    def _normalize_risk_score(total_cost_tl: float) -> int:
        """Maliyeti 0–100 arası risk skoruna dönüştürür."""
        if total_cost_tl <= 0:
            return 0
        score = int((total_cost_tl / _RISK_SCORE_COST_CAP_TL) * 100)
        return min(score, 100)


def verify_risk_score_response(risk: DailyRiskScoreResponse) -> dict[str, Any]:
    """Risk skorunun saatlik maliyet toplamı ve normalizasyon ile tutarlı olduğunu doğrular."""
    recomputed_total = round(sum(hour.imbalance_cost_tl for hour in risk.hours), 2)
    recomputed_score = RiskScoringService._normalize_risk_score(recomputed_total)
    total_matches = abs(recomputed_total - risk.total_imbalance_cost_tl) <= 0.05
    score_matches = recomputed_score == risk.risk_score
    in_range = 0 <= risk.risk_score <= 100
    passed = total_matches and score_matches and in_range
    return {
        "passed": passed,
        "recomputed_total_imbalance_cost_tl": recomputed_total,
        "recomputed_risk_score": recomputed_score,
        "total_matches": total_matches,
        "score_matches": score_matches,
        "in_range": in_range,
    }
