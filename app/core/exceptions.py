"""
Domain exception hierarchy.

Using typed exceptions instead of generic ValueError/RuntimeError lets
the global handler map exceptions to HTTP status codes declaratively.
Never raise HTTPException from service or repository layers — those layers
don't know they're being called from HTTP.
"""
from __future__ import annotations

from uuid import UUID


class AppError(Exception):
    """Root of all application exceptions."""
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


# --- 404 family ---

class NotFoundError(AppError):
    message = "Resource not found"


class EmployeeNotFoundError(NotFoundError):
    def __init__(self, employee_id: UUID | str) -> None:
        super().__init__(f"Employee '{employee_id}' not found")


# --- 409 family ---

class ConflictError(AppError):
    message = "Resource conflict"


class EmployeeCodeConflictError(ConflictError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Employee code '{code}' already exists")


# --- 422 family ---

class ValidationError(AppError):
    message = "Validation failed"


class FaceNotDetectedError(ValidationError):
    message = "No face detected in the provided image"


class MultipleFacesError(ValidationError):
    message = "Multiple faces detected — please provide a single-face image"


class ImageQualityError(ValidationError):
    def __init__(self, score: float, threshold: float) -> None:
        super().__init__(
            f"Image quality score {score:.2f} is below threshold {threshold:.2f}"
        )


# --- 503 family ---

class ServiceUnavailableError(AppError):
    message = "Service temporarily unavailable"


class AIEngineNotReadyError(ServiceUnavailableError):
    message = "Face recognition engine is not ready"


class CameraConnectionError(ServiceUnavailableError):
    def __init__(self, camera_id: str) -> None:
        super().__init__(f"Cannot connect to camera '{camera_id}'")