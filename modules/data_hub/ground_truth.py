"""Operational vs equipment ground-truth güven bayrakları.

EPİAŞ türevi / mock actual production alarmı üretmemeli.
"""

from __future__ import annotations

from typing import Any, Optional

NON_LIVE_SCADA_MODES = frozenset({"simulated", "mock"})


def scada_is_proxy(meta: Optional[dict[str, Any]]) -> bool:
    """Fiziksel SCADA değilse True (simulated EPİAŞ veya deterministik mock)."""
    if not meta:
        return False
    live = meta.get("live")
    if live is True or live == "true":
        return False
    mode = str(meta.get("mode") or "")
    if mode in NON_LIVE_SCADA_MODES:
        return True
    return meta.get("source") == "simulated_from_epias"


def observed_hour_keys(meta: Optional[dict[str, Any]]) -> Optional[set[str]]:
    """Gözlemlenen saat anahtarları (HH:00).

    None → tüm saatler değerlendirmeye dahil (live veya tam mock).
    set → yalnızca bu saatler MAPE/risk'e girer (EPİAŞ pad saatleri hariç).
    """
    if not meta:
        return None
    raw = meta.get("observed_hours")
    if raw is None:
        return None
    return {str(item) for item in raw}


def enrich_scada_layer_meta(meta: dict[str, Any]) -> dict[str, Any]:
    """Operational / Equipment katman etiketlerini meta'ya ekler."""
    out = dict(meta)
    mode = str(out.get("mode") or "unknown")
    if mode == "live":
        out.setdefault("operational_layer", "live")
        out.setdefault("operational_label", "Operational: Live SCADA")
        out.setdefault("equipment_layer", "live")
        out.setdefault("equipment_label", "Equipment: Live SCADA")
    elif mode == "simulated":
        out.setdefault("operational_layer", "derived")
        out.setdefault(
            "operational_label",
            "Operational: EPİAŞ Derived (MW only)",
        )
        out.setdefault("equipment_layer", "mock")
        out.setdefault("equipment_label", "Equipment: Mock (no plant telemetry)")
    else:
        out.setdefault("operational_layer", "mock")
        out.setdefault("operational_label", "Operational: Mock")
        out.setdefault("equipment_layer", "mock")
        out.setdefault("equipment_label", "Equipment: Mock")
    return out
