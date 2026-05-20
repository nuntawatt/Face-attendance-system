"""
Simple IoU-based face tracker.

Purpose: Avoid running recognition on every detected face every second.
If a face bbox overlaps significantly with one seen in the last N seconds,
we assume it's the same person — no recognition needed.

This reduces recognition calls by ~70-80% in a typical factory gate
scenario where people walk through the camera FOV over several seconds.

The tracker is per-camera, per-worker. It is NOT shared across cameras.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from uuid import UUID

import numpy as np


@dataclass
class TrackedFace:
    bbox: tuple[int, int, int, int]
    employee_id: UUID | None  # None = detected but not yet recognized
    last_seen: float = field(default_factory=time.monotonic)
    recognized: bool = False


class FaceTracker:
    """
    Tracks faces across frames using IoU bounding box overlap.
    Evicts tracks not seen in TTL seconds.
    """

    def __init__(self, iou_threshold: float = 0.4, ttl_seconds: float = 5.0) -> None:
        self._iou_threshold = iou_threshold
        self._ttl = ttl_seconds
        self._tracks: list[TrackedFace] = []

    def update(self, bboxes: list[tuple[int, int, int, int]]) -> list[int | None]:
        """
        Match incoming bboxes to existing tracks.
        Returns list of track indices (None = new face, needs recognition).
        """
        self._evict_stale()
        result: list[int | None] = []

        for bbox in bboxes:
            match_idx = self._find_match(bbox)
            if match_idx is not None:
                self._tracks[match_idx].last_seen = time.monotonic()
                self._tracks[match_idx].bbox = bbox
            else:
                self._tracks.append(TrackedFace(bbox=bbox))
                match_idx = len(self._tracks) - 1
            result.append(match_idx)

        return result

    def mark_recognized(self, track_idx: int, employee_id: UUID) -> None:
        if 0 <= track_idx < len(self._tracks):
            self._tracks[track_idx].employee_id = employee_id
            self._tracks[track_idx].recognized = True

    def is_recognized(self, track_idx: int) -> bool:
        if 0 <= track_idx < len(self._tracks):
            return self._tracks[track_idx].recognized
        return False

    def get_employee_id(self, track_idx: int) -> UUID | None:
        if 0 <= track_idx < len(self._tracks):
            return self._tracks[track_idx].employee_id
        return None

    def _evict_stale(self) -> None:
        now = time.monotonic()
        self._tracks = [t for t in self._tracks if now - t.last_seen < self._ttl]

    def _find_match(self, bbox: tuple) -> int | None:
        best_iou = self._iou_threshold
        best_idx: int | None = None

        for i, track in enumerate(self._tracks):
            iou = _compute_iou(bbox, track.bbox)
            if iou > best_iou:
                best_iou = iou
                best_idx = i

        return best_idx


def _compute_iou(a: tuple, b: tuple) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    intersection = (ix2 - ix1) * (iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - intersection

    return intersection / union if union > 0 else 0.0