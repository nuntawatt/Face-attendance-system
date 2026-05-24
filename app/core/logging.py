"""
Structured JSON logging สำหรับ production

ทำไมต้องใช้ structlog? stdlib logging ของ Python ส่งออก unstructured text
ใน production, log ไปที่ aggregator (Datadog, Loki, ELK) Log แบบ JSON
หมายความว่า parser overhead เป็นศูนย์ และค้นหาตาม field ได้ทันที

หมายเหตุ performance: Processor ถูก chain กัน ทำให้ chain เบาที่สุด
ห้ามเพิ่ม processor ที่ทำ I/O เด็ดขาด (เช่น DB call ใน log processor)
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """
    เรียกครั้งเดียวตอน application startup
    json_logs=False ให้ output ที่อ่านง่ายสำหรับ local development
    json_logs=True สำหรับ production (ส่งไป log aggregator)
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,  # รวม context vars เข้า log
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,  # cache เพื่อ performance
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())

    # ปิดเสียง logger ของ third-party ที่ verbose เกินไป
    for name in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
