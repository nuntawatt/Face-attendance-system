"""
AttendanceRecord model สำหรับเก็บข้อมูลการลงเวลาของพนักงานในระบบ
- ใช้ SQLAlchemy ORM ในการกำหนดโมเดลและความสัมพันธ์กับตารางอื่นๆ
- มีฟิลด์ต่างๆ เช่น employee_id, check_in_time
- มีความสัมพันธ์กับ Employee เพื่อเชื่อมโยงข้อมูลการลงเวลากับพนักงาน
- รองรับการ mark checkout โดยการอัพเดต check_out_time ใน record ที่มีอยู่แล้ว
- รองรับการคำนวณสถานะการลงเวลา เช่น late หรือ early leave โดยอิงจากกฎการลงเวลาที่กำหนดไว้ในระบบ
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin
from app.models.employee import Employee


class AttendanceRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "attendance_records"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    check_in_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    camera_id: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="present", nullable=False
    )  # present | late | early_leave

    employee: Mapped["Employee"] = relationship("Employee", back_populates="attendance_records")  # noqa: F821