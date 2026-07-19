"""Application orchestration across routing and reliability layers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from divine_router.config.models import DivineConfig, ProviderConfig
from divine_router.errors import DivineError
from divine_router.models.canonical import CanonicalRequest, CanonicalResponse
from divine_router.models.streaming import StreamEvent
from divine_router.providers.base import Provider
from divine_router.reliability.executor import FallbackExecutor, ProviderTarget
from divine_router.routing.models import ModelCapabilities, ModelRecord, ModelRegistry
from divine_router.routing.router import AutoRouter, RouteConstraints
from divine_router.security.credentials import CredentialStore, CredentialUnavailable


@dataclass(frozen=True, slots=True)
class RouteMetadata:
    provider_id: str
    model: str
    route: str
    fallback_count: int = 0


class Gateway:
    def __init__(
        self,
        config: DivineConfig,
        providers: dict[str, Provider],
        registry: ModelRegistry,
    ) -> None:
        self.config = config
        self.providers = providers
        self.registry = registry
        health = {provider_id: provider.health for provider_id, provider in providers.items()}
        self.router = AutoRouter(registry, health)
        self.executor = FallbackExecutor(config.server.total_deadline_seconds)
        self.provider_configs = {provider.id: provider for provider in config.providers}

    @classmethod
    def from_config(
        cls,
        config: DivineConfig,
        credential_store: CredentialStore,
        provider_factory: object | None = None,
    ) -> Gateway:
        from divine_router.providers.factory import create_provider

        factory = provider_factory or create_provider
        providers: dict[str, Provider] = {}
        registry = ModelRegistry()
        for provider_config in config.providers:
            if not provider_config.enabled:
                continue
            credential: str | None = None
            if provider_config.credential:
                try:
                    credential = credential_store.resolve(provider_config.credential)
                except CredentialUnavailable:
                    continue
            provider = factory(provider_config, credential)  # type: ignore[operator]
            providers[provider_config.id] = provider
            capabilities = _capabilities(provider_config)
            for model_id in provider_config.models:
                registry.register(ModelRecord(provider_config.id, model_id, capabilities))
        return cls(config, providers, registry)

    async def complete(
        self, request: CanonicalRequest, constraints: RouteConstraints
    ) -> tuple[CanonicalResponse, RouteMetadata]:
        targets, route = self._targets(request, constraints)
        result = await self.executor.execute(request, targets)
        return result.response, RouteMetadata(
            result.provider_id, result.model, route, result.fallback_count
        )

    async def stream(
        self, request: CanonicalRequest, constraints: RouteConstraints
    ) -> tuple[AsyncIterator[StreamEvent], RouteMetadata]:
        targets, route = self._targets(request, constraints)
        result = await self.executor.prepare_stream(
            request,
            targets,
            self.config.server.streaming_idle_timeout_seconds,
        )
        return result.events, RouteMetadata(
            result.provider_id, result.model, route, result.fallback_count
        )

    def _targets(
        self, request: CanonicalRequest, constraints: RouteConstraints
    ) -> tuple[list[ProviderTarget], str]:
        if request.model == "auto":
            decision = self.router.auto(request, constraints)
            records = [decision.selected, *decision.fallbacks]
            route = decision.route
        else:
            records = self.router.explicit(request.model, self.config.aliases)
            route = f"explicit:{request.model}"
            if constraints.disable_fallback:
                records = records[:1]
        targets = []
        for record in records:
            provider = self.providers.get(record.provider_id)
            config = self.provider_configs.get(record.provider_id)
            if provider and config:
                targets.append(ProviderTarget(provider, record.model_id, config.retry))
        if not targets:
            raise DivineError(
                "the requested model has no enabled provider with an available credential",
                "invalid_request_error",
                503,
                "provider_unavailable",
                "model",
            )
        return targets, route


def _capabilities(config: ProviderConfig) -> ModelCapabilities:
    known = ModelCapabilities.__dataclass_fields__
    values = {key: value for key, value in config.capabilities.items() if key in known}
    return ModelCapabilities(**values)  # type: ignore[arg-type]
