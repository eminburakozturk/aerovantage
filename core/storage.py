"""Pipeline çalıştırma geçmişi ve adım adım audit log depolama."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.logger import get_logger

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_HISTORY_FILE = _DATA_DIR / "pipeline_history.jsonl"
_AUDIT_FILE = _DATA_DIR / "pipeline_audit.jsonl"
_METRICS_FILE = _DATA_DIR / "pipeline_metrics.jsonl"


@dataclass
class AuditLog:
    """Tek pipeline adımının izlenebilirlik kaydı."""

    audit_id: str
    step: str
    asset_id: str
    target_date: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def dedupe_runs_by_asset_date(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aynı (asset_id, gün) için yalnızca en yeni kaydı tutar.

    Gün anahtarı: target_date (tercih) veya saved_at tarihi.
    Girdi en yeniden eskiye sıralı olmalı; çıktı da aynı sırayı korur.
    """
    seen: set[tuple[Any, str]] = set()
    unique: list[dict[str, Any]] = []
    for run in runs:
        target = str(run.get("target_date") or "").strip()
        if not target:
            target = str(run.get("saved_at") or "")[:10]
        key = (run.get("asset_id"), target)
        if key in seen:
            continue
        seen.add(key)
        unique.append(run)
    return unique


class PipelineStorage:
    """JSON Lines tabanlı pipeline ve audit log depolaması."""

    def __init__(
        self,
        history_file: Path | None = None,
        audit_file: Path | None = None,
        metrics_file: Path | None = None,
    ) -> None:
        self._history_file = history_file or _HISTORY_FILE
        self._audit_file = audit_file or _AUDIT_FILE
        self._metrics_file = metrics_file or _METRICS_FILE
        self._logger = get_logger("core.storage")
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        self._history_file.parent.mkdir(parents=True, exist_ok=True)

    def log_step(
        self,
        step: str,
        asset_id: str,
        target_date: str,
        status: str = "completed",
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Pipeline adımını audit log dosyasına yazar."""
        entry = AuditLog(
            audit_id=str(uuid4()),
            step=step,
            asset_id=asset_id,
            target_date=target_date,
            status=status,
            details=details or {},
        )
        with self._audit_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

        self._logger.info(
            "Audit kaydi: step=%s asset_id=%s status=%s",
            step,
            asset_id,
            status,
        )
        return entry

    def get_audit_trail(self, limit: int = 50) -> list[dict[str, Any]]:
        """Son audit kayıtlarını en yeniden eskiye döndürür."""
        if not self._audit_file.exists():
            return []

        entries: list[dict[str, Any]] = []
        with self._audit_file.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return list(reversed(entries[-limit:]))

    def save_run(self, run_data: dict[str, Any]) -> dict[str, Any]:
        """Pipeline çalıştırma kaydını zaman damgasıyla JSONL dosyasına yazar."""
        record = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            **run_data,
        }
        with self._history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        self._logger.info(
            "Pipeline kaydi depolandi: asset_id=%s target_date=%s",
            run_data.get("asset_id"),
            run_data.get("target_date"),
        )
        return record

    def _read_all_runs(self) -> list[dict[str, Any]]:
        if not self._history_file.exists():
            return []
        runs: list[dict[str, Any]] = []
        with self._history_file.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                runs.append(json.loads(line))
        return runs

    def get_recent_runs(
        self,
        limit: int = 10,
        *,
        asset_id: str | None = None,
        dedupe: bool = True,
    ) -> list[dict[str, Any]]:
        """Son pipeline kayıtlarını en yeniden eskiye döndürür.

        Varsayılan olarak (asset_id, target_date) başına tek kayıt (en yeni).
        `limit` benzersiz kayıt sayısıdır; dosyadan daha geniş pencere okunur.
        """
        runs = self._read_all_runs()
        if asset_id:
            runs = [run for run in runs if run.get("asset_id") == asset_id]

        # En yeniden eskiye
        newest_first = list(reversed(runs))
        if dedupe:
            newest_first = dedupe_runs_by_asset_date(newest_first)

        return newest_first[: max(0, limit)]

    def log_model_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Model/evaluation metriklerini zaman damgasıyla saklar."""
        record = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **metrics,
        }
        with self._metrics_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._logger.info(
            "Model metrik kaydı depolandı: asset_id=%s target_date=%s",
            metrics.get("asset_id"),
            metrics.get("target_date"),
        )
        return record

    def get_recent_metrics(self, asset_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Son model/evaluation metrik kayıtlarını döndürür."""
        if not self._metrics_file.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self._metrics_file.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if asset_id and item.get("asset_id") != asset_id:
                    continue
                entries.append(item)
        return list(reversed(entries[-limit:]))
