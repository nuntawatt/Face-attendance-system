"""
Application lifespan manager

ลำดับ startup สำคัญมาก:
1. โหลด AI model (blocking — ต้องเสร็จก่อน serve request)
2. สร้าง embedding index จาก DB ใหม่
3. เริ่ม camera worker เป็น background task
4. เปิด connection (Redis, DB pool) — async session factory จัดการแล้ว

ลำดับ shutdown (ย้อนกลับ):
1. ส่งสัญญาณให้ camera worker หยุด
2. รอ task drain
3. คืน resource

ถ้ากล้องตัวหนึ่ง fail กล้องอื่นๆ ต้องทำงานต่อ
asyncio.gather(*tasks, return_exceptions=True) ทำให้แน่ใจเรื่องนี้
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI

from app.ai.engine import face_engine
from app.ai.recognition import embedding_index
from app.attendance.engine import AttendanceEngine
from app.camera.stream_reader import CameraConfig
from app.core.config import settings
from app.database.session import async_session_factory
from app.services.embedding_cache_service import EmbeddingCacheService

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("กำลังเริ่มต้น application")

    # 1. โหลด AI engine (blocking จงใจ)
    face_engine.load()

    # 2. สร้าง embedding index ใหม่
    async with async_session_factory() as session:
        cache_service = EmbeddingCacheService(session)
        await cache_service.rebuild_index()

    # 3. เริ่ม camera worker
    stop_event = asyncio.Event()
    camera_tasks: list[asyncio.Task] = []

    for cam_config in settings.camera_configs:
        engine = AttendanceEngine(
            config=cam_config,
            session_factory=async_session_factory,
            redis_client=app.state.redis,
            stop_event=stop_event,
        )
        task = asyncio.create_task(
            engine.run(),
            name=f"camera-{cam_config.camera_id}",
        )
        camera_tasks.append(task)

    logger.info("application พร้อมใช้งาน", จำนวนกล้อง=len(camera_tasks))
    yield  # app ทำงานอยู่ที่นี่

    # Shutdown
    logger.info("กำลังปิด application")
    stop_event.set()  # ส่งสัญญาณให้ทุก camera worker หยุด

    if camera_tasks:
        await asyncio.gather(*camera_tasks, return_exceptions=True)

    logger.info("application ปิดแล้ว")
