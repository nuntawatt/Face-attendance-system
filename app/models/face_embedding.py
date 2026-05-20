"""
FaceEmbedding model สำหรับเก็บข้อมูล embedding vector ของใบหน้าพนักงาน
- ใช้ SQLAlchemy ORM ในการกำหนดโมเดลและความสัมพันธ์กับตารางอื่นๆ
- มีฟิลด์ต่างๆ เช่น employee_id, embedding_vector, model_version
- มีความสัมพันธ์กับ Employee เพื่อเชื่อมโยงข้อมูลใบหน้ากับพนักงาน
- รองรับการอัพเดต embedding vector และ model version เมื่อมีการลงทะเบียนใบหน้าใหม่หรืออัพเดตข้อมูลใบหน้าเดิม
- รองรับการลบ embeddingเมื่อพนักงานถูกลบหรือไม่ active แล้ว เพื่อให้ข้อมูลในระบบสะอาดและเป็นปัจจุบัน
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin
from app.models.employee import Employee


class FaceEmbedding(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "face_embeddings"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    embedding_vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    image_quality_score: Mapped[float | None] = mapped_column(nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="face_embedding")  # noqa: F821