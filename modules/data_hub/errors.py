"""Data Hub veri doğrulama hataları."""

from __future__ import annotations

from typing import Any


class DataValidationError(ValueError):
    """Dış veri kaynağından gelen geçersiz veya eksik veri."""


class DataSourceDegradedError(RuntimeError):
    """Canlı veri kaynağı başarısız olduğu için fallback devreye girdi."""


class DataQualityGateError(RuntimeError):
    """Pipeline veri kalitesi eşiğini geçemediği için durduruldu."""

    def __init__(self, report: Any) -> None:
        self.report = report
        score = getattr(report, "score", 0.0)
        super().__init__(f"Data quality gate failed (score={score})")
