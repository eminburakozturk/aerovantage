"""Çoklu santral portföy birleştirme servisi."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from core.i18n import translate
from core.logger import get_logger
from modules.ai.assistant import AIDecisionAssistant
from modules.asset_registry.service import AssetRegistryService
from modules.reporting.service import ReportingService


class PortfolioAggregatorService:
    """Birden fazla santralin raporlarını portföy düzeyinde birleştirir."""

    def __init__(
        self,
        reporting_service: Optional[ReportingService] = None,
        asset_registry: Optional[AssetRegistryService] = None,
        ai_assistant: Optional[AIDecisionAssistant] = None,
    ) -> None:
        self._reporting_service = reporting_service or ReportingService()
        self._asset_registry = asset_registry or AssetRegistryService()
        self._ai_assistant = ai_assistant or AIDecisionAssistant()
        self._logger = get_logger("modules.portfolio_aggregator")

    def get_aggregated_report(
        self, asset_ids: list[str], days: int, locale: str = "tr"
    ) -> dict[str, Any]:
        """Seçili santrallerin executive raporlarını portföy metriklerinde birleştirir."""
        if not asset_ids:
            raise ValueError("En az bir asset_id gerekli")

        asset_reports: list[dict[str, Any]] = []
        total_cost = 0.0
        critical_alert_count = 0
        weighted_mape_numerator = 0.0
        total_capacity_mw = 0.0
        asset_summaries: list[dict[str, Any]] = []

        for asset_id in asset_ids:
            report = self._reporting_service.generate_executive_report(
                asset_id=asset_id,
                days_back=days,
                locale=locale,
            )
            asset_reports.append(report)

            total_cost += float(report.get("total_imbalance_cost_tl") or 0)
            critical_alert_count += int(report.get("critical_alerts_count") or 0)

            try:
                asset = self._asset_registry.get_asset_by_id(asset_id)
                capacity_mw = asset.capacity_mw
            except KeyError:
                capacity_mw = 1.0

            average_mape = float(report.get("average_mape") or 0)
            weighted_mape_numerator += average_mape * capacity_mw
            total_capacity_mw += capacity_mw

            asset_summaries.append(
                {
                    "asset_id": asset_id,
                    "capacity_mw": capacity_mw,
                    "total_imbalance_cost_tl": report.get("total_imbalance_cost_tl", 0),
                    "average_mape": average_mape,
                    "critical_alerts_count": report.get("critical_alerts_count", 0),
                    "executive_summary": report.get("executive_summary", ""),
                }
            )

        avg_mape = (
            round(weighted_mape_numerator / total_capacity_mw, 4)
            if total_capacity_mw > 0
            else 0.0
        )

        portfolio_prompt_data = {
            "report_type": "portfolio_aggregate",
            "asset_ids": asset_ids,
            "period_days": days,
            "total_imbalance_cost_tl": round(total_cost, 2),
            "average_mape": avg_mape,
            "critical_alerts_count": critical_alert_count,
            "total_capacity_mw": round(total_capacity_mw, 2),
            "asset_summaries": asset_summaries,
        }
        try:
            summary = self._ai_assistant.generate_explanation(
                portfolio_prompt_data, locale=locale
            ).insight
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("Portföy AI özeti atlandı: %s", exc)
            summary = translate(
                locale,
                "reporting.portfolio_fallback",
                count=len(asset_ids),
                cost=total_cost,
                mape=avg_mape,
                critical=critical_alert_count,
            )

        result = {
            "report_id": str(uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "asset_ids": asset_ids,
            "period_days": days,
            "total_cost": round(total_cost, 2),
            "avg_mape": avg_mape,
            "critical_alert_count": critical_alert_count,
            "summary": summary,
            "assets": asset_reports,
        }

        self._logger.info(
            "Portfoy raporu uretildi: assets=%s days=%s total_cost=%.2f avg_mape=%.2f critical=%s",
            len(asset_ids),
            days,
            result["total_cost"],
            result["avg_mape"],
            result["critical_alert_count"],
        )
        return result
