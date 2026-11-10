"""API kimlik doğrulama — Bearer token."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import get_settings

_bearer_scheme = HTTPBearer(auto_error=False)


def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer_scheme),
) -> str:
    """Tüm /api/v1/* rotaları için Bearer API anahtarı doğrular."""
    settings = get_settings()
    expected_key = settings.api_secret_key.get_secret_value()

    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    if credentials is None or credentials.credentials != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    return credentials.credentials
