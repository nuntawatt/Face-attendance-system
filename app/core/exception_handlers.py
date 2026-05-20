"""
Global FastAPI exception handlers.

This is the ONLY place that translates domain exceptions to HTTP responses.
Routers never catch exceptions — they bubble up to here.
"""
from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

logger = structlog.get_logger(__name__)


def _error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    error_class = type(exc).__name__

    if isinstance(exc, NotFoundError):
        logger.warning("not_found", error=error_class, message=exc.message)
        return _error_response(404, error_class, exc.message)

    if isinstance(exc, ConflictError):
        logger.warning("conflict", error=error_class, message=exc.message)
        return _error_response(409, error_class, exc.message)

    if isinstance(exc, ValidationError):
        logger.warning("validation_error", error=error_class, message=exc.message)
        return _error_response(422, error_class, exc.message)

    if isinstance(exc, ServiceUnavailableError):
        logger.error("service_unavailable", error=error_class, message=exc.message)
        return _error_response(503, error_class, exc.message)

    logger.exception("unhandled_app_error", error=error_class)
    return _error_response(500, "InternalError", "An unexpected error occurred")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", exc_type=type(exc).__name__)
    return _error_response(500, "InternalError", "An unexpected error occurred")