from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class FaceRegistrationResponse(BaseModel):
    employee_id: UUID
    success: bool
    message: str
    quality_score: float | None = None
    model_version: str


class FaceVerificationResult(BaseModel):
    employee_id: UUID
    employee_code: str
    full_name: str
    confidence: float
    camera_id: str
    timestamp: str


class EmbeddingCacheStatus(BaseModel):
    total_embeddings: int
    cache_hit: bool
    last_updated: str | None