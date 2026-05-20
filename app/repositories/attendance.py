"""
AttendanceRepository: Repository สำหรับจัดการ AttendanceRecord model
- สืบทอดจาก BaseRepository เพื่อใช้ CRUD operations ทั่วไป
- เพิ่ม method เฉพาะสำหรับ AttendanceRecord เช่น get_today_record, get_by_date_range
- ใช้ SQLAlchemy Core ในการ query database แบบ async
- รองรับการ mark checkout โดยการอัพเดต check_out_time ใน record ที่มีอยู่แล้ว
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceRecord
from app.repositories.base import BaseRepository


class AttendanceRepository(BaseRepository[AttendanceRecord]):

    # AttendanceRepository จะสืบทอดจาก BaseRepository โดยระบุ ModelT เป็น AttendanceRecord
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AttendanceRecord, session)

    # เพิ่ม method เฉพาะสำหรับ AttendanceRecord เช่น get_today_record, get_by_date_range
    async def get_today_record(self, employee_id: UUID) -> AttendanceRecord | None:
        today = date.today()
        result = await self._session.execute(
            select(AttendanceRecord).where(
                and_(
                    AttendanceRecord.employee_id == employee_id,
                    func.date(AttendanceRecord.check_in_time) == today,
                )
            )
        )
        return result.scalar_one_or_none()

    # get_by_date_range จะ return list ของ AttendanceRecord ที่อยู่ในช่วงวันที่นี้ โดยรองรับ pagination ด้วย limit และ offset
    async def get_by_date_range(
        self,
        employee_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[AttendanceRecord]:
        result = await self._session.execute(
            select(AttendanceRecord).where(
                and_(
                    AttendanceRecord.employee_id == employee_id,
                    func.date(AttendanceRecord.check_in_time) >= start_date,
                    func.date(AttendanceRecord.check_in_time) <= end_date,
                )
            ).order_by(AttendanceRecord.check_in_time.desc())
        )
        return list(result.scalars().all())

    # mark_checkout จะอัพเดต check_out_time ใน record ที่มีอยู่แล้ว โดยรับ record_id และ checkout_time มาเป็น parameter
    async def mark_checkout(
        self, record_id: UUID, checkout_time: datetime
    ) -> AttendanceRecord | None:
        record = await self.get_by_id(record_id)
        if record:
            record.check_out_time = checkout_time
            await self._session.flush() # flush เพื่อบันทึกการเปลี่ยนแปลงใน session ก่อน refresh
            await self._session.refresh(record) # refresh เพื่อดึงข้อมูลล่าสุดจาก database หลังจาก update
        return record