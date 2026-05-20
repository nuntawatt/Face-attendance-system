"""
Realtime attendance engine — worker หลักของ production

นี่ไม่ใช่ FastAPI route แต่เป็น long-running asyncio coroutine
ที่เริ่มใน application lifespan และรันตลอดอายุของ app

สถาปัตยกรรม:
CameraStreamReader -> frame_queue -> AttendanceEngine
    (producer)                      (consumer)

Queue แยก producer ออกจาก consumer ถ้า recognition ช้า
frame จะ back-pressure และ drop (LIFO maxsize=1 ต่อกล้อง)
การ drop frame เป็นเจตนา — สำหรับ attendance เราต้องการ frame ล่าสุด
ไม่ใช่คิว backlog ของ frame เก่า

การกำจัดซ้ำ (Deduplication):
Redis เก็บ key "recognized::{employee_id}::{date}" พร้อม TTL 4 ชั่วโมง
ถ้า key มีอยู่แล้ว ข้าม DB write พนักงาน check-in แล้ว
ป้องกัน duplicate attendance record เมื่อคนยืนอยู่หน้ากล้องหลายวินาที
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

import structlog

from app.ai.engine import face_engine
from app.ai.recognition import embedding_index
from app.camera.face_tracker import FaceTracker
from app.camera.stream_reader import CameraConfig, stream_frames
from app.core.config import settings

logger = structlog.get_logger(__name__)

ATTENDANCE_DEDUP_TTL = 4 * 3600  # 4 ชั่วโมง (วินาที)


class AttendanceEngine:
    """
    ประสาน: อ่าน stream -> ตรวจจับใบหน้า -> จำแนก -> เขียน DB
    1 instance ต่อ 1 กล้อง รัน concurrent ทุกกล้องด้วย asyncio.gather
    """

    def __init__(
        self,
        config: CameraConfig,
        session_factory,
        redis_client,
        stop_event: asyncio.Event,
    ) -> None:
        self._config = config
        self._session_factory = session_factory
        self._redis = redis_client
        self._stop = stop_event
        self._tracker = FaceTracker()  # แต่ละกล้องมี tracker ของตัวเอง

    async def run(self) -> None:
        logger.info("attendance_engine_start", camera_id=self._config.camera_id)
        async for camera_id, frame in stream_frames(self._config, self._stop):
            try:
                await self._process_frame(frame)
            except Exception:
                # log แต่ไม่ crash กล้องต้องทำงานต่อเสมอ
                logger.exception("frame_processing_error", camera_id=camera_id)
        logger.info("attendance_engine_stop", camera_id=self._config.camera_id)

    async def _process_frame(self, frame) -> None:
        """ประมวลผล 1 frame: ตรวจจับ -> track -> จำแนกเฉพาะใบหน้าใหม่"""
        faces = await face_engine.analyze_frame(frame)
        if not faces:
            return

        bboxes = [f.bbox for f in faces]
        track_indices = self._tracker.update(bboxes)

        recognition_tasks = []
        for i, (face, track_idx) in enumerate(zip(faces, track_indices)):
            if self._tracker.is_recognized(track_idx):
                continue  # จำแนกแล้วในการเข้างานนี้ - ข้าม
            recognition_tasks.append(
                self._recognize_and_record(face.embedding, track_idx)
            )

        # รันทุก recognition พร้อมกันไม่รอทีละคน
        if recognition_tasks:
            await asyncio.gather(*recognition_tasks, return_exceptions=True)

    async def _recognize_and_record(self, embedding, track_idx: int) -> None:
        """จำแนกใบหน้า 1 ใบ และบันทึกการเข้างานถ้าจำแนกได้"""
        match = await embedding_index.find_match(embedding)
        if match is None or not match.is_confident:
            return  # ไม่แน่ใจพอ ไม่บันทึก

        employee_id = match.employee_id
        self._tracker.mark_recognized(track_idx, employee_id)

        # ตรวจสอบ deduplication ใน Redis ก่อน เร็วมาก
        dedup_key = self._dedup_key(employee_id)
        if await self._redis.exists(dedup_key):
            logger.debug("attendance_dedup_hit", employee_id=str(employee_id))
            return

        # บันทึกการเข้างาน
        async with self._session_factory() as session:
            from app.repositories.attendance import AttendanceRepository
            repo = AttendanceRepository(session)
            from app.models.attendance import AttendanceRecord
            
            now_time = datetime.now(timezone.utc)
            work_date = now_time.date()
            
            # ถ้ามี record ของวันนี้อยู่แล้ว ให้ update เป็น check_out_time ใหม่
            record = await repo.get_today_record(employee_id)
            if record:
                # Check-out logic: Update check_out_time ถ้าพนักงานยืนอยู่หน้ากล้องนานๆ
                record.check_out_time = now_time
                record.camera_id = self._config.camera_id
                record.confidence_score = (record.confidence_score + match.similarity) / 2.0
            else:
                # Check-in logic: สร้าง record ใหม่
                record = AttendanceRecord(
                    employee_id=employee_id,
                    work_date=work_date,
                    check_in_time=now_time,
                    camera_id=self._config.camera_id,
                    confidence_score=match.similarity,
                )
                await repo.create(record)
                
            await session.commit()

        # ตั้ง dedup key ใน Redis เพื่อป้องกันการบันทึกซ้ำในวันนี้
        await self._redis.setex(dedup_key, ATTENDANCE_DEDUP_TTL, "1")
        logger.info(
            "attendance_recorded",
            employee_id=str(employee_id),
            camera_id=self._config.camera_id,
            confidence=round(match.similarity, 3),
        )

    def _dedup_key(self, employee_id: UUID) -> str:
        """สร้าง Redis key ที่ unique ต่อพนักงาน ต่อวัน"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"attendance:dedup:{employee_id}:{today}"