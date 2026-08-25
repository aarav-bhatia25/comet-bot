"""Data models for ingested knowledge-base chunks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Chunk:
    """One searchable section from a knowledge-base markdown file."""

    id: str
    source_file: str
    document_title: str
    heading: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def heading_path(self) -> str:
        """Human-readable path for citations: Document > Section."""
        return f"{self.document_title} > {self.heading}"
