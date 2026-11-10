"""What-if senaryo analizi servisi."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.i18n import DEFAULT_LOCALE, build_scenario_summary, normalize_locale
from core.logger import get_logger
from core.storage import PipelineStorage
from modules.asset_registry.service import AssetRegistryService
from modules.scenario.schemas import ScenarioRequest, ScenarioResult

_SCENARIO_HISTORY = Path(__file__).resolve().parent.parent.parent / "data" / "scenario_history.jsonl"
_RISK_COST_CAP = 10_000.0


class ScenarioService:
    """Pipeline verisine parametre ayarları uygulayarak what-if analizi yapar."""

    def __init__(
        self,
        storage: Optional[PipelineStorage] = None,
        registry: Optional[AssetRegistryService] = None,
    ) -> None:
        self._storage = storage or PipelineStorage()
        self._registry = registry or AssetRegistryService()
        self._logger = get_logger("modules.scenario")
        _SCENARIO_HISTORY.parent.mkdir(parents=True, exist_ok=True)

    def run_scenario(self, request: ScenarioRequest, locale: str = DEFAULT_LOCALE) -> dict[str, Any]:
        """Senaryo parametrelerini baseline pipeline verisine uygular."""
        locale = normalize_locale(locale)
        asset = self._registry.get_asset_by_id(request.asset_id)
        target_date = request.target_date or date.today()

        baseline = self._find_baseline_run(request.asset_id)
        baseline_forecast = float(baseline.get("total_daily_mw", asset.capacity_mw * 0.4))
        baseline_cost = float(baseline.get("total_imbalance_cost_tl", 0))
        baseline_risk = int(baseline.get("risk_score", 30))

        wind_factor = 1.0 + (request.wind_adjustment_pct / 100.0)
        ptf_factor = 1.0 + (request.ptf_adjustment_pct / 100.0)

        turbines = self._registry.get_turbines(request.asset_id)
        down_capacity = sum(
            t["capacity_mw"] for t in turbines[: request.turbines_down]
        )
        capacity_factor = max(0.1, (asset.capacity_mw - down_capacity) / asset.capacity_mw)

        adjusted_forecast = round(baseline_forecast * wind_factor * capacity_factor, 2)
        adjusted_cost = round(baseline_cost * ptf_factor * (2.0 - capacity_factor), 2)
        adjusted_risk = self._normalize_risk(adjusted_cost, baseline_risk, capacity_factor)

        summary = build_scenario_summary(
            locale,
            name=asset.name,
            wind_adjustment_pct=request.wind_adjustment_pct,
            ptf_adjustment_pct=request.ptf_adjustment_pct,
            turbines_down=request.turbines_down,
            baseline_forecast_mw=baseline_forecast,
            adjusted_forecast_mw=adjusted_forecast,
            baseline_cost_tl=baseline_cost,
            adjusted_cost_tl=adjusted_cost,
            baseline_risk_score=baseline_risk,
            adjusted_risk_score=adjusted_risk,
        )

        result = ScenarioResult(
            generated_at=datetime.now(timezone.utc),
            asset_id=request.asset_id,
            target_date=target_date,
            baseline_forecast_mw=baseline_forecast,
            adjusted_forecast_mw=adjusted_forecast,
            baseline_cost_tl=baseline_cost,
            adjusted_cost_tl=adjusted_cost,
            baseline_risk_score=baseline_risk,
            adjusted_risk_score=adjusted_risk,
            capacity_impact_mw=round(down_capacity, 2),
            summary=summary,
            parameters=request,
        )
        payload = result.model_dump(mode="json")
        # Persist canonical TR summary so storage stays language-stable; localize on read.
        if locale != DEFAULT_LOCALE:
            payload_tr = dict(payload)
            payload_tr["summary"] = build_scenario_summary(
                DEFAULT_LOCALE,
                name=asset.name,
                wind_adjustment_pct=request.wind_adjustment_pct,
                ptf_adjustment_pct=request.ptf_adjustment_pct,
                turbines_down=request.turbines_down,
                baseline_forecast_mw=baseline_forecast,
                adjusted_forecast_mw=adjusted_forecast,
                baseline_cost_tl=baseline_cost,
                adjusted_cost_tl=adjusted_cost,
                baseline_risk_score=baseline_risk,
                adjusted_risk_score=adjusted_risk,
            )
            self._save_history(payload_tr)
        else:
            self._save_history(payload)
        self._logger.info("Senaryo tamamlandi: asset_id=%s", request.asset_id)
        return payload

    def get_history(self, limit: int = 20, locale: str = DEFAULT_LOCALE) -> list[dict[str, Any]]:
        """Son senaryo çalıştırmalarını döndürür (özet locale'e göre yeniden üretilir)."""
        locale = normalize_locale(locale)
        if not _SCENARIO_HISTORY.exists():
            return []
        records: list[dict[str, Any]] = []
        with _SCENARIO_HISTORY.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        out = list(reversed(records[-limit:]))
        return [self._localize_record(record, locale) for record in out]

    def _localize_record(self, record: dict[str, Any], locale: str) -> dict[str, Any]:
        if locale == DEFAULT_LOCALE:
            return record
        params = record.get("parameters") or {}
        asset_id = str(record.get("asset_id") or params.get("asset_id") or "")
        name = asset_id
        if asset_id:
            try:
                name = self._registry.get_asset_by_id(asset_id).name
            except KeyError:
                name = asset_id
        out = dict(record)
        out["summary"] = build_scenario_summary(
            locale,
            name=name,
            wind_adjustment_pct=float(params.get("wind_adjustment_pct", 0) or 0),
            ptf_adjustment_pct=float(params.get("ptf_adjustment_pct", 0) or 0),
            turbines_down=int(params.get("turbines_down", 0) or 0),
            baseline_forecast_mw=float(record.get("baseline_forecast_mw", 0) or 0),
            adjusted_forecast_mw=float(record.get("adjusted_forecast_mw", 0) or 0),
            baseline_cost_tl=float(record.get("baseline_cost_tl", 0) or 0),
            adjusted_cost_tl=float(record.get("adjusted_cost_tl", 0) or 0),
            baseline_risk_score=int(record.get("baseline_risk_score", 0) or 0),
            adjusted_risk_score=int(record.get("adjusted_risk_score", 0) or 0),
        )
        return out

    def _find_baseline_run(self, asset_id: str) -> dict[str, Any]:
        runs = self._storage.get_recent_runs(limit=30)
        for run in runs:
            if run.get("asset_id") == asset_id:
                return run
        return runs[0] if runs else {}

    @staticmethod
    def _normalize_risk(cost: float, baseline_risk: int, capacity_factor: float) -> int:
        cost_component = min(100, int((cost / _RISK_COST_CAP) * 70))
        capacity_component = int((1.0 - capacity_factor) * 30)
        return min(100, max(0, cost_component + capacity_component + baseline_risk // 4))

    def _save_history(self, record: dict[str, Any]) -> None:
        with _SCENARIO_HISTORY.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
