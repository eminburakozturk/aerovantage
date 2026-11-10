"""Performans izleme servisi — tahmin vs gerçekleşen sapma analizi."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from core.logger import get_logger
from modules.data_hub.ground_truth import enrich_scada_layer_meta, observed_hour_keys, scada_is_proxy
from modules.data_hub.scada import ScadaClient
from modules.performance.mape import aggregate_mape
from modules.performance.schemas import PerformanceData, PerformanceEvaluationResponse

_TURKEY_TZ = ZoneInfo("Europe/Istanbul")


def _hour_label(timestamp: Any) -> str:
    """Zaman damgasından SCADA saat anahtarı (HH:00, Europe/Istanbul) üretir.

    Naive timestamp → teslimat saati zaten yerel kabul edilir (forecast/test).
    Aware timestamp → Europe/Istanbul'a çevrilir.
    """
    if isinstance(timestamp, str):
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    else:
        parsed = timestamp
    if parsed.tzinfo is None:
        return f"{parsed.hour:02d}:00"
    local = parsed.astimezone(_TURKEY_TZ)
    return f"{local.hour:02d}:00"


def _resolve_target_date(forecast_data: dict[str, Any], target_date: Optional[str]) -> str:
    """Forecast verisinden veya parametreden hedef tarihi çözümler."""
    if target_date:
        return target_date

    explicit = forecast_data.get("target_date")
    if explicit:
        return str(explicit)

    forecast_hours = forecast_data.get("hours", [])
    if forecast_hours:
        first_timestamp = forecast_hours[0]["timestamp"]
        if isinstance(first_timestamp, str):
            return datetime.fromisoformat(first_timestamp.replace("Z", "+00:00")).date().isoformat()
        return first_timestamp.date().isoformat()

    return date.today().isoformat()


class PerformanceMonitoringService:
    """Üretim tahmini ile gerçekleşen üretim sapmasını değerlendirir."""

    def __init__(self, scada_client: Optional[ScadaClient] = None) -> None:
        self._scada_client = scada_client or ScadaClient()
        self._logger = get_logger("modules.performance")

    def evaluate_performance(
        self,
        forecast_data: dict[str, Any],
        asset_id: Optional[str] = None,
        target_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Forecast verisine göre SCADA gerçekleşen üretim ile sapma metriklerini üretir."""
        forecast_hours = forecast_data.get("hours", [])
        resolved_asset_id = asset_id or str(forecast_data.get("asset_id", "UNKNOWN"))
        resolved_target_date = _resolve_target_date(forecast_data, target_date)

        scada_data = self._scada_client.fetch_actual_generation(
            resolved_asset_id,
            resolved_target_date,
        )
        scada_meta = enrich_scada_layer_meta(self._scada_client.get_last_fetch_meta())
        observed_keys = observed_hour_keys(scada_meta)
        proxy = scada_is_proxy(scada_meta)

        hours: list[PerformanceData] = []
        mape_pairs: list[tuple[float, float]] = []

        for hour in forecast_hours:
            forecast_mw = float(hour["generated_mw"])
            timestamp = hour["timestamp"]
            hour_key = _hour_label(timestamp)
            actual_mw = max(0.0, round(float(scada_data.get(hour_key, 0.0)), 4))
            deviation_mw = round(actual_mw - forecast_mw, 4)
            is_observed = True if observed_keys is None else hour_key in observed_keys

            if actual_mw > 0 and is_observed:
                hour_mape = round(abs(deviation_mw) / actual_mw * 100, 4)
            else:
                hour_mape = 0.0

            if is_observed:
                mape_pairs.append((forecast_mw, actual_mw))

            hours.append(
                PerformanceData(
                    timestamp=timestamp,
                    forecast_mw=forecast_mw,
                    actual_mw=actual_mw,
                    deviation_mw=deviation_mw,
                    mape_percentage=hour_mape,
                    observed=is_observed,
                )
            )

        response = PerformanceEvaluationResponse(hours=hours)
        result = response.model_dump(mode="json")
        result["mape_percentage"] = aggregate_mape(mape_pairs)
        result["scada"] = scada_meta
        result["evaluation_mode"] = "simulation" if proxy else "production"
        result["mape_informational"] = proxy
        result["observed_hour_count"] = sum(1 for item in hours if item.observed)
        result["padded_hour_count"] = sum(1 for item in hours if not item.observed)
        self._logger.info(
            "Performans degerlendirmesi tamamlandi: asset_id=%s hours=%s mape=%.2f "
            "mode=%s observed=%s padded=%s informational=%s",
            resolved_asset_id,
            len(hours),
            result["mape_percentage"],
            scada_meta.get("mode"),
            result["observed_hour_count"],
            result["padded_hour_count"],
            result["mape_informational"],
        )
        return result
