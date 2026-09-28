"""
Multi-object tracker using Ultralytics built-in ByteTrack integration.

Wraps ``model.track()`` so the rest of the application only works with
application-level Pydantic schemas (TrackedObject / TrackFrameResult).

ByteTrack Limitations
---------------------
* Track IDs are *locally* persistent within a single video session.
* A physically identical object may receive a **new** track ID after prolonged
  disappearance or heavy occlusion because ByteTrack does not perform
  re-identification.
* Track IDs from one video MUST NOT leak into another — always create a fresh
  ``ObjectTracker`` instance per video processing job.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from app.schemas.tracking import (
    TrackFrameResult,
    TrackedObject,
    TrackingBoundingBox,
)

logger = logging.getLogger(__name__)


class ObjectTracker:
    """
    Object tracking wrapper using Ultralytics ``model.track()`` with ByteTrack.

    Parameters
    ----------
    model : ultralytics.YOLO
        An already-loaded YOLO model instance (reuses the detector's model).
    tracker_config : str
        Ultralytics tracker YAML name.  ``"bytetrack.yaml"`` or ``"botsort.yaml"``.
    conf : float
        Minimum detection confidence for tracking.
    iou : float
        IoU threshold for NMS / tracker association.
    device : str
        Inference device (``"cpu"``, ``"0"``, …).
    imgsz : int
        Inference image size.
    max_det : int
        Maximum detections per frame.
    """

    def __init__(
        self,
        model: Any,
        tracker_config: str = "bytetrack.yaml",
        conf: float = 0.25,
        iou: float = 0.5,
        device: str = "cpu",
        imgsz: int = 640,
        max_det: int = 100,
    ):
        if model is None:
            raise ValueError("ObjectTracker requires a loaded YOLO model instance.")
        self.model = model
        self.tracker_config = tracker_config
        self.conf = conf
        self.iou = iou
        self.device = device
        self.imgsz = imgsz
        self.max_det = max_det
        logger.info(
            "ObjectTracker initialised — tracker=%s  conf=%.2f  iou=%.2f  device=%s",
            tracker_config, conf, iou, device,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def track_frame(self, frame: np.ndarray, frame_index: int = 0) -> TrackFrameResult:
        """
        Run YOLO detection + ByteTrack tracking on a single frame.

        This calls ``model.track()`` which internally performs detection *and*
        tracking in a single pass — the YOLO model is NOT invoked separately.

        Parameters
        ----------
        frame : np.ndarray
            BGR image (OpenCV format).
        frame_index : int
            Current frame number (used for statistics only).

        Returns
        -------
        TrackFrameResult
            Structured list of tracked objects for this frame.
        """
        try:
            results = self.model.track(
                source=frame,
                tracker=self.tracker_config,
                conf=self.conf,
                iou=self.iou,
                device=self.device,
                imgsz=self.imgsz,
                max_det=self.max_det,
                persist=True,   # critical: maintain state between frames
                verbose=False,
            )

            tracked_objects = self._parse_results(results)

            return TrackFrameResult(
                frame_index=frame_index,
                tracked_objects=tracked_objects,
                object_count=len(tracked_objects),
            )

        except Exception as exc:
            logger.error("Tracking failed on frame %d: %s", frame_index, exc)
            return TrackFrameResult(
                frame_index=frame_index,
                tracked_objects=[],
                object_count=0,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_results(results) -> List[TrackedObject]:
        """Convert raw Ultralytics tracking results to application schemas."""
        tracked: List[TrackedObject] = []

        if not results or len(results) == 0:
            return tracked

        result = results[0]
        names: Dict[int, str] = getattr(result, "names", {})
        boxes = getattr(result, "boxes", None)

        if boxes is None:
            return tracked

        # Track IDs may be absent when tracker loses all objects
        track_ids = None
        if hasattr(boxes, "id") and boxes.id is not None:
            track_ids = boxes.id.cpu().numpy().astype(int).flatten()

        xyxy_arr = boxes.xyxy.cpu().numpy()
        conf_arr = boxes.conf.cpu().numpy()
        cls_arr = boxes.cls.cpu().numpy().astype(int)

        for i in range(len(xyxy_arr)):
            # Skip detections without a track ID
            if track_ids is None or i >= len(track_ids):
                continue

            track_id = int(track_ids[i])
            class_id = int(cls_arr[i])
            class_name = names.get(class_id, f"class_{class_id}")
            confidence = round(float(conf_arr[i]), 4)

            x1, y1, x2, y2 = (
                float(xyxy_arr[i][0]),
                float(xyxy_arr[i][1]),
                float(xyxy_arr[i][2]),
                float(xyxy_arr[i][3]),
            )

            center_x = round((x1 + x2) / 2.0, 2)
            center_y = round((y1 + y2) / 2.0, 2)

            tracked.append(
                TrackedObject(
                    track_id=track_id,
                    class_id=class_id,
                    class_name=class_name,
                    confidence=confidence,
                    bounding_box=TrackingBoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    center_x=center_x,
                    center_y=center_y,
                )
            )

        return tracked
