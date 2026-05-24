"""
Pydantic v2 schemas สำหรับ Employee domain

รูปแบบการแบ่งชั้น schema:
    EmployeeBase -> field ร่วม (ไม่มี ID, ไม่มี timestamp)
    EmployeeCreate -> สิ่งที่ API รับตอน POST
    EmployeeUpdate -> body ของ PATCH (ทุก field เป็น optional)
    EmployeeResponse -> สิ่งที่ API ส่งกลับ (รวม computed fields)
    EmployeeListResponse -> wrapper สำหรับรายการแบบ paginated

ป้องกัน over-posting (client ไม่สามารถตั้ง face_registered โดยตรงได้)
และ under-exposure (ไม่เคย leak internal DB fields)
"""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
        """รหัสพนักงานต้องเป็นตัวอักษร ตัวเลข หรือขีดกลางเท่านั้น"""
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9\-]+$", v):
            raise ValueError(
                "Employee code must contain only alphanumeric characters and hyphens"
            )
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """ทำความสะอาด whitespace ใน full name"""
        return " ".join(v.split())


class EmployeeCreate(EmployeeBase):
    is_active: bool = True


class EmployeeUpdate(BaseModel):
    """ทุก field เป็น optional สำหรับ PATCH semantics แก้ได้แค่ field ที่ส่งมา"""

    full_name: str | None = Field(None, min_length=2, max_length=200)
    department: str | None = Field(None, min_length=2, max_length=100)
    position: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    notes: str | None = None
    is_active: bool | None = None


class EmployeeResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)  # อ่านค่าจาก ORM object ได้โดยตรง

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
