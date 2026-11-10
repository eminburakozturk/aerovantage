"""Ortak yardımcı dekoratörler — retry ve cache."""

from __future__ import annotations

import functools
import random
import time
from typing import Any, Callable, TypeVar

from core.logger import get_logger

F = TypeVar("F", bound=Callable[..., Any])
_LOGGER = get_logger("core.utils")


def retry_on_failure(
    max_retries: int = 3,
    delay_seconds: float = 0.5,
    max_delay_seconds: float = 3.0,
    backoff_multiplier: float = 2.0,
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    """Geçici hatalarda fonksiyonu bounded backoff ile yeniden dener."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:  # type: ignore[misc]
                    if not isinstance(exc, Exception):
                        raise
                    last_error = exc
                    if attempt < max_retries:
                        base_delay = min(
                            max_delay_seconds,
                            delay_seconds * (backoff_multiplier ** attempt),
                        )
                        jitter = random.uniform(0.0, base_delay * 0.25)
                        sleep_seconds = base_delay + jitter
                        _LOGGER.warning(
                            "Retry denemesi: fn=%s attempt=%s/%s error=%s next_sleep=%.2fs",
                            func.__name__,
                            attempt + 1,
                            max_retries + 1,
                            exc,
                            sleep_seconds,
                        )
                        time.sleep(sleep_seconds)
                except Exception:
                    # Retry kapsamı dışında kalan hatalar doğrudan yükseltilir.
                    raise
            if last_error is not None:
                raise last_error
            raise RuntimeError(f"{func.__name__} başarısız oldu")

        return wrapper  # type: ignore[misc]

    return decorator


def cache_data(ttl_seconds: int = 60) -> Callable[[F], F]:
    """Sonuçları belirli süre bellek içinde önbelleğe alır.

    Instance method'larda ``self`` kimliği cache anahtarına dahil edilir;
    aksi halde farklı client ayarları birbirinin sonucunu çalar ve
    ``_last_fetch_meta`` gibi yan etkiler güncellenmez.
    """

    def decorator(func: F) -> F:
        cache_store: dict[str, tuple[float, Any]] = {}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            instance_key = id(args[0]) if args else None
            cache_key = repr(
                (func.__qualname__, instance_key, args[1:], tuple(sorted(kwargs.items())))
            )
            now = time.time()
            cached = cache_store.get(cache_key)
            if cached is not None:
                expires_at, value = cached
                if now < expires_at:
                    return value

            result = func(*args, **kwargs)
            cache_store[cache_key] = (now + ttl_seconds, result)
            return result

        wrapper.cache_clear = lambda: cache_store.clear()  # type: ignore[attr-defined]
        return wrapper  # type: ignore[misc]

    return decorator
