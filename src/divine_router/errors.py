"""Normalized errors shared by adapters, routing, and protocol serializers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DivineError(Exception):
    message: str
    category: str = "invalid_request_error"
    status_code: int = 400
    code: str | None = None
    param: str | None = None

    def __str__(self) -> str:
        return self.message

    def openai_envelope(self) -> dict[str, Any]:
        return {
            "error": {
                "message": self.message,
                "type": self.category,
                "param": self.param,
                "code": self.code,
            }
        }

    def anthropic_envelope(self) -> dict[str, Any]:
        return {"type": "error", "error": {"type": self.category, "message": self.message}}


class AuthenticationError(DivineError):
    def __init__(self, message: str = "invalid Divine API token") -> None:
        super().__init__(message, "authentication_error", 401, "invalid_api_key")


class CompatibilityError(DivineError):
    def __init__(self, message: str, param: str | None = None) -> None:
        super().__init__(message, "invalid_request_error", 400, "unsupported_feature", param)


class ProviderError(DivineError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        category: str = "provider_error",
        retry_after: float | None = None,
        response_started: bool = False,
    ) -> None:
        super().__init__(message, category, status_code)
        self.retry_after = retry_after
        self.response_started = response_started
