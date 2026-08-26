"""Sanitized order lookup against orders.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from comet_bot.config import ORDERS_FILE
from comet_bot.tools.models import OrderLookupResult

_ORDER_ID_PATTERN = re.compile(r"ORD-\d{4}", re.IGNORECASE)
_CUSTOMER_SAFE_ITEM_FIELDS = ("name", "quantity", "final_sale")
_CUSTOMER_SAFE_TOP_LEVEL_FIELDS = (
    "order_id",
    "membership_tier",
    "placed_at",
    "status",
    "status_updated_at",
    "shipped_at",
    "delivered_at",
    "carrier",
    "tracking_number",
    "estimated_delivery",
    "customer_safe_message",
)


def normalize_order_id(raw: str | None) -> str | None:
    """Normalize harmless order ID differences; return None if no valid ID."""
    if raw is None:
        return None

    cleaned = raw.strip().upper()
    cleaned = re.sub(r"^[^A-Z0-9]+|[^A-Z0-9]+$", "", cleaned)
    match = _ORDER_ID_PATTERN.search(cleaned)
    if match is None:
        return None

    return match.group(0).upper()


def extract_order_id(text: str) -> str | None:
    """Find the first order ID in free-form user text."""
    return normalize_order_id(text)


def _sanitize_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for item in items:
        sanitized.append(
            {field: item[field] for field in _CUSTOMER_SAFE_ITEM_FIELDS if field in item}
        )
    return sanitized


def _sanitize_order_record(order: dict[str, Any]) -> dict[str, Any]:
    """Return only customer-safe fields from a raw order record."""
    sanitized: dict[str, Any] = {
        field: order[field]
        for field in _CUSTOMER_SAFE_TOP_LEVEL_FIELDS
        if field in order
    }
    if "items" in order:
        sanitized["items"] = _sanitize_items(order["items"])
    return sanitized


def _apply_status_rules(order: dict[str, Any]) -> tuple[dict[str, Any], bool, str | None]:
    """Adjust sanitized output based on authoritative status rules."""
    status = order.get("status")
    handoff = False
    guidance_parts: list[str] = []

    if status in {"cancelled", "returned"}:
        order["estimated_delivery"] = None
        guidance_parts.append(
            "The order status is authoritative. Ignore any stale carrier or delivery estimate fields."
        )

    if status == "shipped" and order.get("estimated_delivery") is None:
        guidance_parts.append(
            "The order has shipped, but no delivery estimate is currently available."
        )

    if status == "exception":
        handoff = True
        guidance_parts.append(
            "The order has an exception that requires support review. Recommend human handoff."
        )

    guidance = " ".join(guidance_parts) if guidance_parts else None
    return order, handoff, guidance


class OrderStore:
    """In-memory order lookup backed by orders.json."""

    def __init__(self, orders_file: Path | None = None) -> None:
        self.orders_file = orders_file or ORDERS_FILE
        self.snapshot_at: str | None = None
        self._orders_by_id: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        payload = json.loads(self.orders_file.read_text(encoding="utf-8"))
        self.snapshot_at = payload.get("snapshot_at")
        self._orders_by_id = {
            order["order_id"]: order for order in payload.get("orders", [])
        }

    def lookup(self, raw_order_id: str) -> OrderLookupResult:
        """Look up one order by ID and return a sanitized, rule-aware result."""
        normalized_id = normalize_order_id(raw_order_id)
        if normalized_id is None:
            return OrderLookupResult(
                found=False,
                order_id=None,
                error="invalid_order_id",
                guidance="Ask the customer to provide a valid order ID such as ORD-1007.",
            )

        raw_order = self._orders_by_id.get(normalized_id)
        if raw_order is None:
            return OrderLookupResult(
                found=False,
                order_id=normalized_id,
                handoff_recommended=True,
                error="order_not_found",
                guidance=(
                    "No order was found for that ID. Ask the customer to verify the order ID "
                    "or contact support."
                ),
            )

        sanitized = _sanitize_order_record(raw_order)
        sanitized, handoff, guidance = _apply_status_rules(sanitized)

        return OrderLookupResult(
            found=True,
            order_id=normalized_id,
            data=sanitized,
            handoff_recommended=handoff,
            guidance=guidance,
        )


_default_store: OrderStore | None = None


def get_order_store() -> OrderStore:
    """Return a shared OrderStore instance."""
    global _default_store
    if _default_store is None:
        _default_store = OrderStore()
    return _default_store


def lookup_order(raw_order_id: str, *, store: OrderStore | None = None) -> OrderLookupResult:
    """Convenience wrapper for a single order lookup."""
    active_store = store or get_order_store()
    return active_store.lookup(raw_order_id)
