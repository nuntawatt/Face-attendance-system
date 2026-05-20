"""
Environment-based configuration using Pydantic Settings.

All values come from environment variables (or .env file via python-dotenv).
Never hardcode URLs, credentials, or thresholds in application code.

The @cached_property on camera_configs means the parsing happens
once, not on every access.
"""
from __future__ import annotations

import json
from functools import cached_property
from typing import Literal

from pydantic import Field, RedisDsn, PostgresDsn
from pydantic_settings import BaseSettings

from app.camera.stream_reader import CameraConfig


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # App
    app_name: str = "Face Attendance System"
    environment: Literal["development", "staging", "production"] = "production"
    log_level: str = "INFO"

    # Database
    database_url: PostgresDsn = Field(..., alias="DATABASE_URL")
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: RedisDsn = Field(..., alias="REDIS_URL")

    # AI
    face_model_pack: str = "buffalo_s"
    face_det_size: int = 320
    face_det_threshold: float = 0.5
    face_recognition_threshold: float = 0.45
    min_image_quality: float = 0.4

    # Camera — JSON array of camera config dicts
    cameras_json: str = Field("[]", alias="CAMERAS_JSON")

    @cached_property
    def camera_configs(self) -> list[CameraConfig]:
        raw = json.loads(self.cameras_json)
        return [CameraConfig(**c) for c in raw]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()