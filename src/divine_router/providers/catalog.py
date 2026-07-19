"""Editable built-in provider templates.

URLs are provider API roots documented by their operators as of 2026-07-19. Templates do not
hardcode current model IDs and remain disabled until the operator opts in.
"""

from __future__ import annotations

from divine_router.config.models import (
    AdapterFamily,
    CredentialReference,
    ProviderConfig,
    VerificationStatus,
)


def _provider(
    provider_id: str,
    name: str,
    base_url: str,
    environment: str | None,
    *,
    adapter: AdapterFamily = AdapterFamily.OPENAI,
    auth_style: str = "bearer",
    discovery: str | None = "/models",
    verification: VerificationStatus = VerificationStatus.COMPATIBLE_UNVERIFIED,
    trust: str = "direct",
    notes: str | None = None,
) -> ProviderConfig:
    credential = CredentialReference(environment=environment) if environment else None
    return ProviderConfig(
        id=provider_id,
        display_name=name,
        adapter=adapter,
        base_url=base_url,
        credential=credential,
        auth_style=auth_style,
        model_discovery_path=discovery,
        enabled=False,
        verification=verification,
        trust_level=trust,
        notes=notes,
    )


def built_in_providers() -> list[ProviderConfig]:
    """Return new configuration objects for the complete initial catalogue."""
    return [
        _provider("openai", "OpenAI", "https://api.openai.com/v1", "OPENAI_API_KEY"),
        _provider(
            "anthropic",
            "Anthropic",
            "https://api.anthropic.com/v1",
            "ANTHROPIC_API_KEY",
            adapter=AdapterFamily.ANTHROPIC,
            auth_style="x-api-key",
        ),
        _provider(
            "gemini",
            "Google Gemini",
            "https://generativelanguage.googleapis.com/v1beta",
            "GEMINI_API_KEY",
            adapter=AdapterFamily.GEMINI,
            auth_style="x-goog-api-key",
            discovery=None,
        ),
        _provider("deepseek", "DeepSeek", "https://api.deepseek.com", "DEEPSEEK_API_KEY"),
        _provider("groq", "Groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
        _provider("cerebras", "Cerebras", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY"),
        _provider(
            "nvidia",
            "NVIDIA API Catalog",
            "https://integrate.api.nvidia.com/v1",
            "NVIDIA_API_KEY",
        ),
        _provider("mistral", "Mistral AI", "https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
        _provider("xai", "xAI", "https://api.x.ai/v1", "XAI_API_KEY"),
        _provider("together", "Together AI", "https://api.together.ai/v1", "TOGETHER_API_KEY"),
        _provider(
            "fireworks",
            "Fireworks AI",
            "https://api.fireworks.ai/inference/v1",
            "FIREWORKS_API_KEY",
        ),
        _provider("sambanova", "SambaNova", "https://api.sambanova.ai/v1", "SAMBANOVA_API_KEY"),
        _provider(
            "cohere",
            "Cohere Compatibility API",
            "https://api.cohere.ai/compatibility/v1",
            "COHERE_API_KEY",
        ),
        _provider(
            "huggingface",
            "Hugging Face Inference Providers",
            "https://router.huggingface.co/v1",
            "HUGGINGFACE_API_KEY",
        ),
        _provider(
            "cloudflare",
            "Cloudflare Workers AI",
            "https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/ai/v1",
            "CLOUDFLARE_API_TOKEN",
            discovery=None,
            verification=VerificationStatus.EXPERIMENTAL,
            notes=(
                "Replace ACCOUNT_ID with the account-specific Workers AI base URL before enabling."
            ),
        ),
        _provider(
            "perplexity",
            "Perplexity",
            "https://api.perplexity.ai",
            "PERPLEXITY_API_KEY",
            discovery=None,
        ),
        _provider(
            "azure-openai",
            "Azure OpenAI",
            "https://RESOURCE_NAME.openai.azure.com/openai/v1",
            "AZURE_OPENAI_API_KEY",
            auth_style="api-key",
            notes="Replace RESOURCE_NAME with the Azure resource host before enabling.",
        ),
        _provider(
            "ollama",
            "Ollama",
            "http://127.0.0.1:11434/v1",
            None,
            auth_style="none",
            trust="local",
        ),
        _provider(
            "lm-studio",
            "LM Studio",
            "http://127.0.0.1:1234/v1",
            None,
            auth_style="none",
            trust="local",
        ),
        _provider(
            "bedrock",
            "AWS Bedrock extension",
            "https://bedrock-runtime.REGION.amazonaws.com",
            None,
            adapter=AdapterFamily.BEDROCK,
            auth_style="none",
            discovery=None,
            verification=VerificationStatus.EXPERIMENTAL,
            notes="Requires an extension implementing AWS SigV4 and a concrete region.",
        ),
        _provider(
            "vertex",
            "Google Vertex AI extension",
            "https://LOCATION-aiplatform.googleapis.com/v1",
            None,
            adapter=AdapterFamily.VERTEX,
            auth_style="none",
            discovery=None,
            verification=VerificationStatus.EXPERIMENTAL,
            notes="Requires an extension implementing Google ADC and a concrete location/project.",
        ),
        _provider(
            "openrouter",
            "OpenRouter",
            "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY",
            trust="aggregator",
        ),
        _provider(
            "agentrouter",
            "AgentRouter",
            "https://api.agentrouter.to/api/agentic-api",
            "AGENTROUTER_API_KEY",
            discovery=None,
            verification=VerificationStatus.DISABLED,
            trust="aggregator",
            notes=(
                "Current official API is capability-oriented, not verified as OpenAI-compatible; "
                "template remains disabled pending a dedicated adapter."
            ),
        ),
        _provider(
            "forge",
            "Forge at forge-ai.space",
            "https://www.forge-ai.space",
            "FORGE_API_KEY",
            discovery=None,
            verification=VerificationStatus.DISABLED,
            trust="aggregator",
            notes=(
                "No official API base path was discoverable; configure a documented URL before "
                "enabling."
            ),
        ),
        _provider(
            "bluesminds",
            "BluesMinds",
            "https://api.bluesminds.com/v1",
            "BLUESMINDS_API_KEY",
            trust="aggregator",
        ),
        _provider(
            "custom-openai",
            "Custom OpenAI-compatible",
            "https://example.invalid/v1",
            "DIVINE_CUSTOM_OPENAI_API_KEY",
            discovery=None,
            verification=VerificationStatus.DISABLED,
            trust="custom",
            notes="Replace the example URL and credential reference before enabling.",
        ),
        _provider(
            "custom-anthropic",
            "Custom Anthropic-compatible",
            "https://example.invalid/v1",
            "DIVINE_CUSTOM_ANTHROPIC_API_KEY",
            adapter=AdapterFamily.ANTHROPIC,
            auth_style="x-api-key",
            discovery=None,
            verification=VerificationStatus.DISABLED,
            trust="custom",
            notes="Replace the example URL and credential reference before enabling.",
        ),
    ]
