"""
Repository สำหรับจัดเก็บ face embedding

Embedding ถูกเก็บเป็น float array ดิบใน PostgreSQL โดยใช้ extension pgvector
(หรือ BYTEA ถ้าไม่มี pgvector) Repository นี้ซ่อน detail การเก็บข้อมูลนั้น
ไม่ให้ service layer เห็นโดยสิ้นเชิง

หมายเหตุ performance: เราไม่โหลด embedding ทั้งหมดใน hot loop
Recognition engine ดึง embedding แบบ bulk ตอน startup แล้ว cache ใน Redis/memory
Repository นี้ถูกเรียกแค่ตอน registration และ cache invalidation เท่านั้น
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face_embedding import FaceEmbedding
from app.repositories.base import BaseRepository


class FaceEmbeddingRepository(BaseRepository[FaceEmbedding]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FaceEmbedding, session)

    async def get_by_employee_id(self, employee_id: UUID) -> FaceEmbedding | None:
        """ดึง embedding ของพนักงานคนนั้น (1 คน = 1 embedding)"""
        result = await self._session.execute(
            select(FaceEmbedding).where(FaceEmbedding.employee_id == employee_id)
        )
        return result.scalar_one_or_none()

    async def get_all_active_embeddings(self) -> list[FaceEmbedding]:
        """
        โหลด embedding ทั้งหมดแบบ bulk สำหรับสร้าง in-memory recognition index
        เรียกแค่ตอน startup และหลังมีการลงทะเบียนใบหน้าใหม่เท่านั้น
        """
        result = await self._session.execute(
            select(FaceEmbedding)
            .join(FaceEmbedding.employee)
            .where(FaceEmbedding.employee.has(is_active=True))
        )
        return list(result.scalars().all())

    async def upsert(self, embedding: FaceEmbedding) -> FaceEmbedding:
        """แทนที่ embedding เดิมหรือสร้างใหม่ถ้ายังไม่มี"""
        existing = await self.get_by_employee_id(embedding.employee_id)
        if existing:
            existing.embedding_vector = embedding.embedding_vector
            existing.model_version = embedding.model_version
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        return await self.create(embedding)

    async def delete_by_employee_id(self, employee_id: UUID) -> None:
        """ลบ embedding เมื่อพนักงานออกจากระบบ"""
        await self._session.execute(
            delete(FaceEmbedding).where(FaceEmbedding.employee_id == employee_id)
        )
        await self._session.flush()