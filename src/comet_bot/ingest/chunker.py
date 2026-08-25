"""Split knowledge-base markdown files into breadcrumbed chunks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from comet_bot.ingest.metadata import enrich_metadata
from comet_bot.ingest.models import Chunk

_FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H1_PATTERN = re.compile(r"^# (.+)$", re.MULTILINE)
_SECTION_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)
_SLUGIFY_PATTERN = re.compile(r"[^\w\s-]")
_WHITESPACE_PATTERN = re.compile(r"[\s_]+")

INTRO_HEADING = "Introduction"


def slugify(text: str) -> str:
    """Turn a heading into a stable, URL-safe chunk id suffix."""
    normalized = _SLUGIFY_PATTERN.sub("", text.lower().strip())
    return _WHITESPACE_PATTERN.sub("-", normalized).strip("-")


def make_breadcrumb(document_title: str, section_heading: str) -> str:
    """Build the context label prepended to each chunk."""
    return f"Document: {document_title}\nSection: {section_heading}"


def build_chunk_text(document_title: str, section_heading: str, body: str) -> str:
    """Combine breadcrumb and section body into the final chunk text."""
    breadcrumb = make_breadcrumb(document_title, section_heading)
    content = body.strip()
    if not content:
        return breadcrumb
    return f"{breadcrumb}\n\n{content}"


def parse_front_matter(raw: str) -> tuple[dict[str, Any], str]:
    """Return YAML metadata and markdown body."""
    match = _FRONT_MATTER_PATTERN.match(raw)
    if not match:
        return {}, raw

    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        metadata = {}

    body = raw[match.end() :]
    return metadata, body


def _document_title(metadata: dict[str, Any], body: str) -> str:
    """Prefer front-matter title; fall back to the file's # heading."""
    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()

    h1_match = _H1_PATTERN.search(body)
    if h1_match:
        return h1_match.group(1).strip()

    return "Untitled Document"


def _strip_document_heading(body: str) -> str:
    """Remove the top-level # heading line; section content keeps ## headings."""
    return _H1_PATTERN.sub("", body, count=1).strip()


def _split_sections(body: str) -> list[tuple[str, str]]:
    """Split markdown body into (heading, content) pairs using ## boundaries."""
    parts = _SECTION_PATTERN.split(body)
    if len(parts) == 1:
        intro = parts[0].strip()
        if intro:
            return [(INTRO_HEADING, intro)]
        return []

    sections: list[tuple[str, str]] = []

    intro = parts[0].strip()
    if intro:
        sections.append((INTRO_HEADING, intro))

    for index in range(1, len(parts), 2):
        heading = parts[index].strip()
        content = parts[index + 1].strip() if index + 1 < len(parts) else ""
        sections.append((heading, content))

    return sections


def chunk_markdown(raw: str, source_file: str) -> list[Chunk]:
    """Parse one markdown file's contents into breadcrumbed chunks."""
    raw_metadata, body = parse_front_matter(raw)
    metadata = enrich_metadata(raw_metadata)
    document_title = _document_title(metadata, body)
    body_without_h1 = _strip_document_heading(body)
    sections = _split_sections(body_without_h1)

    chunks: list[Chunk] = []
    for heading, content in sections:
        chunk_id = f"{source_file}#{slugify(heading)}"
        chunks.append(
            Chunk(
                id=chunk_id,
                source_file=source_file,
                document_title=document_title,
                heading=heading,
                text=build_chunk_text(document_title, heading, content),
                metadata=metadata,
            )
        )

    return chunks


def chunk_file(path: Path) -> list[Chunk]:
    """Read a markdown file from disk and return its chunks."""
    raw = path.read_text(encoding="utf-8")
    return chunk_markdown(raw, source_file=path.name)
