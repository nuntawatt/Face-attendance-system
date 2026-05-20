"""
InsightFace ONNX engine wrapper.

Singleton pattern: the model is loaded ONCE at startup and reused.
Loading a 300MB ONNX model per-request would be catastrophic.

Thread-safety: ONNX Runtime sessions are thread-safe for inference.
We use asyncio.to_thread() to run CPU-bound inference without blocking
the event loop.

Performance levers:
  - inter_op_num_threads / intra_op_num_threads: tune per deployment
  - Use CUDAExecutionProvider if GPU available, fall back to CPU
  - face_det_size: lower = faster detection, less accurate on small faces
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
import structlog
from insightface.app import FaceAnalysis

logger = structlog.get_logger(__name__)


class DetectedFace(NamedTuple):
    embedding: np.ndarray  # shape: (512,) normalized float32
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    det_score: float
    quality_score: float


class FaceEngine:
    """
    Wraps InsightFace for detection + embedding extraction.

    model_pack: 'buffalo_l' (accuracy) or 'buffalo_s' (speed).
    For factory deployment, buffalo_s is usually sufficient and
    saves ~40% CPU vs buffalo_l.
    """

    def __init__(
        self,
        model_pack: str = "buffalo_s",
        det_size: tuple[int, int] = (320, 320),
        det_thresh: float = 0.5,
        providers: list[str] | None = None,
    ) -> None:
        self._model_pack = model_pack
        self._det_size = det_size
        self._det_thresh = det_thresh
        self._providers = providers or ["CPUExecutionProvider"]
        self._app: FaceAnalysis | None = None

    def load(self) -> None:
        """Blocking load call from startup event, not from a coroutine."""
        logger.info("loading_face_engine", model=self._model_pack)
        self._app = FaceAnalysis(
            name=self._model_pack,
            providers=self._providers,
        )
        self._app.prepare(ctx_id=0, det_size=self._det_size, det_thresh=self._det_thresh)
        logger.info("face_engine_ready", model=self._model_pack)

    @property
    def is_ready(self) -> bool:
        return self._app is not None

    async def analyze_frame(self, frame: np.ndarray) -> list[DetectedFace]:
        """
        Run detection + embedding on a frame asynchronously.
        asyncio.to_thread ensures the CPU-bound ONNX inference does not
        block the event loop, preserving API responsiveness.
        """
        if not self.is_ready:
            raise RuntimeError("FaceEngine not loaded")
        return await asyncio.to_thread(self._analyze_sync, frame)

    def _analyze_sync(self, frame: np.ndarray) -> list[DetectedFace]:
        faces = self._app.get(frame)
        results: list[DetectedFace] = []
        for face in faces:
            embedding = face.normed_embedding.astype(np.float32)
            bbox = tuple(face.bbox.astype(int).tolist())
            quality = self._estimate_quality(frame, bbox)
            results.append(DetectedFace(
                embedding=embedding,
                bbox=bbox,
                det_score=float(face.det_score),
                quality_score=quality,
            ))
        return results

    @staticmethod
    def _estimate_quality(frame: np.ndarray, bbox: tuple) -> float:
        """
        Lightweight quality heuristic: Laplacian variance (sharpness).
        Score > 100 = usable, > 200 = good quality for registration.
        This is intentionally cheap no ML model, pure CV math.
        """
        x1, y1, x2, y2 = bbox
        face_crop = frame[y1:y2, x1:x2]
        if face_crop.size == 0:
            return 0.0
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        return min(float(variance) / 200.0, 1.0)  # normalize to [0, 1]


# Application-level singleton initialized in lifespan
face_engine = FaceEngine()