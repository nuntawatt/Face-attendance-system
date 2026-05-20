"""
Employee model สำหรับเก็บข้อมูลพนักงานในระบบ
- ใช้ SQLAlchemy ORM ในการกำหนดโมเดลและความสัมพันธ์กับตารางอื่นๆ
- มีฟิลด์ต่างๆ เช่น employee_code, full_name, department
- มีความสัมพันธ์กับ FaceEmbedding และ AttendanceRecord เพื่อเชื่อมโยงข้อมูลใบหน้าและการลงเวลาของพนักงาน
- มี field face_registered เพื่อบ่งบอกว่าพนักงานนี้ได้ลงทะเบียนใบหน้าแล้วหรือยัง ซึ่งจะช่วยในการจัดการ flow การลงทะเบียนใบหน้าและการตรวจสอบ
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin


# Employee model จะสืบทอดจาก UUIDMixin, TimestampMixin และ Base เพื่อให้มี id เป็น UUID และมี created_at, updated_at โดยอัตโนมัติ
class Employee(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employees"

    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    face_registered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    face_embedding: Mapped["FaceEmbedding"] = relationship(  # noqa: F821
        "FaceEmbedding", back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(  # noqa: F821
        "AttendanceRecord", back_populates="employee", cascade="all, delete-orphan"
    )