"""
FaceEmbeddingRepository: Repository สำหรับจัดการ FaceEmbedding model
- สืบทอดจาก BaseRepository เพื่อใช้ CRUD operations ทั่วไป
- เพิ่ม method เฉพาะสำหรับ FaceEmbedding เช่น get_by_employee_id, get_all_active
- ใช้ SQLAlchemy Core ในการ query database แบบ async
- รองรับการ upsert (update หรือ insert) ของ embedding เพื่อให้การลงทะเบียนใบหน้าใหม่หรือการอัพเดต embedding เดิมทำได้ง่ายขึ้น
- รองรับการลบ embedding เมื่อพนักงานถูกลบหรือไม่ active แล้ว
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face_embedding import FaceEmbedding
from app.repositories.base import BaseRepository


class FaceEmbeddingRepository(BaseRepository[FaceEmbedding]):

    # FaceEmbeddingRepository จะสืบทอดจาก BaseRepository โดยระบุ ModelT เป็น FaceEmbedding
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FaceEmbedding, session)

    # เพิ่ม method เฉพาะสำหรับ FaceEmbedding เช่น get_by_employee_id, get_all_active
    async def get_by_employee_id(self, employee_id: UUID) -> FaceEmbedding | None:
        result = await self._session.execute(
            select(FaceEmbedding).where(FaceEmbedding.employee_id == employee_id)
        )
        return result.scalar_one_or_none()

    # get_all_active_embeddings จะ return list ของ FaceEmbedding ที่เชื่อมโยงกับ Employee ที่มี is_active = True
    async def get_all_active_embeddings(self) -> list[FaceEmbedding]:
        """
        Bulk load for in-memory recognition index.
        Called only at startup and after new registrations.
        """
        result = await self._session.execute(
            select(FaceEmbedding)
            .join(FaceEmbedding.employee)
            .where(FaceEmbedding.employee.has(is_active=True))
        )
        return list(result.scalars().all())

    # upsert จะรับ FaceEmbedding instance และจะ update ถ้ามีอยู่แล้ว หรือสร้างใหม่ถ้าไม่มี
    async def upsert(self, embedding: FaceEmbedding) -> FaceEmbedding:
        """Replace existing embedding or create new one."""
        existing = await self.get_by_employee_id(embedding.employee_id)
        if existing:
            existing.embedding_vector = embedding.embedding_vector
            existing.model_version = embedding.model_version
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        return await self.create(embedding)

    # delete_by_employee_id จะลบ FaceEmbedding ที่เชื่อมโยงกับ employee_id นี้
    async def delete_by_employee_id(self, employee_id: UUID) -> None:
        await self._session.execute(
            delete(FaceEmbedding).where(FaceEmbedding.employee_id == employee_id)
        )
        await self._session.flush()