"""In-memory vector index over knowledge-base chunks."""

from __future__ import annotations

import numpy as np

from comet_bot.ingest import load_chunks
from comet_bot.ingest.models import Chunk
from comet_bot.retrieval.conflicts import detect_conflicts
from comet_bot.retrieval.embedder import DeterministicEmbedder, Embedder, OpenAIEmbedder
from comet_bot.retrieval.models import RetrievalResponse, SearchResult
from comet_bot.retrieval.ranking import final_score


def cosine_similarity(query_vector: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between one query vector and many stored vectors."""
    if matrix.size == 0:
        return np.empty(0, dtype=np.float32)

    query_norm = np.linalg.norm(query_vector)
    if query_norm == 0:
        return np.zeros(matrix.shape[0], dtype=np.float32)

    row_norms = np.linalg.norm(matrix, axis=1)
    safe_norms = np.where(row_norms == 0, 1.0, row_norms)
    normalized = matrix / safe_norms[:, np.newaxis]
    return normalized @ (query_vector / query_norm)


class KnowledgeIndex:
    """Embeds chunks once, then supports semantic search with metadata reranking."""

    def __init__(
        self,
        chunks: list[Chunk],
        embeddings: np.ndarray,
        embedder: Embedder,
    ) -> None:
        self.chunks = chunks
        self.embeddings = embeddings
        self.embedder = embedder

    @classmethod
    def build(
        cls,
        chunks: list[Chunk] | None = None,
        embedder: Embedder | None = None,
    ) -> KnowledgeIndex:
        """Load chunks, embed them, and return a searchable index."""
        chunk_list = chunks or load_chunks()
        if embedder is None:
            embedder = OpenAIEmbedder()

        if isinstance(embedder, DeterministicEmbedder):
            embedder.fit([chunk.text for chunk in chunk_list])

        texts = [chunk.text for chunk in chunk_list]
        embeddings = embedder.embed_texts(texts)
        return cls(chunks=chunk_list, embeddings=embeddings, embedder=embedder)

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        candidate_pool: int = 12,
    ) -> RetrievalResponse:
        """Return top-k chunks for a query, with precedence reranking applied."""
        if not self.chunks:
            return RetrievalResponse(query=query, results=(), conflicts=())

        query_vector = self.embedder.embed_texts([query])[0]
        similarities = cosine_similarity(query_vector, self.embeddings)

        pool_size = min(candidate_pool, len(self.chunks))
        candidate_indices = np.argsort(similarities)[::-1][:pool_size]

        ranked: list[SearchResult] = []
        for index in candidate_indices:
            chunk = self.chunks[int(index)]
            similarity = float(similarities[int(index)])
            meta_boost, keyword, score = final_score(similarity, chunk, query)
            ranked.append(
                SearchResult(
                    chunk=chunk,
                    similarity_score=similarity,
                    metadata_boost=meta_boost,
                    keyword_boost=keyword,
                    final_score=score,
                )
            )

        ranked.sort(key=lambda result: result.final_score, reverse=True)
        top_results = ranked[:top_k]
        conflicts = detect_conflicts(top_results, query=query)

        return RetrievalResponse(
            query=query,
            results=tuple(top_results),
            conflicts=tuple(conflicts),
        )
