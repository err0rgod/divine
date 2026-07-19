"""Versioned, validated Divine Router configuration schema."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from divine_router.constants import DEFAULT_HOST, DEFAULT_PORT, SCHEMA_VERSION


class AdapterFamily(StrEnum):
    OPENAI = "openai-compatible"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    BEDROCK = "bedrock-extension"
    VERTEX = "vertex-extension"


class VerificationStatus(StrEnum):
    VERIFIED_LIVE = "verified-live"
    VERIFIED_MOCKED = "verified-mocked"
    COMPATIBLE_UNVERIFIED = "compatible-unverified"
    EXPERIMENTAL = "experimental"
    DISABLED = "disabled"


class CredentialReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keyring_name: str | None = None
    environment: str | None = None
    encrypted_file_name: str | None = None

    @model_validator(mode="after")
    def require_reference(self) -> CredentialReference:
        if not any((self.keyring_name, self.environment, self.encrypted_file_name)):
            raise ValueError("at least one credential reference is required")
        return self


class RetryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay_seconds: float = Field(default=0.25, ge=0, le=30)
    max_delay_seconds: float = Field(default=8.0, ge=0, le=120)


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    display_name: str
    adapter: AdapterFamily
    base_url: str
    credential: CredentialReference | None = None
    auth_style: str = "bearer"
    additional_headers: dict[str, str] = Field(default_factory=dict)
    model_discovery_path: str | None = None
    timeout_seconds: float = Field(default=60, gt=0, le=600)
    enabled: bool = False
    capabilities: dict[str, bool | int] = Field(default_factory=dict)
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    trust_level: str = "external"
    verification: VerificationStatus = VerificationStatus.COMPATIBLE_UNVERIFIED
    models: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        if not value.startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ValueError("provider base URL must use HTTPS unless it is local")
        return value.rstrip("/")


class ServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = DEFAULT_HOST
    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    allow_remote_bind: bool = False
    request_body_limit_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    rate_limit_per_minute: int = Field(default=120, ge=1)
    total_deadline_seconds: float = Field(default=120, gt=0)
    streaming_idle_timeout_seconds: float = Field(default=45, gt=0)

    @model_validator(mode="after")
    def require_remote_opt_in(self) -> ServerConfig:
        if self.host == "0.0.0.0" and not self.allow_remote_bind:  # noqa: S104
            raise ValueError("binding to 0.0.0.0 requires allow_remote_bind=true")
        return self


class ClassifierConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    provider: str = "groq"
    model: str | None = None
    timeout_seconds: float = Field(default=3, gt=0, le=15)
    max_output_tokens: int = Field(default=100, ge=20, le=300)
    sample_character_limit: int = Field(default=2000, ge=100, le=10000)


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str = "INFO"
    content_logging: bool = False


class DivineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    server: ServerConfig = Field(default_factory=ServerConfig)
    providers: list[ProviderConfig] = Field(default_factory=list)
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    fallback_chains: dict[str, list[str]] = Field(default_factory=dict)
    routing: dict[str, Any] = Field(default_factory=dict)
    classifier: ClassifierConfig = Field(default_factory=ClassifierConfig)
    cli_profiles: dict[str, dict[str, Any]] = Field(default_factory=dict)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    usage_retention_days: int = Field(default=90, ge=1, le=3650)
    pricing_as_of: str | None = None
    pricing: dict[str, dict[str, float]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_provider_ids(self) -> DivineConfig:
        provider_ids = [provider.id for provider in self.providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider IDs must be unique")
        return self
