"""Shared HTTP authentication and provider error normalization."""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from time import time

import httpx

from divine_router.config.models import ProviderConfig
from divine_router.errors import ProviderError


def authentication(
    config: ProviderConfig, credential: str | None
) -> tuple[dict[str, str], dict[str, str]]:
    headers = dict(config.additional_headers)
    params: dict[str, str] = {}
    if not credential:
        return headers, params
    match config.auth_style:
        case "bearer":
            headers["Authorization"] = f"Bearer {credential}"
        case "x-api-key":
            headers["x-api-key"] = credential
        case "api-key":
            headers["api-key"] = credential
        case "x-goog-api-key":
            headers["x-goog-api-key"] = credential
        case "query-key":
            params["key"] = credential
        case "none":
            pass
        case _:
            raise ProviderError("provider has an unsupported authentication style")
    return headers, params


def retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, parsedate_to_datetime(value).timestamp() - time())
        except (TypeError, ValueError, OverflowError):
            return None


def provider_error(response: httpx.Response) -> ProviderError:
    category = "rate_limit_error" if response.status_code == 429 else "provider_error"
    if response.status_code in {401, 403}:
        category = "provider_authentication_error"
    message = f"provider returned HTTP {response.status_code}"
    try:
        body = response.json()
        candidate = body.get("error", {}).get("message") if isinstance(body, dict) else None
        if isinstance(candidate, str) and candidate:
            message = candidate[:500]
    except ValueError:
        pass
    return ProviderError(
        message,
        status_code=502 if response.status_code >= 500 else response.status_code,
        category=category,
        retry_after=retry_after_seconds(response),
    )
