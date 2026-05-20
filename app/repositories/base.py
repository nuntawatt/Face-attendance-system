"""
Repository กลางแบบ async สำหรับใช้ CRUD ร่วมกัน

ทุก domain repository จะสืบทอดจาก class นี้
Generic[T] ช่วยให้ type-safe:
- IDE autocomplete ทำงานถูกต้อง
- static type checking แม่นยำขึ้น
- ลด bug จาก type mismatch
"""

from __future__ import annotations

from typing import Generic, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

# Generic type ของ ORM model
# bound=Base หมายถึง ModelT ต้องสืบทอดจาก Base เท่านั้น
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):

    """
    Generic repository ที่รองรับ async

    - repository ทำหน้าที่ access database เท่านั้น
    - transaction จะถูกควบคุมโดย service layer
    - รองรับ scalability และ multi-repository transaction
    """
    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    # CRUD operations
    async def get_by_id(self, entity_id: UUID) -> ModelT | None:
        result = await self._session.execute(
            select(self._model).where(self._model.id == entity_id)
        )
        return result.scalar_one_or_none()

    # get_all รองรับ pagination ด้วย limit และ offset
    async def get_all(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        result = await self._session.execute(
            select(self._model).limit(limit).offset(offset)
        )
        return result.scalars().all()

    # สร้าง instance ใหม่ใน database และ return instance ที่มี id และข้อมูลล่าสุดจาก database
    async def create(self, instance: ModelT) -> ModelT:
        self._session.add(instance)
        await self._session.flush()  # flush เพื่อให้ instance มี id ก่อน refresh
        await self._session.refresh(instance) # refresh เพื่อดึงข้อมูลล่าสุดจาก database (เช่น id ที่ถูก auto-generated)
        return instance

    # update จะรับ instance ที่มี id อยู่แล้ว และจะ update ข้อมูลใน database ตาม instance นั้น
    async def delete(self, instance: ModelT) -> None:
        await self._session.delete(instance)
        await self._session.flush()

    # ตรวจสอบว่ามี entity ที่มี id นี้อยู่ใน database หรือไม่
    async def exists(self, entity_id: UUID) -> bool:
        result = await self._session.execute(
            select(self._model.id).where(self._model.id == entity_id)
        )
        return result.scalar_one_or_none() is not None
