"""Embedding, indexing, and semantic search over knowledge-base chunks."""

from comet_bot.retrieval.conflicts import detect_conflicts
from comet_bot.retrieval.embedder import DeterministicEmbedder, OpenAIEmbedder
from comet_bot.retrieval.index import KnowledgeIndex
from comet_bot.retrieval.models import RetrievalResponse, SearchResult, SourceConflict
from comet_bot.retrieval.ranking import final_score, keyword_boost, metadata_boost

__all__ = [
    "DeterministicEmbedder",
    "KnowledgeIndex",
    "OpenAIEmbedder",
    "RetrievalResponse",
    "SearchResult",
    "SourceConflict",
    "detect_conflicts",
    "final_score",
    "keyword_boost",
    "metadata_boost",
]
