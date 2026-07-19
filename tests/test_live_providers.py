from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv

from divine_router.models.canonical import (
    CanonicalContent,
    CanonicalMessage,
    CanonicalRequest,
    ContentKind,
)
from divine_router.providers.catalog import built_in_providers
from divine_router.providers.factory import create_provider

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_explicit_live_provider() -> None:
    """Run one tiny explicit provider request only under the complete opt-in contract."""
    if os.environ.get("DIVINE_LIVE_TESTS") != "1":
        pytest.skip("set DIVINE_LIVE_TESTS=1 to enable provider calls")
    provider_id = os.environ.get("DIVINE_LIVE_PROVIDER")
    model = os.environ.get("DIVINE_LIVE_MODEL")
    if not provider_id or not model:
        pytest.skip("DIVINE_LIVE_PROVIDER and DIVINE_LIVE_MODEL are required")

    load_dotenv(Path.cwd() / ".env", override=False)
    templates = {provider.id: provider for provider in built_in_providers()}
    template = templates.get(provider_id)
    if template is None:
        pytest.fail(f"unknown live provider ID {provider_id!r}")
    if template.credential is None or template.credential.environment is None:
        pytest.skip("provider has no environment credential reference")
    credential = os.environ.get(template.credential.environment)
    if not credential or len(credential.strip()) < 16:
        pytest.skip("credential is missing or malformed")

    config = template.model_copy(
        update={"enabled": True, "timeout_seconds": 15.0, "models": [model]}
    )
    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=httpx.Timeout(config.timeout_seconds),
    ) as client:
        provider = create_provider(config, credential, client)
        discovered = await provider.discover_models()
        assert model in discovered
        response = await provider.complete(
            CanonicalRequest(
                model=f"{provider_id}/{model}",
                messages=[
                    CanonicalMessage(
                        role="user",
                        content=[
                            CanonicalContent(
                                kind=ContentKind.TEXT,
                                text="Reply with exactly DIVINE_LIVE_OK and nothing else.",
                            )
                        ],
                    )
                ],
                temperature=0,
                max_output_tokens=24,
            ),
            model,
        )
    text = "".join(part.text or "" for part in response.message.content).strip()
    assert "DIVINE_LIVE_OK" in text
    assert response.provider_response_id
