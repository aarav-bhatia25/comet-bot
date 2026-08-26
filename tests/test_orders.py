"""Tests for sanitized order lookup."""

from __future__ import annotations

import json

from comet_bot.tools import (
    OrderStore,
    extract_order_id,
    lookup_order,
    normalize_order_id,
)


def test_normalize_order_id_handles_case_and_whitespace() -> None:
    assert normalize_order_id("  ord-1007  ") == "ORD-1007"
    assert normalize_order_id("(ORD-1003).") == "ORD-1003"


def test_normalize_order_id_rejects_invalid_values() -> None:
    assert normalize_order_id("ORD-999") is None
    assert normalize_order_id("not-an-order") is None
    assert normalize_order_id("") is None


def test_extract_order_id_from_free_form_text() -> None:
    assert extract_order_id("Can you check status for   ord-1003  ?") == "ORD-1003"


def test_lookup_ord_1007_returns_customer_safe_fields_only() -> None:
    result = lookup_order("ORD-1007")
    assert result.found is True
    assert result.data is not None
    assert result.data["status"] == "shipped"
    assert result.data["carrier"] == "UPS"
    assert result.data["estimated_delivery"] == "2026-08-22"
    assert "customer" not in result.data
    assert "internal" not in result.data
    assert "risk_score" not in json.dumps(result.to_tool_dict())


def test_lookup_cancelled_order_clears_stale_eta() -> None:
    result = lookup_order("ORD-1004")
    assert result.found is True
    assert result.data is not None
    assert result.data["status"] == "cancelled"
    assert result.data["estimated_delivery"] is None
    assert "stale" in (result.guidance or "").lower()


def test_lookup_returned_order_clears_delivery_estimate() -> None:
    result = lookup_order("ORD-1008")
    assert result.data is not None
    assert result.data["status"] == "returned"
    assert result.data["estimated_delivery"] is None


def test_lookup_shipped_without_eta() -> None:
    result = lookup_order("ORD-1011")
    assert result.data is not None
    assert result.data["status"] == "shipped"
    assert result.data["carrier"] == "Canada Post"
    assert result.data["estimated_delivery"] is None
    assert result.guidance is not None
    assert "estimate" in result.guidance.lower()


def test_lookup_exception_recommends_handoff() -> None:
    result = lookup_order("ORD-1010")
    assert result.data is not None
    assert result.data["status"] == "exception"
    assert result.handoff_recommended is True


def test_lookup_unknown_order() -> None:
    result = lookup_order("ORD-9999")
    assert result.found is False
    assert result.order_id == "ORD-9999"
    assert result.handoff_recommended is True
    assert result.error == "order_not_found"


def test_lookup_invalid_order_id() -> None:
    result = lookup_order("ORD-ABC")
    assert result.found is False
    assert result.error == "invalid_order_id"


def test_order_store_loads_snapshot_at() -> None:
    store = OrderStore()
    assert store.snapshot_at == "2026-08-15T12:00:00Z"
    assert len(store._orders_by_id) == 12
