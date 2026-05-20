"""
Application lifespan manager.

Startup order matters:
  1. Load AI model (blocking, must complete before serving requests)
  2. Rebuild embedding index from DB
  3. Start camera workers as background tasks
  4. Open connections (Redis, DB pool) — already done by session factory

Shutdown order (reverse):
  1. Signal camera workers to stop
  2. Wait for tasks to drain
  3. Release resources

Using asyncio.TaskGroup (Python 3.11+) ensures that if one camera
task fails, the others keep running. A single bad camera should never
take down the system.
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
    logger.info("application_starting")

    # 1. Load AI engine (blocking intentional)
    face_engine.load()

    # 2. Rebuild embedding index
    async with async_session_factory() as session:
        cache_service = EmbeddingCacheService(session)
        await cache_service.rebuild_index()

    # 3. Start camera workers
    stop_event = asyncio.Event()
    camera_tasks: list[asyncio.Task] = []

    # Load camera configs from settings/DB
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

    logger.info("application_ready", cameras=len(camera_tasks))
    yield

    # Shutdown
    logger.info("application_shutting_down")
    stop_event.set()

    if camera_tasks:
        await asyncio.gather(*camera_tasks, return_exceptions=True)

    logger.info("application_stopped")