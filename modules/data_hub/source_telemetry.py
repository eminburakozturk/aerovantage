"""Data hub kaynak telemetrisi — mock/live ayrımı ve neden kodları."""

from __future__ import annotations

from typing import Any


def parse_source_label(source: str) -> dict[str, str]:
    """Kaynak etiketinden mode, reason ve provider çıkarır."""
    normalized = (source or "unknown").strip().lower()
    if not normalized or normalized == "unknown":
        return {"mode": "unknown", "reason": "unknown", "provider": "unknown", "source": source or "unknown"}

    if "mock" in normalized:
        reason = "mock"
        if ":" in source:
            reason = source.split(":", 1)[1]
        return {
            "mode": "mock",
            "reason": reason,
            "provider": source.split("-", 1)[0] if "-" in source else source,
            "source": source,
        }

    if "simulated" in normalized:
        return {
            "mode": "simulated",
            "reason": "epias_derived",
            "provider": "epias_simulator",
            "source": source,
        }

    provider = source.split("-", 1)[0] if "-" in source else source
    return {
        "mode": "live",
        "reason": "ok",
        "provider": provider,
        "source": source,
    }


def build_source_entry(
    *,
    source: str | None = None,
    mode: str | None = None,
    reason: str | None = None,
    freshness_ok: bool | None = None,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    """Tek bir veri kaynağı için telemetri girdisi üretir."""
    parsed = parse_source_label(source or "unknown")
    entry: dict[str, Any] = {
        "source": source or parsed["source"],
        "mode": mode or parsed["mode"],
        "reason": reason or parsed["reason"],
        "provider": parsed["provider"],
    }
    if freshness_ok is not None:
        entry["freshness_ok"] = freshness_ok
    if fetched_at is not None:
        entry["fetched_at"] = fetched_at
    return entry


def build_pipeline_telemetry(
    *,
    weather_source: str,
    weather_meta: dict[str, Any] | None = None,
    scada_source: dict[str, Any],
    epias_source: str,
    epias_meta: dict[str, Any] | None = None,
    llm_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pipeline metadata için birleşik kaynak telemetrisi üretir."""
    weather_entry = build_source_entry(source=weather_source)
    if weather_meta:
        weather_entry.update(
            {
                k: weather_meta[k]
                for k in ("mode", "reason", "freshness_ok", "fetched_at", "provider")
                if k in weather_meta
            }
        )
        if weather_meta.get("source"):
            weather_entry["source"] = weather_meta["source"]

    epias_entry = build_source_entry(source=epias_source)
    if epias_meta:
        epias_entry.update(
            {
                k: epias_meta[k]
                for k in ("mode", "reason", "fetched_at", "provider")
                if k in epias_meta
            }
        )
        if epias_meta.get("source"):
            epias_entry["source"] = epias_meta["source"]

    scada_entry: dict[str, Any] = {
        "mode": scada_source.get("mode", "unknown"),
        "reason": scada_source.get("reason", "unknown"),
        "source": scada_source.get("source", f"scada-{scada_source.get('mode', 'unknown')}"),
        "provider": scada_source.get("provider", "scada"),
    }
    for key in ("confidence", "live", "label"):
        if key in scada_source:
            scada_entry[key] = scada_source[key]

    llm_entry: dict[str, Any] = {
        "mode": "unknown",
        "reason": "not_recorded",
        "source": "llm-unknown",
        "provider": "llm",
    }
    if llm_meta:
        llm_entry.update({k: llm_meta[k] for k in llm_meta})

    sources = {
        "weather": weather_entry,
        "scada": scada_entry,
        "epias": epias_entry,
        "gemini": llm_entry,
    }

    def _is_degraded(name: str, data: dict[str, Any]) -> bool:
        if data.get("freshness_ok") is False:
            return True
        mode = data.get("mode")
        if mode in ("mock", "fallback"):
            return True
        if name == "scada" and mode == "simulated":
            return True
        if mode == "live":
            return False
        reason = data.get("reason", "ok")
        return reason not in ("ok", "unknown", "epias_derived")

    degraded_sources = [name for name, data in sources.items() if _is_degraded(name, data)]

    mock_count = sum(1 for data in sources.values() if data.get("mode") == "mock")
    simulated_count = sum(1 for data in sources.values() if data.get("mode") == "simulated")
    live_count = sum(1 for data in sources.values() if data.get("mode") == "live")
    fallback_count = sum(1 for data in sources.values() if data.get("mode") == "fallback")

    return {
        "sources": sources,
        "is_degraded": len(degraded_sources) > 0,
        "degraded_sources": degraded_sources,
        "mock_usage_rate": round(mock_count / len(sources), 4) if sources else 0.0,
        "live_source_count": live_count,
        "mock_source_count": mock_count,
        "simulated_source_count": simulated_count,
        "fallback_source_count": fallback_count,
    }
