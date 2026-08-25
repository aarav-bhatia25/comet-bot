"""Document loading and chunking."""

from comet_bot.ingest.chunker import chunk_file, chunk_markdown
from comet_bot.ingest.loader import load_chunks
from comet_bot.ingest.metadata import derive_document_flags, enrich_metadata
from comet_bot.ingest.models import Chunk

__all__ = [
    "Chunk",
    "chunk_file",
    "chunk_markdown",
    "derive_document_flags",
    "enrich_metadata",
    "load_chunks",
]
