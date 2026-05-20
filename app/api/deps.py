"""
FastAPI dependency providers.

All database sessions, service instances, and auth checks are provided
as dependencies. This means every router stays thin — no setup code,
no teardown code. The session lifecycle is managed here via async generators.

Session-per-request: each HTTP request gets its own AsyncSession.
This is the standard pattern. Do NOT share sessions across requests.
"""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import async_session_factory
from app.services.employee_service import EmployeeService
from app.services.face_service import FaceRegistrationService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_employee_service(
    session: AsyncSession = Depends(get_db_session),
) -> EmployeeService:
    return EmployeeService(session)


async def get_face_service(
    session: AsyncSession = Depends(get_db_session),
) -> FaceRegistrationService:
    return FaceRegistrationService(session)