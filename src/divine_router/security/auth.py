"""Independent Divine API token generation and constant-time validation."""

from __future__ import annotations

import os
import secrets
from hmac import compare_digest
from pathlib import Path

from fastapi import Request

from divine_router.errors import AuthenticationError


def load_or_create_token(path: Path) -> str:
    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if len(token) >= 32:
            return token
        raise AuthenticationError("stored Divine API token is invalid")
    path.parent.mkdir(parents=True, exist_ok=True)
    token = f"divine_{secrets.token_urlsafe(32)}"
    path.write_text(token, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return token


def supplied_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("x-api-key")


def authenticate_request(request: Request, expected: str) -> None:
    supplied = supplied_token(request)
    if not supplied or not compare_digest(supplied, expected):
        raise AuthenticationError()
