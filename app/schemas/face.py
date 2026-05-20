from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class FaceRegistrationResponse(BaseModel):
    employee_id: UUID
    success: bool
    message: str
    quality_score: float | None = None # คะแนนคุณภาพภาพ (0.0 - 1.0)
    model_version: str # เวอร์ชันโมเดล AI ที่ใช้สร้าง embedding นี้


class FaceVerificationResult(BaseModel):
    employee_id: UUID
    employee_code: str
    full_name: str
    confidence: float # ความมั่นใจ (0.0 = ไม่แน่ใจ, 1.0 = แน่ใจมาก)
    camera_id: str
    timestamp: str


class EmbeddingCacheStatus(BaseModel):
    """สถานะ cache ของ embedding index ใน memory"""
    total_embeddings: int
    cache_hit: bool
    last_updated: str | None