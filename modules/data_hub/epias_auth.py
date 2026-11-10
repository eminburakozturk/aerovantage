"""EPİAŞ CAS (TGT/Ticket) kimlik doğrulama istemcisi."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from requests import Session

from core.config import Settings, get_settings
from core.logger import get_logger


class EpiasAuthError(Exception):
    """EPİAŞ kimlik doğrulama hatası."""

    def __init__(self, reason: str, message: str = "") -> None:
        super().__init__(message or reason)
        self.reason = reason


class EpiasCasAuth:
    """EPİAŞ Şeffaflık Platformu için TGT tabanlı kimlik doğrulama."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        session: Optional[Session] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._session = session or requests.Session()
        self._logger = get_logger("data_hub.epias_auth")
        self._tgt: Optional[str] = None
        self._tgt_expires_at: Optional[datetime] = None

    def has_credentials(self) -> bool:
        """TGT almak için gerekli kullanıcı bilgilerinin tanımlı olup olmadığını döndürür."""
        username = self._settings.epias_username.get_secret_value()
        password = self._settings.epias_password.get_secret_value()
        return bool(username and password)

    def get_auth_headers(self) -> dict[str, str]:
        """Canlı EPİAŞ servis çağrıları için kimlik doğrulama header'larını üretir."""
        api_key = self._settings.epias_api_key.get_secret_value()
        if self.has_credentials():
            return {"TGT": self._get_valid_tgt()}
        if api_key:
            return {"Authorization": f"Bearer {api_key}"}
        raise EpiasAuthError("credentials_missing")

    def invalidate(self) -> None:
        """Önbellekteki TGT değerini temizler."""
        self._tgt = None
        self._tgt_expires_at = None

    def _get_valid_tgt(self) -> str:
        now = datetime.now(timezone.utc)
        if self._tgt and self._tgt_expires_at and now < self._tgt_expires_at:
            return self._tgt
        return self._request_tgt()

    def _request_tgt(self) -> str:
        username = self._settings.epias_username.get_secret_value()
        password = self._settings.epias_password.get_secret_value()
        if not username or not password:
            raise EpiasAuthError("credentials_missing")

        cas_url = self._settings.epias_cas_url.rstrip("/")
        self._logger.info("EPİAŞ TGT isteniyor: cas_url=%s", cas_url)

        try:
            response = self._session.post(
                cas_url,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "text/plain",
                },
                data={"username": username, "password": password},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise EpiasAuthError("request_failed", str(exc)) from exc

        if response.status_code in (401, 403):
            raise EpiasAuthError("auth_failed")

        if response.status_code >= 400:
            raise EpiasAuthError(
                "auth_failed",
                f"CAS HTTP {response.status_code}: {response.text[:200]}",
            )

        tgt = response.text.strip()
        if not tgt.startswith("TGT-"):
            raise EpiasAuthError("invalid_tgt_response")

        ttl_minutes = max(5, int(self._settings.epias_tgt_ttl_minutes))
        self._tgt = tgt
        self._tgt_expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        self._logger.info("EPİAŞ TGT alındı: ttl_minutes=%s", ttl_minutes)
        return tgt
