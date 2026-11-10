"""Veri kaynağı freshness (tazelik) kontrolleri."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Protocol
from zoneinfo import ZoneInfo

_TURKEY_TZ = ZoneInfo("Europe/Istanbul")


class _HasTimestamp(Protocol):
    timestamp: datetime


def _local_date(ts: datetime) -> date:
    aware = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return aware.astimezone(_TURKEY_TZ).date()


def check_hourly_freshness(
    hours: list[_HasTimestamp],
    target_date: date,
    *,
    max_age_hours: float = 48.0,
    reference_time: datetime | None = None,
) -> dict[str, Any]:
    """Saatlik veri setinin hedef tarih ve maksimum yaş açısından tazeliğini doğrular."""
    now = reference_time or datetime.now(timezone.utc)
    if not hours:
        return {
            "freshness_ok": False,
            "reason": "empty_dataset",
            "target_date": target_date.isoformat(),
            "newest_timestamp": None,
            "age_hours": None,
        }

    timestamps = [
        hour.timestamp if hour.timestamp.tzinfo else hour.timestamp.replace(tzinfo=timezone.utc)
        for hour in hours
    ]
    newest = max(timestamps)
    oldest = min(timestamps)

    covers_target = any(_local_date(ts) == target_date for ts in timestamps)
    age_hours = (now - newest).total_seconds() / 3600.0
    freshness_ok = covers_target and age_hours <= max_age_hours

    reason = "ok"
    if not covers_target:
        reason = "missing_target_date"
    elif age_hours > max_age_hours:
        reason = "stale_data"

    return {
        "freshness_ok": freshness_ok,
        "reason": reason,
        "target_date": target_date.isoformat(),
        "newest_timestamp": newest.isoformat(),
        "oldest_timestamp": oldest.isoformat(),
        "age_hours": round(age_hours, 2),
        "hour_count": len(hours),
    }
