"""Tests for knowledge-base markdown chunking."""

from comet_bot.ingest import chunk_markdown, load_chunks
from comet_bot.ingest.chunker import INTRO_HEADING, build_chunk_text, slugify


def test_load_chunks_produces_expected_volume() -> None:
    chunks = load_chunks()
    assert len(chunks) >= 40
    assert len({chunk.source_file for chunk in chunks}) == 14


def test_standard_return_window_chunk() -> None:
    chunks = load_chunks()
    matches = [
        chunk
        for chunk in chunks
        if chunk.source_file == "01-returns-policy-current.md"
        and chunk.heading == "Standard return window"
    ]
    assert len(matches) == 1

    chunk = matches[0]
    assert "30 calendar days" in chunk.text
    assert chunk.metadata["status"] == "active"
    assert chunk.metadata["policy_authority"] == "official"
    assert chunk.text.startswith("Document: Returns Policy\nSection: Standard return window")


def test_trailplus_return_window_chunk() -> None:
    chunks = load_chunks()
    matches = [
        chunk
        for chunk in chunks
        if chunk.source_file == "09-trailplus-membership.md"
        and chunk.heading == "Return window"
    ]
    assert len(matches) == 1
    assert "45-calendar-day" in matches[0].text


def test_legacy_policy_is_tagged_superseded() -> None:
    chunks = load_chunks()
    legacy_chunks = [c for c in chunks if c.source_file == "02-returns-policy-legacy.md"]
    assert legacy_chunks
    assert all(chunk.metadata["status"] == "superseded" for chunk in legacy_chunks)


def test_internal_migration_note_metadata() -> None:
    chunks = load_chunks()
    internal_chunks = [
        c for c in chunks if c.source_file == "14-internal-content-migration-notes.md"
    ]
    assert internal_chunks
    assert all(chunk.metadata["audience"] == "internal" for chunk in internal_chunks)
    assert any(chunk.heading == INTRO_HEADING for chunk in internal_chunks)


def test_breeze_tumbler_conflict_chunks_exist() -> None:
    chunks = load_chunks()
    care = [
        c
        for c in chunks
        if c.source_file == "11-product-care.md" and c.heading == "Breeze Tumbler"
    ]
    product_card = [
        c
        for c in chunks
        if c.source_file == "12-breeze-tumbler-product-card.md" and c.heading == "Cleaning"
    ]
    assert len(care) == 1
    assert len(product_card) == 1
    assert "hand-washed" in care[0].text
    assert "dishwasher safe" in product_card[0].text.lower()


def test_slugify_normalizes_heading() -> None:
    assert slugify("Standard return window") == "standard-return-window"
    assert slugify("Breeze Tumbler — Product Information") == "breeze-tumbler-product-information"


def test_build_chunk_text_includes_breadcrumb_and_body() -> None:
    text = build_chunk_text(
        "Returns Policy",
        "Standard return window",
        "Customers may return within 30 calendar days.",
    )
    assert text == (
        "Document: Returns Policy\n"
        "Section: Standard return window\n\n"
        "Customers may return within 30 calendar days."
    )


def test_chunk_markdown_without_front_matter() -> None:
    raw = "# Example Doc\n\n## First section\n\nHello world."
    chunks = chunk_markdown(raw, source_file="example.md")
    assert len(chunks) == 1
    assert chunks[0].heading == "First section"
    assert chunks[0].document_title == "Example Doc"
    assert "Hello world." in chunks[0].text
