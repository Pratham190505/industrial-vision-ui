"""
WarehouseVision AI — Inventory Counting, Tracking & Monitoring Layer.

This module provides the in-memory InventoryAnalyzer that operates directly
on tracked objects produced by the object tracker. It computes visible counts,
tracks unique objects, calculates session statistics, detects periodic snapshot
count changes, and monitors low-stock thresholds without accessing MongoDB or
re-running YOLO.
"""

import logging
from typing import Any, Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)


class InventoryAnalyzer:
    """
    In-memory analyzer for warehouse inventory monitoring.

    Analyzes tracked objects across frames to compute visible counts,
    unique tracked IDs, cumulative statistics, periodic snapshots,
    count-change events, and low-stock alerts.
    """

    def __init__(
        self,
        configured_classes: Optional[Iterable[str]] = None,
        confidence_threshold: float = 0.40,
        count_mode: str = "visible",
        snapshot_interval_seconds: float = 10.0,
        change_threshold: int = 1,
        low_stock_enabled: bool = True,
        low_stock_thresholds: Optional[Dict[str, int]] = None,
        event_cooldown_seconds: float = 10.0,
        enabled: bool = True,
    ):
        self.enabled: bool = enabled
        self.confidence_threshold: float = confidence_threshold
        self.count_mode: str = count_mode
        self.snapshot_interval_seconds: float = max(0.1, snapshot_interval_seconds)
        self.change_threshold: int = max(1, change_threshold)
        self.low_stock_enabled: bool = low_stock_enabled
        self.event_cooldown_seconds: float = max(0.0, event_cooldown_seconds)

        # Normalize configured classes
        raw_classes = configured_classes or ["box", "pallet", "crate"]
        self.configured_classes: Set[str] = {
            c.strip().lower() for c in raw_classes if c and c.strip()
        }

        # Normalize low stock thresholds
        raw_thresholds = low_stock_thresholds or {"box": 5, "pallet": 2, "crate": 3}
        self.low_stock_thresholds: Dict[str, int] = {
            str(k).strip().lower(): int(v) for k, v in raw_thresholds.items()
        }

        # Model availability state
        self.available_classes: Set[str] = set()
        self.unavailable_classes: Set[str] = set(self.configured_classes)
        self.is_available: bool = False
        self.reason: Optional[str] = "Model classes have not been inspected."

        # Cumulative / session tracking state
        self.unique_track_ids: Dict[str, Set[int]] = {}
        self.stats: Dict[str, Dict[str, Any]] = {}
        self.snapshots: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []

        # Internal timing and snapshot state
        self.last_snapshot_time: float = -1e9
        self.last_snapshot_counts: Optional[Dict[str, int]] = None
        self.last_change_event_time: Dict[str, float] = {}
        self.last_low_stock_event_time: Dict[str, float] = {}
        self.total_frames_processed: int = 0

        self._init_class_containers()

    def _init_class_containers(self) -> None:
        """Initialize stats and track containers for all configured/available classes."""
        target_classes = self.available_classes if self.is_available else self.configured_classes
        for cls in target_classes:
            if cls not in self.unique_track_ids:
                self.unique_track_ids[cls] = set()
            if cls not in self.stats:
                self.stats[cls] = {
                    "current_visible_count": 0,
                    "max_visible_count": 0,
                    "min_visible_count": 0,
                    "frames_with_inventory": 0,
                    "total_visible_instances": 0,
                    "first_seen_frame": None,
                    "last_seen_frame": None,
                }

    # ------------------------------------------------------------------
    # Model Class Inspection
    # ------------------------------------------------------------------

    def inspect_model_classes(self, model_classes: Any) -> None:
        """
        Inspect YOLO model class names to determine which configured inventory
        classes are supported by the loaded model.

        Parameters
        ----------
        model_classes : dict or list or iterable or None
            YOLO model ``names`` mapping (e.g. {0: "person", 1: "bicycle", ...})
            or list of class names.
        """
        if not self.enabled:
            self.is_available = False
            self.reason = "Inventory monitoring is disabled."
            return

        if not model_classes:
            self.available_classes = set()
            self.unavailable_classes = set(self.configured_classes)
            self.is_available = False
            self.reason = "No model classes provided or YOLO model is not loaded."
            return

        # Extract normalized set of names from model
        if isinstance(model_classes, dict):
            supported_names = {str(v).strip().lower() for v in model_classes.values()}
        elif isinstance(model_classes, (list, tuple, set)):
            supported_names = {str(v).strip().lower() for v in model_classes}
        else:
            supported_names = set()

        self.available_classes = self.configured_classes.intersection(supported_names)
        self.unavailable_classes = self.configured_classes - self.available_classes

        if not self.available_classes:
            self.is_available = False
            self.reason = "Configured inventory classes are not available in the loaded YOLO model."
            logger.info("Inventory: no configured classes (%s) found in model.", sorted(self.configured_classes))
        else:
            self.is_available = True
            self.reason = None
            logger.info(
                "Inventory: available classes: %s, unavailable: %s",
                sorted(self.available_classes),
                sorted(self.unavailable_classes),
            )

        self._init_class_containers()

    # ------------------------------------------------------------------
    # Frame Analysis
    # ------------------------------------------------------------------

    def analyze_frame(
        self,
        tracked_objects: List[Any],
        frame_number: int,
        timestamp_seconds: float,
    ) -> Dict[str, Any]:
        """
        Analyze a single video frame for inventory objects.

        Filters tracked objects for available inventory classes, updates
        visible and cumulative statistics, evaluates periodic snapshots,
        and generates count-change or low-stock events when triggered.

        Parameters
        ----------
        tracked_objects : list
            List of TrackedObject instances or dicts containing object detections.
        frame_number : int
            Current frame index (0-based).
        timestamp_seconds : float
            Timestamp in seconds from the beginning of the video.

        Returns
        -------
        dict
            Structured inventory results for the frame including visible counts
            and tracked inventory objects.
        """
        if not self.enabled or not self.is_available:
            return {
                "visible_counts": {},
                "tracked_objects": [],
            }

        self.total_frames_processed += 1
        visible_counts: Dict[str, int] = {cls: 0 for cls in self.available_classes}
        matched_objects: List[Dict[str, Any]] = []

        try:
            # 1. Filter tracked objects for available inventory classes
            for obj in tracked_objects:
                # Handle TrackedObject dataclass or dict
                if isinstance(obj, dict):
                    class_name = str(obj.get("class_name", "")).strip().lower()
                    confidence = float(obj.get("confidence", 0.0))
                    track_id = int(obj.get("track_id", 0))
                    bbox = obj.get("bbox")
                else:
                    class_name = str(getattr(obj, "class_name", "")).strip().lower()
                    confidence = float(getattr(obj, "confidence", 0.0))
                    track_id = int(getattr(obj, "track_id", 0))
                    bbox = getattr(obj, "bbox", None)
                    if bbox is None and hasattr(obj, "to_xyxy"):
                        try:
                            bbox = obj.to_xyxy()
                        except Exception:
                            bbox = None

                if class_name in self.available_classes and confidence >= self.confidence_threshold:
                    visible_counts[class_name] += 1
                    self.unique_track_ids[class_name].add(track_id)
                    matched_objects.append({
                        "track_id": track_id,
                        "class_name": class_name,
                        "confidence": round(confidence, 4),
                        "bbox": bbox,
                    })

            # 2. Update cumulative statistics for each available class
            for cls in self.available_classes:
                count = visible_counts[cls]
                c_stats = self.stats[cls]
                c_stats["current_visible_count"] = count
                c_stats["total_visible_instances"] += count

                if count > c_stats["max_visible_count"]:
                    c_stats["max_visible_count"] = count

                if count > 0:
                    c_stats["frames_with_inventory"] += 1
                    if c_stats["frames_with_inventory"] == 1:
                        c_stats["min_visible_count"] = count
                    else:
                        c_stats["min_visible_count"] = min(c_stats["min_visible_count"], count)

                    if c_stats["first_seen_frame"] is None:
                        c_stats["first_seen_frame"] = frame_number
                    c_stats["last_seen_frame"] = frame_number

            # 3. Evaluate periodic snapshots and count changes
            time_since_snapshot = timestamp_seconds - self.last_snapshot_time
            is_snapshot_frame = (
                time_since_snapshot >= self.snapshot_interval_seconds
                or (frame_number == 0 and len(self.snapshots) == 0)
            )

            if is_snapshot_frame:
                snapshot = {
                    "timestamp_seconds": round(timestamp_seconds, 2),
                    "frame_number": frame_number,
                    "counts": dict(visible_counts),
                }
                self.snapshots.append(snapshot)

                # Compare with previous snapshot for count changes
                if self.last_snapshot_counts is not None:
                    for cls in self.available_classes:
                        prev_c = self.last_snapshot_counts.get(cls, 0)
                        curr_c = visible_counts[cls]
                        diff = curr_c - prev_c

                        if abs(diff) >= self.change_threshold:
                            last_event_time = self.last_change_event_time.get(cls, -1e9)
                            if (timestamp_seconds - last_event_time) >= self.event_cooldown_seconds:
                                direction = "increased" if diff > 0 else "decreased"
                                self.events.append({
                                    "event_type": "inventory_count_change",
                                    "class_name": cls,
                                    "previous_count": prev_c,
                                    "current_count": curr_c,
                                    "change": diff,
                                    "frame_number": frame_number,
                                    "timestamp_seconds": round(timestamp_seconds, 2),
                                    "message": f"Observed visible {cls} count {direction} by {abs(diff)}.",
                                })
                                self.last_change_event_time[cls] = timestamp_seconds

                self.last_snapshot_counts = dict(visible_counts)
                self.last_snapshot_time = timestamp_seconds

            # 4. Low-stock monitoring (checked per frame against event cooldown)
            if self.low_stock_enabled:
                for cls in self.available_classes:
                    thresh = self.low_stock_thresholds.get(cls)
                    if thresh is not None:
                        curr_c = visible_counts[cls]
                        if curr_c <= thresh:
                            last_low_time = self.last_low_stock_event_time.get(cls, -1e9)
                            if (timestamp_seconds - last_low_time) >= self.event_cooldown_seconds:
                                self.events.append({
                                    "event_type": "inventory_low_stock",
                                    "class_name": cls,
                                    "current_count": curr_c,
                                    "threshold": thresh,
                                    "frame_number": frame_number,
                                    "timestamp_seconds": round(timestamp_seconds, 2),
                                    "message": (
                                        f"Observed visible {cls} count ({curr_c}) is at or "
                                        f"below the configured threshold ({thresh})."
                                    ),
                                })
                                self.last_low_stock_event_time[cls] = timestamp_seconds

        except Exception as exc:
            logger.error("Error during inventory frame analysis at frame %d: %s", frame_number, exc, exc_info=True)

        return {
            "visible_counts": visible_counts,
            "tracked_objects": matched_objects,
        }

    # ------------------------------------------------------------------
    # Summary & Reset
    # ------------------------------------------------------------------

    def build_summary(self) -> Dict[str, Any]:
        """
        Build the cumulative inventory summary dictionary for the job.

        Returns
        -------
        dict
            Structured summary suitable for persisting into processing_jobs
            and returning via InventorySummary schema.
        """
        if not self.enabled:
            return {
                "enabled": False,
                "available_classes": [],
                "unavailable_classes": sorted(self.configured_classes),
                "reason": "Inventory monitoring is disabled.",
                "counts": {},
                "total_inventory_events": 0,
            }

        if not self.is_available:
            return {
                "enabled": True,
                "available_classes": [],
                "unavailable_classes": sorted(self.unavailable_classes),
                "reason": self.reason or "Configured inventory classes are not available in the loaded YOLO model.",
                "counts": {},
                "total_inventory_events": 0,
            }

        counts_summary: Dict[str, Dict[str, Any]] = {}
        for cls in sorted(self.available_classes):
            c_stats = self.stats[cls]
            frames_with_inv = c_stats["frames_with_inventory"]
            avg_count = (
                round(c_stats["total_visible_instances"] / self.total_frames_processed, 2)
                if self.total_frames_processed > 0
                else 0.0
            )

            counts_summary[cls] = {
                "current_visible_count": c_stats["current_visible_count"],
                "max_visible_count": c_stats["max_visible_count"],
                "min_visible_count": c_stats["min_visible_count"],
                "unique_track_count": len(self.unique_track_ids.get(cls, set())),
                "frames_with_inventory": frames_with_inv,
                "average_visible_count": avg_count,
                "first_seen_frame": c_stats["first_seen_frame"],
                "last_seen_frame": c_stats["last_seen_frame"],
            }

        return {
            "enabled": True,
            "available_classes": sorted(self.available_classes),
            "unavailable_classes": sorted(self.unavailable_classes),
            "reason": None,
            "counts": counts_summary,
            "total_inventory_events": len(self.events),
        }

    def reset(self) -> None:
        """Reset internal tracking state for a new processing session."""
        self.unique_track_ids = {}
        self.stats = {}
        self.snapshots = []
        self.events = []
        self.last_snapshot_time = -1e9
        self.last_snapshot_counts = None
        self.last_change_event_time = {}
        self.last_low_stock_event_time = {}
        self.total_frames_processed = 0
        self._init_class_containers()
