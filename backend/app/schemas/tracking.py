"""
Pydantic schemas for multi-object tracking data.

These schemas define the application-level data structures for object tracking
output.  No raw Ultralytics objects are exposed through these models.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TrackingBoundingBox(BaseModel):
    """Axis-aligned bounding box coordinates (pixel space)."""
    x1: float
    y1: float
    x2: float
    y2: float


class TrackedObject(BaseModel):
    """
    A single object detected and tracked within a video frame.

    Attributes:
        track_id: Persistent ID assigned by the tracker across frames.
                  This is NOT the same as class_id.
        class_id: YOLO class index (e.g. 0 = person in COCO).
        class_name: Human-readable class label from the model.
        confidence: Detection confidence score [0, 1].
        bounding_box: Pixel-space bounding box.
        center_x: Horizontal center of the bounding box.
        center_y: Vertical center of the bounding box.
    """
    track_id: int
    class_id: int
    class_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_box: TrackingBoundingBox
    center_x: float
    center_y: float


class TrackFrameResult(BaseModel):
    """Tracking output for a single video frame."""
    frame_index: int
    tracked_objects: List[TrackedObject] = []
    object_count: int = 0


class TrackHistory(BaseModel):
    """
    Internal per-track lifecycle record maintained during processing.

    NOT stored in MongoDB by default — used for computing aggregate statistics.
    """
    track_id: int
    class_name: str
    first_seen_frame: int
    last_seen_frame: int
    detection_count: int = 0
    last_center: List[float] = Field(default_factory=lambda: [0.0, 0.0])


class TrackingSummary(BaseModel):
    """
    Aggregate tracking statistics for a completed video processing job.

    This is the structure persisted to MongoDB under the ``tracking`` field
    of a processing_jobs document.
    """
    enabled: bool = True
    tracker_type: str = "bytetrack"
    unique_track_count: int = 0
    max_active_tracks: int = 0
    tracks_by_class: Dict[str, int] = Field(default_factory=dict)
    tracked_detections: int = 0
    frames_with_tracks: int = 0
    average_objects_per_frame: float = 0.0
