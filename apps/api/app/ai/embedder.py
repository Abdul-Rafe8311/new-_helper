"""Embeddings behind a protocol.

FastEmbedEmbedder loads the ONNX model lazily and only the pipeline uses it: the API
process stays under its memory limit by reading vectors stored in Postgres instead.
"""

import hashlib
import math
import struct
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar, Protocol

from app.models.user import EMBEDDING_DIM

BATCH_SIZE = 64
BODY_WORDS = 400
DEFAULT_CACHE_DIR = "~/.cache/fastembed"


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def article_embedding_text(title: str, excerpt: str | None, content: str | None) -> str:
    """Title + excerpt + the first 400 words of the body."""
    body = " ".join((content or "").split()[:BODY_WORDS])
    return "\n".join(part for part in (title.strip(), (excerpt or "").strip(), body) if part)


class FastEmbedEmbedder:
    """BAAI/bge-small-en-v1.5 (384 dims) via fastembed, loaded on first use."""

    _models: ClassVar[dict[str, Any]] = {}  # process-wide singleton per model name

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        dim: int = EMBEDDING_DIM,
        cache_dir: str = DEFAULT_CACHE_DIR,
    ):
        self.model_name = model_name
        self.dim = dim
        self.cache_dir = str(Path(cache_dir).expanduser())

    def _model(self) -> Any:
        if self.model_name not in self._models:
            from fastembed import TextEmbedding  # heavy import, kept out of the API process

            self._models[self.model_name] = TextEmbedding(
                model_name=self.model_name, cache_dir=self.cache_dir
            )
        return self._models[self.model_name]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._model()
        vectors = model.embed(list(texts), batch_size=BATCH_SIZE)
        return [[float(x) for x in vec] for vec in vectors]


class FakeEmbedder:
    """Deterministic, hash-based unit vectors for tests. Same text -> same vector.

    Each word contributes a pseudo-random direction, so texts sharing words are similar.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    def _word_vector(self, word: str) -> list[float]:
        digest = hashlib.sha256(word.encode()).digest()
        values: list[float] = []
        counter = 0
        while len(values) < self.dim:
            block = hashlib.sha256(digest + struct.pack(">I", counter)).digest()
            values.extend((b - 127.5) / 127.5 for b in block)
            counter += 1
        return values[: self.dim]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            acc = [0.0] * self.dim
            for word in text.lower().split() or [""]:
                for i, v in enumerate(self._word_vector(word)):
                    acc[i] += v
            norm = math.sqrt(sum(x * x for x in acc)) or 1.0
            out.append([x / norm for x in acc])
        return out


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
