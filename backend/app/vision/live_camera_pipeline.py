"""
Live Camera Pipeline — Real-time frame processing for webcam feeds.

Processes individual frames received from the browser webcam, executing
object tracking, safety zone/proximity/collision heuristics, PPE compliance,
and inventory counts without writing annotated video files to disk.
"""

from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional
import cv2
import numpy as np

from app.schemas.live import (
    LiveBBox,
    LiveCenter,
    LiveFrameResponse,
    LiveInventoryResult,
    LivePPEResult,
    LiveSafetyResult,
    LiveTrackedObject,
)

logger = logging.getLogger(__name__)


class LiveCameraPipeline:
    """
    Executes real-time computer vision inference on sampled webcam frames.
    Maintains session-isolated tracker and analyzer state.
    """

    def process_frame(
        self,
        frame: np.ndarray,
        session_state: Any,
    ) -> Dict[str, Any]:
        """
        Process a single image frame using the session's tracker and analyzers.

        Parameters
        ----------
        frame : np.ndarray
            BGR image array.
        session_state : LiveSessionState
            In-memory state containing tracker, analyzers, and timing.

        Returns
        -------
        dict
            Structured dictionary serializable to LiveFrameResponse.
        """
        start_time = time.perf_counter()

        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            raise ValueError("Invalid image frame provided.")

        height, width = frame.shape[:2]
        session_state.frame_counter += 1
        frame_number = session_state.frame_counter
        elapsed_sec = max(0.0, time.time() - session_state.start_time)

        # 1. Run YOLO + Object Tracking
        tracked_objects = []
        if session_state.tracker is not None:
            try:
                frame_result = session_state.tracker.track_frame(
                    frame=frame,
                    frame_index=frame_number,
                )
                tracked_objects = getattr(frame_result, "tracked_objects", [])
            except Exception as trk_err:
                logger.error("Live tracking error on frame %d: %s", frame_number, trk_err)

        # 2. Convert tracked objects to JSON-serializable list
        objects_list: List[Dict[str, Any]] = []
        for obj in tracked_objects:
            track_id = int(getattr(obj, "track_id", 0))
            class_name = str(getattr(obj, "class_name", "unknown"))
            confidence = round(float(getattr(obj, "confidence", 0.0)), 4)

            session_state.unique_track_ids.add(track_id)

            bbox_obj = getattr(obj, "bounding_box", None)
            if bbox_obj is not None:
                x1 = float(bbox_obj.x1)
                y1 = float(bbox_obj.y1)
                x2 = float(bbox_obj.x2)
                y2 = float(bbox_obj.y2)
            elif hasattr(obj, "to_xyxy"):
                coords = obj.to_xyxy()
                x1, y1, x2, y2 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
            else:
                x1, y1, x2, y2 = 0.0, 0.0, 0.0, 0.0

            center_x = round(float(getattr(obj, "center_x", (x1 + x2) / 2.0)), 2)
            center_y = round(float(getattr(obj, "center_y", (y1 + y2) / 2.0)), 2)

            objects_list.append({
                "track_id": track_id,
                "class_name": class_name,
                "confidence": confidence,
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "center": {"x": center_x, "y": center_y},
            })

        # 3. Safety Analysis (Restricted Zones, Proximity, Collision Risk)
        safety_result: Dict[str, Any] = {"events": [], "risk_level": "normal"}
        new_safety_events: List[Dict[str, Any]] = []
        if session_state.safety_analyzer and session_state.safety_analyzer.safety_enabled:
            try:
                events = session_state.safety_analyzer.analyze_frame(
                    tracked_objects=tracked_objects,
                    frame_width=width,
                    frame_height=height,
                    frame_number=frame_number,
                    timestamp=elapsed_sec,
                )
                risk = "normal"
                for ev in events:
                    sev = ev.get("severity", "warning").lower()
                    if sev in ["critical", "high"]:
                        risk = "critical" if sev == "critical" else "high"
                    elif sev in ["warning", "medium"] and risk == "normal":
                        risk = "warning"

                    new_safety_events.append({
                        "event_type": ev.get("event_type"),
                        "severity": ev.get("severity", "warning"),
                        "track_ids": ev.get("track_ids", []),
                        "message": ev.get("message", "Safety event detected."),
                        "distance": ev.get("distance"),
                        "zone_id": ev.get("zone_id"),
                        "timestamp_seconds": round(elapsed_sec, 2),
                    })

                safety_result["events"] = new_safety_events
                safety_result["risk_level"] = risk
                session_state.total_safety_events += len(new_safety_events)
            except Exception as safe_err:
                logger.warning("Safety analysis error in live frame %d: %s", frame_number, safe_err)
                safety_result["error"] = "Safety analysis temporarily unavailable."

        # 4. PPE Compliance Analysis
        ppe_result: Dict[str, Any] = {
            "enabled": False,
            "available": False,
            "workers": [],
            "violations_count": 0,
        }
        if session_state.ppe_analyzer is not None:
            ppe_result["enabled"] = True
            ppe_result["available"] = session_state.ppe_analyzer.ppe_detector.is_available
            if ppe_result["available"]:
                try:
                    session_state.ppe_analyzer.analyze_frame(
                        frame=frame,
                        tracked_objects=tracked_objects,
                        frame_number=frame_number,
                        timestamp=elapsed_sec,
                    )
                    workers_list = []
                    violations = 0
                    for comp in session_state.ppe_analyzer._worker_compliance.values():
                        workers_list.append({
                            "track_id": comp["track_id"],
                            "status": comp["status"],
                            "required_ppe": comp["required_ppe"],
                            "detected_ppe": comp["detected_ppe"],
                            "missing_ppe": comp["missing_ppe"],
                        })
                        if comp["status"] == "non_compliant":
                            violations += 1
                    ppe_result["workers"] = workers_list
                    ppe_result["violations_count"] = violations
                except Exception as ppe_err:
                    logger.warning("PPE analysis error in live frame %d: %s", frame_number, ppe_err)
                    ppe_result["error"] = "PPE analysis temporarily unavailable."

        # 5. Inventory Counting Analysis
        inventory_result: Dict[str, Any] = {
            "enabled": False,
            "available": False,
            "counts": {},
            "unique_counts": {},
        }
        if session_state.inventory_analyzer is not None:
            inventory_result["enabled"] = session_state.inventory_analyzer.enabled
            inventory_result["available"] = session_state.inventory_analyzer.is_available
            if inventory_result["enabled"] and inventory_result["available"]:
                try:
                    inv_frame = session_state.inventory_analyzer.analyze_frame(
                        tracked_objects=tracked_objects,
                        frame_number=frame_number,
                        timestamp_seconds=elapsed_sec,
                    )
                    inventory_result["counts"] = inv_frame.get("visible_counts", {})
                    inventory_result["unique_counts"] = {
                        cls: len(session_state.inventory_analyzer.unique_track_ids.get(cls, set()))
                        for cls in session_state.inventory_analyzer.available_classes
                    }
                except Exception as inv_err:
                    logger.warning("Inventory analysis error in live frame %d: %s", frame_number, inv_err)
                    inventory_result["error"] = "Inventory analysis temporarily unavailable."

        processing_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        session_state.processing_times.append(processing_time_ms)

        return {
            "session_id": session_state.session_id,
            "frame_number": frame_number,
            "processing_time_ms": processing_time_ms,
            "frame_width": width,
            "frame_height": height,
            "objects": objects_list,
            "safety": safety_result,
            "ppe": ppe_result,
            "inventory": inventory_result,
        }
