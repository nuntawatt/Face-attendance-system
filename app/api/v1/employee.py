"""
Employee API router

Router เป็นแค่ dispatcher ที่บาง ไม่มี business logic, ไม่มี SQL, ไม่มี AI call
รับ input (ผ่าน Pydantic validate แล้ว), เรียก service, return ผลลัพธ์

Pattern: ทุก endpoint ใช้ response_model ชัดเจน
เพื่อ documentation และ filter response อัตโนมัติ (ไม่เคย leak field โดยบังเอิญ)
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_employee_service
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["พนักงาน"])


@router.post(
    "/",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="ลงทะเบียนพนักงานใหม่",
)
async def create_employee(
    payload: EmployeeCreate,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    return await service.create_employee(payload)


@router.get(
    "/",
    response_model=EmployeeListResponse,
    summary="ดูรายชื่อพนักงานทั้งหมด",
)
async def list_employees(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeListResponse:
    return await service.list_employees(limit=limit, offset=offset)


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="ดูข้อมูลพนักงานตาม ID",
)
async def get_employee(
    employee_id: UUID,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    return await service.get_employee(employee_id)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="แก้ไขข้อมูลพนักงานบางส่วน",
)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    return await service.update_employee(employee_id, payload)


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="ปิดการใช้งานพนักงาน (soft delete)",
)
async def deactivate_employee(
    employee_id: UUID,
    service: EmployeeService = Depends(get_employee_service),
) -> None:
    await service.deactivate_employee(employee_id)