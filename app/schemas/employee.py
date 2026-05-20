"""
Employee schemas สำหรับการรับส่งข้อมูลเกี่ยวกับพนักงานใน API
- EmployeeBase: schema พื้นฐานสำหรับข้อมูลพนักงานที่ใช้ในการสร้างและอัพเดต
- EmployeeCreate: schema สำหรับการสร้างพนักงานใหม่ โดยสืบทอดจาก EmployeeBase และเพิ่ม field is_active
- EmployeeUpdate: schema สำหรับการอัพเดตพนักงาน โดยมี field ทั้งหมดเป็น optional เพื่อรองรับการอัพเดตแบบ partial (PATCH semantics)
- EmployeeResponse: schema สำหรับการตอบกลับข้อมูลพนักงานใน API
- EmployeeListResponse: schema สำหรับการตอบกลับรายการพนักงานพร้อม pagination metadata
- มีการใช้ Pydantic validators เพื่อทำความสะอาดและตรวจสอบข้อมูล
"""
from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class EmployeeBase(BaseModel):
    employee_code: str = Field(..., min_length=2, max_length=50, examples=["EMP-001"])
    full_name: str = Field(..., min_length=2, max_length=200)
    department: str = Field(..., min_length=2, max_length=100)
    position: str = Field(..., min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    notes: str | None = None

    @field_validator("employee_code")
    @classmethod
    def validate_employee_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9\-]+$", v):
            raise ValueError("Employee code must contain only alphanumeric characters and hyphens")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        return " ".join(v.split())  # normalize whitespace


class EmployeeCreate(EmployeeBase):
    is_active: bool = True


class EmployeeUpdate(BaseModel):
    """All fields optional for PATCH semantics."""
    full_name: str | None = Field(None, min_length=2, max_length=200)
    department: str | None = Field(None, min_length=2, max_length=100)
    position: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    notes: str | None = None
    is_active: bool | None = None


class EmployeeResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    face_registered: bool
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int
    limit: int
    offset: int