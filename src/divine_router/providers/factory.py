"""Adapter-family factory without provider-specific conditional sprawl."""

from __future__ import annotations

from collections.abc import Callable

import httpx

from divine_router.config.models import AdapterFamily, ProviderConfig
from divine_router.providers.anthropic import AnthropicProvider
from divine_router.providers.base import Provider
from divine_router.providers.gemini import GeminiProvider
from divine_router.providers.openai_compatible import OpenAICompatibleProvider


def create_provider(
    config: ProviderConfig,
    credential: str | None,
    client: httpx.AsyncClient | None = None,
) -> Provider:
    factories: dict[
        AdapterFamily, Callable[[ProviderConfig, str | None, httpx.AsyncClient | None], Provider]
    ] = {
        AdapterFamily.OPENAI: OpenAICompatibleProvider,
        AdapterFamily.ANTHROPIC: AnthropicProvider,
        AdapterFamily.GEMINI: GeminiProvider,
    }
    factory = factories.get(config.adapter)
    if factory is None:
        raise ValueError(f"adapter family {config.adapter} requires an extension package")
    return factory(config, credential, client)
