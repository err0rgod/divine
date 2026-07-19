"""Validated Divine routing-control headers."""

from __future__ import annotations

from fastapi import Request

from divine_router.errors import DivineError
from divine_router.routing.router import RouteConstraints


def _boolean(request: Request, name: str) -> bool:
    value = request.headers.get(name)
    if value is None:
        return False
    if value.lower() not in {"true", "false", "1", "0"}:
        raise DivineError(f"{name} must be true or false", param=name)
    return value.lower() in {"true", "1"}


def route_constraints(request: Request) -> RouteConstraints:
    max_cost_value = request.headers.get("x-divine-max-cost")
    max_cost: float | None = None
    if max_cost_value is not None:
        try:
            max_cost = float(max_cost_value)
        except ValueError as exc:
            raise DivineError(
                "x-divine-max-cost must be numeric", param="x-divine-max-cost"
            ) from exc
        if max_cost < 0:
            raise DivineError("x-divine-max-cost cannot be negative", param="x-divine-max-cost")
    prefer = request.headers.get("x-divine-prefer")
    if prefer not in {None, "cost", "latency", "quality"}:
        raise DivineError(
            "x-divine-prefer must be cost, latency, or quality", param="x-divine-prefer"
        )
    denied = frozenset(
        part.strip()
        for part in request.headers.get("x-divine-deny-provider", "").split(",")
        if part.strip()
    )
    return RouteConstraints(
        max_cost=max_cost,
        prefer=prefer,
        deny_providers=denied,
        disable_fallback=_boolean(request, "x-divine-disable-fallback"),
        disable_classifier=_boolean(request, "x-divine-disable-classifier"),
    )
