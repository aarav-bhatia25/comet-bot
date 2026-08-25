"""Load and chunk all knowledge-base markdown files."""

from __future__ import annotations

from pathlib import Path

from comet_bot.config import KNOWLEDGE_BASE_DIR
from comet_bot.ingest.chunker import chunk_file
from comet_bot.ingest.models import Chunk


def load_chunks(knowledge_base_dir: Path | None = None) -> list[Chunk]:
    """Chunk every markdown file in the knowledge base, sorted by filename."""
    base_dir = knowledge_base_dir or KNOWLEDGE_BASE_DIR
    paths = sorted(base_dir.glob("*.md"))

    chunks: list[Chunk] = []
    for path in paths:
        chunks.extend(chunk_file(path))

    return chunks
