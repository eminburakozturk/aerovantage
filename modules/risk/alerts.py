"""Risk tabanlı bildirim merkezi."""

from __future__ import annotations

from typing import Any

from core.i18n import DEFAULT_LOCALE, build_localized_notifications, normalize_locale


class NotificationCenter:
    """Dashboard'a taşınacak operasyonel bildirimleri üretir."""

    def build_notifications(
        self,
        alert_status: dict[str, Any],
        action_plan: str,
        risk_score: int,
        locale: str = DEFAULT_LOCALE,
    ) -> list[dict[str, str]]:
        """Uyarı ve aksiyon planından dashboard bildirim listesi oluşturur."""
        return build_localized_notifications(
            normalize_locale(locale),
            alert_status=alert_status,
            action_plan=action_plan,
            risk_score=risk_score,
        )
