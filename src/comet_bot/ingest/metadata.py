"""Derive retrieval-friendly flags from knowledge-base front matter."""

from __future__ import annotations

from typing import Any


def derive_document_flags(metadata: dict[str, Any]) -> dict[str, bool]:
    """Compute boolean flags used for source precedence and retrieval ranking."""
    status = metadata.get("status")
    authority = metadata.get("policy_authority")
    audience = metadata.get("audience")
    customer_answering = metadata.get("customer_answering", True)
    if customer_answering is None:
        customer_answering = True

    is_superseded = status == "superseded"
    is_internal = audience == "internal" or customer_answering is False
    is_customer_facing = audience == "customer" and customer_answering is not False
    is_authoritative = (
        status == "active"
        and authority == "official"
        and is_customer_facing
    )

    return {
        "is_authoritative": is_authoritative,
        "is_superseded": is_superseded,
        "is_internal": is_internal,
        "is_customer_facing": is_customer_facing,
    }


def enrich_metadata(raw_metadata: dict[str, Any]) -> dict[str, Any]:
    """Return front matter plus derived precedence flags."""
    enriched = dict(raw_metadata)
    enriched.update(derive_document_flags(raw_metadata))
    return enriched
