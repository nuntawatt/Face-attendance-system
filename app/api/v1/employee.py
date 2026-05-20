"""
Employee API router.

Routers are dumb dispatchers. No business logic, no SQL, no AI calls.
They validate input (via Pydantic), call the service, return the result.

Pattern: all endpoints use explicit response_model for documentation
and automatic response filtering (never accidentally leak fields).
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

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post(
    "/",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new employee",
)
async def create_employee(
    payload: EmployeeCreate,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    return await service.create_employee(payload)


@router.get(
    "/",
    response_model=EmployeeListResponse,
    summary="List all employees",
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
    summary="Get employee by ID",
)
async def get_employee(
    employee_id: UUID,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    return await service.get_employee(employee_id)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Partially update an employee",
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
    summary="Deactivate an employee (soft delete)",
)
async def deactivate_employee(
    employee_id: UUID,
    service: EmployeeService = Depends(get_employee_service),
) -> None:
    await service.deactivate_employee(employee_id)