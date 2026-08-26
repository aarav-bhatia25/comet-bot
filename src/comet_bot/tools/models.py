"""Data models for order lookup tool results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OrderLookupResult:
    """Sanitized result from an order status lookup."""

    found: bool
    order_id: str | None
    data: dict[str, Any] | None = None
    handoff_recommended: bool = False
    guidance: str | None = None
    error: str | None = None

    def to_tool_dict(self) -> dict[str, Any]:
        """JSON-serializable payload safe to pass into model context."""
        payload: dict[str, Any] = {
            "found": self.found,
            "order_id": self.order_id,
            "handoff_recommended": self.handoff_recommended,
        }
        if self.data is not None:
            payload["data"] = self.data
        if self.guidance is not None:
            payload["guidance"] = self.guidance
        if self.error is not None:
            payload["error"] = self.error
        return payload
