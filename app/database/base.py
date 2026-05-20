"""
สร้างฐานข้อมูลและ mixin สำหรับโมเดลต่างๆ ในระบบ
- Base: คลาสฐานสำหรับโมเดลทั้งหมดที่ใช้ SQLAlchemy ORM
- TimestampMixin: ให้โมเดลมี created_at และ updated_at โดยใช้ server-side defaults
- UUIDMixin: ให้โมเดลมี id เป็น UUID ที่ถูกสร้างโดยแอปพลิเคชัน
- โมเดลต่างๆ เช่น Employee, FaceEmbedding, AttendanceRecord ที่จะสืบทอด
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Provides created_at and updated_at with server-side defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDMixin:
    """UUID primary key generated application-side."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )