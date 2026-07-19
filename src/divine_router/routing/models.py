"""Model capability records and expiring discovery cache."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from divine_router.errors import DivineError


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    chat: bool = True
    responses: bool = False
    streaming: bool = True
    tools: bool = False
    parallel_tools: bool = False
    structured_output: bool = False
    json_mode: bool = False
    vision: bool = False
    audio_input: bool = False
    reasoning: bool = False
    reasoning_content: bool = False
    prompt_caching: bool = False
    token_counting: bool = False
    embeddings: bool = False
    context_window: int | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ModelRecord:
    provider_id: str
    model_id: str
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None
    typical_latency_ms: float | None = None
    enabled: bool = True
    trust_level: str = "external"

    @property
    def qualified_id(self) -> str:
        return f"{self.provider_id}/{self.model_id}"


@dataclass(slots=True)
class DiscoveryEntry:
    models: list[ModelRecord]
    expires_at: datetime


class ModelRegistry:
    def __init__(self, ttl_seconds: int = 900) -> None:
        self.ttl = timedelta(seconds=ttl_seconds)
        self._models: dict[str, ModelRecord] = {}
        self._discovery: dict[str, DiscoveryEntry] = {}

    def register(self, model: ModelRecord) -> None:
        self._models[model.qualified_id] = model

    def all(self) -> list[ModelRecord]:
        return list(self._models.values())

    def get(self, qualified_id: str) -> ModelRecord:
        try:
            return self._models[qualified_id]
        except KeyError as exc:
            raise DivineError(
                f"unknown model: {qualified_id}",
                "invalid_request_error",
                404,
                "model_not_found",
                "model",
            ) from exc

    def cache_discovery(self, provider_id: str, models: list[ModelRecord]) -> None:
        self._discovery[provider_id] = DiscoveryEntry(models, datetime.now(UTC) + self.ttl)
        for model in models:
            self.register(model)

    def discovered(self, provider_id: str) -> list[ModelRecord] | None:
        entry = self._discovery.get(provider_id)
        if not entry or entry.expires_at <= datetime.now(UTC):
            return None
        return entry.models
