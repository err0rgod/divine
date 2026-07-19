"""Deterministic filtering followed by task-aware model scoring."""

from __future__ import annotations

from dataclasses import dataclass, field

from divine_router.errors import DivineError
from divine_router.models.canonical import CanonicalRequest, ContentKind
from divine_router.providers.base import ProviderHealth
from divine_router.routing.classifier import TaskClass, classify
from divine_router.routing.models import ModelRecord, ModelRegistry


@dataclass(frozen=True, slots=True)
class RouteConstraints:
    max_cost: float | None = None
    prefer: str | None = None
    deny_providers: frozenset[str] = frozenset()
    allow_providers: frozenset[str] = frozenset()
    disable_fallback: bool = False
    disable_classifier: bool = False


@dataclass(frozen=True, slots=True)
class RouteDecision:
    selected: ModelRecord
    route: str
    task_class: TaskClass
    fallbacks: tuple[ModelRecord, ...] = field(default_factory=tuple)


class AutoRouter:
    def __init__(
        self,
        registry: ModelRegistry,
        provider_health: dict[str, ProviderHealth] | None = None,
    ) -> None:
        self.registry = registry
        self.provider_health = provider_health or {}

    def explicit(self, requested: str, aliases: dict[str, list[str]]) -> list[ModelRecord]:
        candidates = aliases.get(requested, [requested])
        if not candidates:
            raise DivineError("model alias has no candidates", param="model")
        return [self.registry.get(candidate) for candidate in candidates]

    def auto(self, request: CanonicalRequest, constraints: RouteConstraints) -> RouteDecision:
        task_class = classify(request)
        candidates = [
            model for model in self.registry.all() if self._eligible(model, request, constraints)
        ]
        if not candidates:
            raise DivineError(
                "no configured model satisfies the request capabilities and routing constraints",
                "invalid_request_error",
                422,
                "no_route",
            )
        ranked = sorted(
            candidates, key=lambda model: self._score(model, task_class, constraints), reverse=True
        )
        return RouteDecision(
            selected=ranked[0],
            route=f"auto:{task_class.value}",
            task_class=task_class,
            fallbacks=tuple(() if constraints.disable_fallback else ranked[1:]),
        )

    def _eligible(
        self, model: ModelRecord, request: CanonicalRequest, constraints: RouteConstraints
    ) -> bool:
        if not model.enabled or model.provider_id in constraints.deny_providers:
            return False
        if constraints.allow_providers and model.provider_id not in constraints.allow_providers:
            return False
        health = self.provider_health.get(model.provider_id)
        if health and not health.healthy:
            return False
        capabilities = model.capabilities
        if request.stream and not capabilities.streaming:
            return False
        if request.tools and not capabilities.tools:
            return False
        if request.response_format and not (
            capabilities.structured_output or capabilities.json_mode
        ):
            return False
        if (
            any(
                part.kind is ContentKind.IMAGE
                for message in request.messages
                for part in message.content
            )
            and not capabilities.vision
        ):
            return False
        if request.max_output_tokens and capabilities.max_output_tokens:
            if request.max_output_tokens > capabilities.max_output_tokens:
                return False
        estimated = (model.input_cost_per_million or 0) + (model.output_cost_per_million or 0)
        return constraints.max_cost is None or estimated <= constraints.max_cost

    @staticmethod
    def _score(model: ModelRecord, task_class: TaskClass, constraints: RouteConstraints) -> float:
        score = 1.0
        cost = (model.input_cost_per_million or 0) + (model.output_cost_per_million or 0)
        latency = model.typical_latency_ms or 1000
        if task_class in {TaskClass.CODING, TaskClass.DEBUGGING, TaskClass.DEEP_REASONING}:
            score += 1.5 if model.capabilities.reasoning else 0
        if task_class is TaskClass.VISION:
            score += 2 if model.capabilities.vision else 0
        if task_class is TaskClass.AGENTIC_TOOL_USE:
            score += 1.5 if model.capabilities.parallel_tools else 0.5
        if task_class is TaskClass.LOW_COST:
            score -= cost / 10
        if task_class is TaskClass.LOW_LATENCY:
            score -= latency / 1000
        if constraints.prefer == "cost":
            score -= cost / 10
        elif constraints.prefer == "latency":
            score -= latency / 1000
        elif constraints.prefer == "quality" and model.capabilities.reasoning:
            score += 1
        return score
