"""MAPE hesaplama yardımcıları — düşük üretim saatlerinde sapmayı stabilize eder."""

from __future__ import annotations

from typing import Iterable


def aggregate_mape(
    forecast_actual_pairs: Iterable[tuple[float, float]],
    min_actual_mw: float = 0.5,
) -> float:
    """Ağırlıklı MAPE: yalnızca anlamlı üretim saatlerini dahil eder.

    Formül: sum(|f-a|) / sum(a) * 100
    Sıfıra yakın üretim saatleri MAPE'yi şişirmez.
    """
    active = [(float(f), float(a)) for f, a in forecast_actual_pairs if float(a) >= min_actual_mw]
    if not active:
        return 0.0
    total_actual = sum(a for _, a in active)
    if total_actual <= 0:
        return 0.0
    total_error = sum(abs(f - a) for f, a in active)
    return round(min(999.0, total_error / total_actual * 100), 2)
