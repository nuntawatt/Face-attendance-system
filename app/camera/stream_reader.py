"""
RTSP stream reader with adaptive frame skipping.

Key design decisions:
  1. Frame skipping: We do NOT process every frame. At 25fps, processing
     every frame = 25 inference calls/sec/camera. With 10 cameras, that's
     250 inferences/sec — a CPU killer. Instead, we process 1 frame per
     PROCESS_INTERVAL seconds.

  2. Reconnection: RTSP streams drop. The reader auto-reconnects with
     exponential backoff. The camera process NEVER exits on disconnect.

  3. cv2.CAP_PROP_BUFFERSIZE=1: We want the LATEST frame, not a stale
     one buffered by OpenCV's internal queue. This is critical for
     real-time attendance detection.

  4. asyncio.to_thread for cap.read(): cap.read() blocks. We offload
     it to a thread pool to keep the event loop non-blocking.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import AsyncGenerator

import cv2
import numpy as np
import structlog

logger = structlog.get_logger(__name__)

PROCESS_INTERVAL_SEC = 1.0   # Process one frame per second per camera
RECONNECT_DELAY_BASE = 2.0   # Seconds before first reconnect
RECONNECT_DELAY_MAX = 30.0   # Cap reconnect backoff
FRAME_READ_TIMEOUT = 5.0     # Seconds before declaring stream dead


@dataclass
class CameraConfig:
    camera_id: str
    rtsp_url: str
    fps_target: int = 25
    resolution: tuple[int, int] = (640, 480)


async def stream_frames(
    config: CameraConfig,
    stop_event: asyncio.Event,
) -> AsyncGenerator[tuple[str, np.ndarray], None]:
    """
    Async generator that yields (camera_id, frame) tuples.
    Handles reconnection internally. Caller never sees disconnects.
    """
    reconnect_delay = RECONNECT_DELAY_BASE

    while not stop_event.is_set():
        cap = await asyncio.to_thread(_open_capture, config.rtsp_url, config.resolution)

        if cap is None or not cap.isOpened():
            logger.warning(
                "camera_connect_failed",
                camera_id=config.camera_id,
                retry_in=reconnect_delay,
            )
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, RECONNECT_DELAY_MAX)
            continue

        reconnect_delay = RECONNECT_DELAY_BASE
        logger.info("camera_connected", camera_id=config.camera_id)

        last_process_time = 0.0

        try:
            while not stop_event.is_set():
                ret, frame = await asyncio.wait_for(
                    asyncio.to_thread(cap.read),
                    timeout=FRAME_READ_TIMEOUT,
                )

                if not ret:
                    logger.warning("camera_frame_read_failed", camera_id=config.camera_id)
                    break

                now = time.monotonic()
                if now - last_process_time >= PROCESS_INTERVAL_SEC:
                    last_process_time = now
                    yield config.camera_id, frame

        except asyncio.TimeoutError:
            logger.warning("camera_read_timeout", camera_id=config.camera_id)
        except Exception as exc:
            logger.exception("camera_stream_error", camera_id=config.camera_id, error=str(exc))
        finally:
            await asyncio.to_thread(cap.release)
            logger.info("camera_disconnected", camera_id=config.camera_id)


def _open_capture(rtsp_url: str, resolution: tuple[int, int]) -> cv2.VideoCapture | None:
    """Called in thread pool — blocking OpenCV operations are safe here."""
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # always get latest frame
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    return cap