"""AI karar geçmişi logger."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.logger import get_logger
from modules.ai.schemas import AIResponse, DecisionHistory

_DECISION_HISTORY_FILE = (
    Path(__file__).resolve().parent.parent.parent / "data" / "decision_history.jsonl"
)


class DecisionHistoryLogger:
    """LLM/playbook yanıtlarını kalıcı karar geçmişine yazar."""

    def __init__(self, history_file: Path | None = None) -> None:
        self._history_file = history_file or _DECISION_HISTORY_FILE
        self._logger = get_logger("modules.ai.history")
        self._history_file.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        response: AIResponse,
        risk_data: dict[str, Any],
        source: str,
        asset_id: Optional[str] = None,
    ) -> DecisionHistory:
        """Insight ve action_plan verisini DecisionHistory olarak kaydeder."""
        entry = DecisionHistory(
            recorded_at=datetime.now(timezone.utc),
            source=source,
            asset_id=asset_id or risk_data.get("asset_id"),
            risk_score=risk_data.get("risk_score"),
            insight=response.insight,
            action_plan=response.action_plan,
        )
        with self._history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.model_dump(mode="json"), ensure_ascii=False) + "\n")

        self._logger.info(
            "Decision history kaydedildi: source=%s asset_id=%s action_plan=%s",
            source,
            entry.asset_id,
            entry.action_plan,
        )
        return entry

    def get_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Son karar kayıtlarını döndürür."""
        if not self._history_file.exists():
            return []

        records: list[dict[str, Any]] = []
        with self._history_file.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return list(reversed(records[-limit:]))
