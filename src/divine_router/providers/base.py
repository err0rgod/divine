"""Provider extension interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

from divine_router.models.canonical import CanonicalRequest, CanonicalResponse
from divine_router.models.streaming import StreamEvent


@dataclass(slots=True)
class ProviderHealth:
    provider_id: str
    healthy: bool = True
    score: float = 1.0
    consecutive_failures: int = 0
    last_checked: datetime | None = None
    message: str | None = None

    def success(self) -> None:
        self.healthy = True
        self.consecutive_failures = 0
        self.score = min(1.0, self.score + 0.05)
        self.last_checked = datetime.now(UTC)
        self.message = None

    def failure(self, message: str) -> None:
        self.consecutive_failures += 1
        self.score = max(0.0, self.score - 0.2)
        self.healthy = self.consecutive_failures < 3
        self.last_checked = datetime.now(UTC)
        self.message = message


class Provider(ABC):
    provider_id: str
    health: ProviderHealth

    @abstractmethod
    async def complete(self, request: CanonicalRequest, model: str) -> CanonicalResponse:
        raise NotImplementedError

    @abstractmethod
    def stream(self, request: CanonicalRequest, model: str) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError

    @abstractmethod
    async def discover_models(self) -> list[str]:
        raise NotImplementedError


class BedrockProviderExtension(Provider, ABC):
    """Extension point; authentication requires an optional AWS implementation."""


class VertexProviderExtension(Provider, ABC):
    """Extension point; authentication requires an optional Google implementation."""
