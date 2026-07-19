"""Centralized secret redaction for logs and error messages."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "api_key",
        "token",
        "access_token",
        "webhook",
        "secret",
    }
)
TOKEN_PATTERNS = (
    re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+\-/=]+"),
    re.compile(r"\b(sk-[A-Za-z0-9_-]{8,})\b"),
)


def redact_text(value: str, known_secrets: tuple[str, ...] = ()) -> str:
    result = value
    for secret in known_secrets:
        if secret:
            result = result.replace(secret, REDACTED)
    for pattern in TOKEN_PATTERNS:
        result = pattern.sub(
            lambda match: f"{match.group(1) if match.lastindex else ''}{REDACTED}", result
        )
    return result


def redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, item in value.items():
        lowered = key.lower()
        if lowered in SENSITIVE_KEYS or any(part in lowered for part in ("token", "secret", "key")):
            redacted[key] = REDACTED
        elif isinstance(item, Mapping):
            redacted[key] = redact_mapping(item)
        elif isinstance(item, list):
            redacted[key] = [
                redact_mapping(entry) if isinstance(entry, Mapping) else entry for entry in item
            ]
        elif isinstance(item, str):
            redacted[key] = redact_text(item)
        else:
            redacted[key] = item
    return redacted


def redact_url(value: str) -> str:
    parts = urlsplit(value)
    query_items = [
        (key, REDACTED if key.lower() in SENSITIVE_KEYS else item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
    ]
    query = urlencode(query_items)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
