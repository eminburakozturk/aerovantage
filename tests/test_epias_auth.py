"""EPİAŞ TGT auth ve canlı mapping testleri."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from core.config import Settings
from modules.data_hub.epias import EpiasClient
from modules.data_hub.epias_auth import EpiasAuthError, EpiasCasAuth


class _FakeEpiasResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeEpiasSession:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self._status_code = status_code

    def post(self, *args, **kwargs) -> _FakeEpiasResponse:
        return _FakeEpiasResponse(self._payload, self._status_code)


def _mock_tgt_auth() -> MagicMock:
    auth = MagicMock()
    auth.get_auth_headers.return_value = {"TGT": "TGT-test-token"}
    auth.has_credentials.return_value = True
    auth.invalidate.return_value = None
    return auth


def test_epias_cas_auth_requests_tgt_from_body() -> None:
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=201, text="TGT-123-cas.epias.com.tr")

    auth = EpiasCasAuth(
        settings=Settings(
            epias_username=SecretStr("user@company.com.tr"),
            epias_password=SecretStr("secret"),
        ),
        session=session,
    )

    headers = auth.get_auth_headers()
    assert headers["TGT"] == "TGT-123-cas.epias.com.tr"
    session.post.assert_called_once()
    call_kwargs = session.post.call_args.kwargs
    assert call_kwargs["data"]["username"] == "user@company.com.tr"
    assert call_kwargs["data"]["password"] == "secret"


def test_epias_cas_auth_caches_tgt() -> None:
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=201, text="TGT-cache-test")

    auth = EpiasCasAuth(
        settings=Settings(
            epias_username=SecretStr("user"),
            epias_password=SecretStr("pass"),
        ),
        session=session,
    )

    auth.get_auth_headers()
    auth.get_auth_headers()
    assert session.post.call_count == 1


def test_epias_cas_auth_invalid_credentials() -> None:
    auth = EpiasCasAuth(settings=Settings())
    with pytest.raises(EpiasAuthError) as exc_info:
        auth.get_auth_headers()
    assert exc_info.value.reason == "credentials_missing"


def test_epias_v1_live_mapping_with_tgt() -> None:
    payload = {
        "items": [{"hour": f"{hour:02d}:00", "price": 3000 + hour} for hour in range(24)],
    }
    client = EpiasClient(
        settings=SimpleNamespace(
            epias_use_mock=False,
            epias_base_url="https://seffaflik.epias.com.tr/electricity-service/v1",
            epias_api_key=SimpleNamespace(get_secret_value=lambda: ""),
        ),
        session=_FakeEpiasSession(payload),
        auth=_mock_tgt_auth(),
    )
    result = client.fetch_day_ahead_ptf(date(2026, 7, 6))
    assert result.source == "epias-live"
    assert len(result.hours) == 24
    assert result.hours[0].ptf == 3000
    assert client.get_last_fetch_meta()["mode"] == "live"


def test_epias_credentials_missing_falls_back_to_mock() -> None:
    client = EpiasClient(
        settings=Settings(epias_use_mock=False),
        session=_FakeEpiasSession({}),
    )
    result = client.fetch_day_ahead_ptf(date(2026, 7, 6))
    assert result.source == "epias-mock:credentials_missing"
    assert client.get_last_fetch_meta()["reason"] == "credentials_missing"


def test_epias_auth_failed_after_tgt_retry() -> None:
    session = MagicMock()
    session.post.return_value = _FakeEpiasResponse({}, status_code=401)

    client = EpiasClient(
        settings=Settings(
            epias_use_mock=False,
            epias_username=SecretStr("user"),
            epias_password=SecretStr("pass"),
        ),
        session=session,
        auth=_mock_tgt_auth(),
    )
    result = client.fetch_day_ahead_ptf(date.today())
    assert result.source == "epias-mock:auth_failed"
    assert client.get_last_fetch_meta()["reason"] == "auth_failed"
