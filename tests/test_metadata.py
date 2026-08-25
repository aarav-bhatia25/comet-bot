"""Tests for derived knowledge-base metadata flags."""

from comet_bot.ingest import derive_document_flags, enrich_metadata, load_chunks


def test_current_returns_policy_is_authoritative() -> None:
    chunks = load_chunks()
    current = [
        c for c in chunks if c.source_file == "01-returns-policy-current.md"
    ]
    assert current
    assert all(chunk.metadata["is_authoritative"] is True for chunk in current)
    assert all(chunk.metadata["is_customer_facing"] is True for chunk in current)
    assert all(chunk.metadata["is_superseded"] is False for chunk in current)
    assert all(chunk.metadata["is_internal"] is False for chunk in current)


def test_legacy_returns_policy_is_not_authoritative() -> None:
    chunks = load_chunks()
    legacy = [c for c in chunks if c.source_file == "02-returns-policy-legacy.md"]
    assert legacy
    assert all(chunk.metadata["is_authoritative"] is False for chunk in legacy)
    assert all(chunk.metadata["is_superseded"] is True for chunk in legacy)


def test_internal_migration_notes_are_internal_only() -> None:
    chunks = load_chunks()
    internal = [
        c for c in chunks if c.source_file == "14-internal-content-migration-notes.md"
    ]
    assert internal
    assert all(chunk.metadata["is_authoritative"] is False for chunk in internal)
    assert all(chunk.metadata["is_internal"] is True for chunk in internal)
    assert all(chunk.metadata["is_customer_facing"] is False for chunk in internal)


def test_support_escalation_is_internal_not_authoritative() -> None:
    chunks = load_chunks()
    escalation = [c for c in chunks if c.source_file == "13-support-escalation.md"]
    assert escalation
    assert all(chunk.metadata["is_internal"] is True for chunk in escalation)
    assert all(chunk.metadata["is_authoritative"] is False for chunk in escalation)


def test_conflicting_breeze_sources_remain_authoritative() -> None:
    chunks = load_chunks()
    care = [c for c in chunks if c.source_file == "11-product-care.md"]
    product_card = [c for c in chunks if c.source_file == "12-breeze-tumbler-product-card.md"]
    assert all(chunk.metadata["is_authoritative"] is True for chunk in care)
    assert all(chunk.metadata["is_authoritative"] is True for chunk in product_card)


def test_derive_document_flags_from_raw_metadata() -> None:
    flags = derive_document_flags(
        {
            "status": "active",
            "policy_authority": "official",
            "audience": "customer",
        }
    )
    assert flags == {
        "is_authoritative": True,
        "is_superseded": False,
        "is_internal": False,
        "is_customer_facing": True,
    }


def test_enrich_metadata_preserves_raw_fields() -> None:
    raw = {
        "status": "draft",
        "audience": "internal",
        "policy_authority": "none",
        "customer_answering": False,
        "document_id": "MIG-TEST-04",
    }
    enriched = enrich_metadata(raw)
    assert enriched["document_id"] == "MIG-TEST-04"
    assert enriched["is_authoritative"] is False
    assert enriched["is_internal"] is True
