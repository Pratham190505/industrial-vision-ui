"""
Tracking service — business logic for object tracking.

Responsibilities:
  - Build tracker configuration from application settings.
  - Convert tracker output into aggregate statistics (TrackingSummary).
  - Maintain per-track lifecycle records during processing.
  - Never access HTTP/route concerns directly.
"""

import logging
from typing import Dict, Optional

from app.schemas.tracking import (
    TrackFrameResult,
    TrackHistory,
    TrackingSummary,
)

logger = logging.getLogger(__name__)


class TrackingStatisticsCollector:
    """
    Collects per-frame tracking output and produces aggregate statistics.

    Instantiate once per video processing job.
    """

    def __init__(self, tracker_type: str = "bytetrack"):
        self.tracker_type = tracker_type
        self._tracks: Dict[int, TrackHistory] = {}
        self._max_active: int = 0
        self._total_detections: int = 0
        self._frames_with_tracks: int = 0
        self._total_processed_frames: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, frame_result: TrackFrameResult) -> None:
        """
        Ingest a single frame's tracking result.

        Parameters
        ----------
        frame_result : TrackFrameResult
            Output of ``ObjectTracker.track_frame()``.
        """
        self._total_processed_frames += 1
        objects = frame_result.tracked_objects
        active_count = len(objects)

        if active_count > 0:
            self._frames_with_tracks += 1

        if active_count > self._max_active:
            self._max_active = active_count

        self._total_detections += active_count

        for obj in objects:
            tid = obj.track_id
            if tid in self._tracks:
                rec = self._tracks[tid]
                rec.last_seen_frame = frame_result.frame_index
                rec.detection_count += 1
                rec.last_center = [obj.center_x, obj.center_y]
            else:
                self._tracks[tid] = TrackHistory(
                    track_id=tid,
                    class_name=obj.class_name,
                    first_seen_frame=frame_result.frame_index,
                    last_seen_frame=frame_result.frame_index,
                    detection_count=1,
                    last_center=[obj.center_x, obj.center_y],
                )

    def build_summary(self) -> TrackingSummary:
        """
        Compute aggregate tracking statistics after the video is fully
        processed.

        Returns
        -------
        TrackingSummary
            Summary suitable for MongoDB persistence.
        """
        tracks_by_class: Dict[str, int] = {}
        for rec in self._tracks.values():
            tracks_by_class[rec.class_name] = tracks_by_class.get(rec.class_name, 0) + 1

        avg_per_frame = 0.0
        if self._total_processed_frames > 0:
            avg_per_frame = round(
                self._total_detections / self._total_processed_frames, 2
            )

        return TrackingSummary(
            enabled=True,
            tracker_type=self.tracker_type,
            unique_track_count=len(self._tracks),
            max_active_tracks=self._max_active,
            tracks_by_class=tracks_by_class,
            tracked_detections=self._total_detections,
            frames_with_tracks=self._frames_with_tracks,
            average_objects_per_frame=avg_per_frame,
        )

    def reset(self) -> None:
        """Clear all state.  Called automatically for a new video job."""
        self._tracks.clear()
        self._max_active = 0
        self._total_detections = 0
        self._frames_with_tracks = 0
        self._total_processed_frames = 0


def get_tracker_config_name(tracker_type: str) -> str:
    """
    Map application-level tracker type name to the Ultralytics YAML filename.

    Supported values:
        ``"bytetrack"``  → ``"bytetrack.yaml"``
        ``"botsort"``    → ``"botsort.yaml"``

    Raises ``ValueError`` for unknown tracker types to prevent arbitrary
    file-path injection.
    """
    _ALLOWED = {
        "bytetrack": "bytetrack.yaml",
        "botsort": "botsort.yaml",
    }
    config = _ALLOWED.get(tracker_type.lower())
    if config is None:
        raise ValueError(
            f"Unknown tracker type '{tracker_type}'. "
            f"Allowed values: {list(_ALLOWED.keys())}"
        )
    return config
