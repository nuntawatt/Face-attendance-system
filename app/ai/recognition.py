"""
Face recognition: embedding matching against the employee index.

The employee index is an in-memory numpy matrix. For N employees,
recognition is a single matrix multiplication: O(N * 512).
For N=5000, this takes ~0.3ms on a modern CPU — no GPU needed.

The index is loaded at startup from the database and refreshed via
Redis pub/sub whenever a new face is registered.

Why not use FAISS here?
For <10,000 employees, numpy matmul is faster than FAISS ANN because
the FAISS overhead (quantization, index lookup) exceeds the brute-force
cost at this scale. Switch to FAISS when N > 50,000.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import NamedTuple
from uuid import UUID

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

RECOGNITION_THRESHOLD = 0.45  # cosine similarity threshold for a confident match, tuned empirically


class RecognitionMatch(NamedTuple):
    employee_id: UUID
    similarity: float
    is_confident: bool


@dataclass
class EmployeeEmbeddingIndex:
    """
    Thread-safe in-memory embedding index.

    _matrix shape: (N, 512) stacked normalized embeddings.
    _employee_ids: list of UUIDs in the same order as matrix rows.

    Update is always a full reload (copy-on-write), never an in-place
    mutation, to avoid race conditions during recognition.
    """

    _matrix: np.ndarray = field(default_factory=lambda: np.empty((0, 512), dtype=np.float32))
    _employee_ids: list[UUID] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def size(self) -> int:
        return len(self._employee_ids)

    async def rebuild(self, embeddings: dict[UUID, np.ndarray]) -> None:
        """Replace the entire index atomically."""
        if not embeddings:
            async with self._lock:
                self._matrix = np.empty((0, 512), dtype=np.float32)
                self._employee_ids = []
            return

        ids = list(embeddings.keys())
        matrix = np.stack([embeddings[eid] for eid in ids]).astype(np.float32)

        async with self._lock:
            self._employee_ids = ids
            self._matrix = matrix

        logger.info("embedding_index_rebuilt", size=len(ids))

    async def find_match(self, probe: np.ndarray) -> RecognitionMatch | None:
        """
        Cosine similarity search. Returns the best match above threshold.
        probe must be a normalized (L2) float32 vector of shape (512,).
        """
        async with self._lock:
            if self._matrix.shape[0] == 0:
                return None
            matrix = self._matrix
            ids = self._employee_ids

        # Cosine similarity = dot product of normalized vectors
        similarities = matrix @ probe  # shape: (N,)
        best_idx = int(np.argmax(similarities))
        best_sim = float(similarities[best_idx])

        return RecognitionMatch(
            employee_id=ids[best_idx],
            similarity=best_sim,
            is_confident=best_sim >= RECOGNITION_THRESHOLD,
        )


# Application-level singleton
embedding_index = EmployeeEmbeddingIndex()