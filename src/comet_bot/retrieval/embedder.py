"""Text embedding providers."""

from __future__ import annotations

import re
from typing import Protocol

import numpy as np
from openai import OpenAI

from comet_bot.config import Settings, load_settings

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    """Protocol for components that turn text into dense vectors."""

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return one embedding vector per input string."""


class OpenAIEmbedder:
    """Embed text with the configured OpenAI embedding model."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIEmbedder")

        self.client = OpenAI(api_key=self.settings.openai_api_key)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        response = self.client.embeddings.create(
            model=self.settings.embedding_model,
            input=texts,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = [item.embedding for item in ordered]
        return np.asarray(vectors, dtype=np.float32)


class DeterministicEmbedder:
    """Bag-of-words embedder for offline tests (no API calls)."""

    def __init__(self, vocabulary: list[str] | None = None) -> None:
        self._vocabulary = vocabulary or []

    def fit(self, texts: list[str]) -> DeterministicEmbedder:
        tokens: set[str] = set()
        for text in texts:
            tokens.update(_tokenize(text))
        self._vocabulary = sorted(tokens)
        return self

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not self._vocabulary:
            raise ValueError("DeterministicEmbedder must be fit before use")

        token_to_index = {token: index for index, token in enumerate(self._vocabulary)}
        matrix = np.zeros((len(texts), len(self._vocabulary)), dtype=np.float32)

        for row, text in enumerate(texts):
            for token in _tokenize(text):
                index = token_to_index.get(token)
                if index is not None:
                    matrix[row, index] += 1.0

        return matrix


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))
