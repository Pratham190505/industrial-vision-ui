"""
Safety Analyzer — rule-based computer-vision safety monitoring engine.

Responsibilities:
  - Restricted-zone violation detection via polygon point-in-polygon tests.
  - Person-forklift Euclidean proximity warnings.
  - Heuristic collision-risk assessment using velocity history and relative motion vectors.
  - In-memory event cooldown / deduplication scoped to the active processing job.
  - Computing aggregate SafetySummary statistics.

NOTE: Safety analysis in this module is heuristic and rule-based.
It does NOT perform certified physical collision prediction or medical/legal safety validation.
"""

from collections import deque
import logging
import math
from typing import Any, Deque, Dict, List, Optional, Set, Tuple
import cv2
import numpy as np

from app.schemas.safety import SafetySummary

logger = logging.getLogger(__name__)


class SafetyAnalyzer:
    """
    Vision-level safety analysis engine.

    Evaluates tracked objects on each frame and emits structured safety events.
    Does not interact directly with FastAPI or MongoDB.
    """

    def __init__(
        self,
        safety_enabled: bool = True,
        person_classes: Optional[Set[str]] = None,
        forklift_classes: Optional[Set[str]] = None,
        proximity_warning_distance: float = 100.0,
        collision_warning_distance: float = 50.0,
        restricted_zone_enabled: bool = True,
        event_cooldown_seconds: float = 5.0,
        velocity_window_frames: int = 5,
        zones: Optional[List[Dict[str, Any]]] = None,
    ):
        self.safety_enabled = safety_enabled
        self.person_classes = {c.strip().lower() for c in (person_classes or {"person"})}
        self.forklift_classes = {c.strip().lower() for c in (forklift_classes or {"forklift"})}
        self.proximity_warning_distance = proximity_warning_distance
        self.collision_warning_distance = collision_warning_distance
        self.restricted_zone_enabled = restricted_zone_enabled
        self.event_cooldown_seconds = event_cooldown_seconds
        self.velocity_window_frames = max(2, velocity_window_frames)

        # Preprocessed polygon zones: list of dicts with 'zone_id', 'name', 'polygon_np'
        self._zones: List[Dict[str, Any]] = []
        if zones:
            self.set_zones(zones)

        # In-memory per-job tracking state
        # track_id -> deque of (frame_number, timestamp_seconds, center_x, center_y)
        self._trajectory_history: Dict[int, Deque[Tuple[int, float, float, float]]] = {}

        # Cooldown: event_key -> last_emitted_timestamp_seconds
        self._cooldown_state: Dict[str, float] = {}

        # Track active presence in zones for entry/exit edge triggering:
        # (track_id, zone_id) -> bool (currently inside)
        self._active_zone_occupancy: Dict[Tuple[int, str], bool] = {}

        # Accumulated events for the current job session
        self._session_events: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Configuration and Reset
    # -------------------------------------------------------------------------

    def set_zones(self, zones: List[Dict[str, Any]]) -> None:
        """Parse and cache OpenCV-compatible polygons for restricted zones."""
        self._zones = []
        for z in zones:
            if not z.get("enabled", True):
                continue
            poly_coords = z.get("polygon", [])
            if len(poly_coords) < 3:
                continue
            try:
                poly_np = np.array(poly_coords, dtype=np.int32).reshape((-1, 1, 2))
                self._zones.append({
                    "zone_id": str(z.get("zone_id", z.get("_id", "unknown_zone"))),
                    "name": z.get("name", "Restricted Zone"),
                    "polygon_np": poly_np,
                    "raw_polygon": poly_coords,
                })
            except Exception as exc:
                logger.warning("Failed to parse zone polygon '%s': %s", z.get("name"), exc)

    def reset(self) -> None:
        """Reset all in-memory tracking state between video processing jobs."""
        self._trajectory_history.clear()
        self._cooldown_state.clear()
        self._active_zone_occupancy.clear()
        self._session_events.clear()

    # -------------------------------------------------------------------------
    # Object Class Classifiers
    # -------------------------------------------------------------------------

    def is_person(self, obj: Any) -> bool:
        """Check if tracked object matches configured person class names."""
        name = getattr(obj, "class_name", "")
        return str(name).strip().lower() in self.person_classes

    def is_forklift(self, obj: Any) -> bool:
        """Check if tracked object matches configured forklift class names."""
        name = getattr(obj, "class_name", "")
        return str(name).strip().lower() in self.forklift_classes

    # -------------------------------------------------------------------------
    # Velocity & Motion Helpers
    # -------------------------------------------------------------------------

    def _update_trajectory(self, track_id: int, frame_number: int, timestamp: float, cx: float, cy: float) -> None:
        if track_id not in self._trajectory_history:
            self._trajectory_history[track_id] = deque(maxlen=self.velocity_window_frames)
        self._trajectory_history[track_id].append((frame_number, timestamp, cx, cy))

    def _calculate_velocity(self, track_id: int) -> Optional[Tuple[float, float, float]]:
        """
        Estimate 2D velocity vector (vx, vy) and scalar speed (pixels/frame)
        over the stored trajectory window.
        Returns: (vx, vy, speed) or None if insufficient history.
        """
        history = self._trajectory_history.get(track_id)
        if not history or len(history) < 2:
            return None

        # Compare oldest in window with newest
        oldest_frame, _, old_x, old_y = history[0]
        newest_frame, _, new_x, new_y = history[-1]
        delta_frames = newest_frame - oldest_frame
        if delta_frames <= 0:
            return None

        vx = (new_x - old_x) / delta_frames
        vy = (new_y - old_y) / delta_frames
        speed = math.sqrt(vx * vx + vy * vy)
        return (vx, vy, speed)

    # -------------------------------------------------------------------------
    # Deduplication & Cooldown
    # -------------------------------------------------------------------------

    def _is_cooling_down(self, event_key: str, current_time: float) -> bool:
        last_time = self._cooldown_state.get(event_key)
        if last_time is None:
            return False
        return (current_time - last_time) < self.event_cooldown_seconds

    def _record_event_timestamp(self, event_key: str, current_time: float) -> None:
        self._cooldown_state[event_key] = current_time

    # -------------------------------------------------------------------------
    # Main Analysis Entrypoint
    # -------------------------------------------------------------------------

    def analyze_frame(
        self,
        tracked_objects: List[Any],
        frame_width: int,
        frame_height: int,
        frame_number: int,
        timestamp: float,
    ) -> List[Dict[str, Any]]:
        """
        Analyze a single video frame's tracked objects for safety events.

        Parameters
        ----------
        tracked_objects : list
            TrackedObject schema instances from ObjectTracker.
        frame_width : int
            Video frame width in pixels.
        frame_height : int
            Video frame height in pixels.
        frame_number : int
            0-indexed frame number.
        timestamp : float
            Elapsed video time in seconds.

        Returns
        -------
        list of dict
            Safety events triggered on this frame.
        """
        if not self.safety_enabled or not tracked_objects:
            return []

        frame_events: List[Dict[str, Any]] = []

        # 1. Update trajectory histories
        people: List[Any] = []
        forklifts: List[Any] = []

        for obj in tracked_objects:
            cx = float(getattr(obj, "center_x", 0.0))
            cy = float(getattr(obj, "center_y", 0.0))
            self._update_trajectory(obj.track_id, frame_number, timestamp, cx, cy)

            if self.is_person(obj):
                people.append(obj)
            elif self.is_forklift(obj):
                forklifts.append(obj)

        # 2. Check Restricted Zones
        if self.restricted_zone_enabled and self._zones:
            zone_events = self._check_restricted_zones(people, frame_number, timestamp)
            frame_events.extend(zone_events)

        # 3. Check Person–Forklift Proximity and Collision Risk
        if people and forklifts:
            prox_and_collision_events = self._check_proximity_and_collision(
                people, forklifts, frame_number, timestamp
            )
            frame_events.extend(prox_and_collision_events)

        # Accumulate in session history
        self._session_events.extend(frame_events)
        return frame_events

    # -------------------------------------------------------------------------
    # Safety Rule Evaluators
    # -------------------------------------------------------------------------

    def _check_restricted_zones(
        self,
        people: List[Any],
        frame_number: int,
        timestamp: float,
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        current_frame_occupants: Set[Tuple[int, str]] = set()

        for person in people:
            pt = (float(person.center_x), float(person.center_y))

            for zone in self._zones:
                zone_id = zone["zone_id"]
                zone_name = zone["name"]
                poly_np = zone["polygon_np"]

                # OpenCV pointPolygonTest: >= 0 means inside or on edge
                is_inside = cv2.pointPolygonTest(poly_np, pt, False) >= 0

                occupancy_key = (person.track_id, zone_id)
                if is_inside:
                    current_frame_occupants.add(occupancy_key)
                    was_inside = self._active_zone_occupancy.get(occupancy_key, False)
                    event_key = f"restricted_zone_violation:person{person.track_id}:zone{zone_id}"

                    # Trigger event if newly entered OR if cooldown expired while remaining inside
                    should_emit = not was_inside or not self._is_cooling_down(event_key, timestamp)

                    if should_emit:
                        self._record_event_timestamp(event_key, timestamp)
                        events.append({
                            "event_type": "restricted_zone_violation",
                            "severity": "high",
                            "track_ids": [person.track_id],
                            "zone_id": zone_id,
                            "distance": None,
                            "frame_number": frame_number,
                            "timestamp_seconds": round(timestamp, 2),
                            "message": f"Person #{person.track_id} entered restricted zone '{zone_name}'.",
                        })

        # Update active zone occupancy
        # Any person who was inside previously but not in current_frame_occupants has left
        for key in list(self._active_zone_occupancy.keys()):
            if key not in current_frame_occupants:
                self._active_zone_occupancy[key] = False
        for key in current_frame_occupants:
            self._active_zone_occupancy[key] = True

        return events

    def _check_proximity_and_collision(
        self,
        people: List[Any],
        forklifts: List[Any],
        frame_number: int,
        timestamp: float,
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        for person in people:
            px, py = float(person.center_x), float(person.center_y)
            p_vel = self._calculate_velocity(person.track_id)

            for forklift in forklifts:
                fx, fy = float(forklift.center_x), float(forklift.center_y)
                f_vel = self._calculate_velocity(forklift.track_id)

                dx = px - fx
                dy = py - fy
                distance = math.sqrt(dx * dx + dy * dy)

                pair_key_suffix = f"{min(person.track_id, forklift.track_id)}_{max(person.track_id, forklift.track_id)}"

                # Check if approaching
                is_approaching = False
                closing_speed = 0.0

                if p_vel is not None and f_vel is not None and distance > 0.0:
                    # Relative velocity of person with respect to forklift
                    vx_rel = p_vel[0] - f_vel[0]
                    vy_rel = p_vel[1] - f_vel[1]
                    # Relative displacement vector from forklift to person: (dx, dy)
                    # Dot product of position and relative velocity:
                    # If negative, the distance between them is decreasing
                    dot = dx * vx_rel + dy * vy_rel
                    if dot < -0.1:
                        is_approaching = True
                        closing_speed = -dot / distance
                elif distance > 0.0:
                    # Fallback velocity check using distance delta from previous frame if available
                    p_hist = self._trajectory_history.get(person.track_id)
                    f_hist = self._trajectory_history.get(forklift.track_id)
                    if p_hist and f_hist and len(p_hist) >= 2 and len(f_hist) >= 2:
                        prev_p = p_hist[-2]
                        prev_f = f_hist[-2]
                        prev_dist = math.sqrt((prev_p[2] - prev_f[2]) ** 2 + (prev_p[3] - prev_f[3]) ** 2)
                        if (prev_dist - distance) > 0.5:
                            is_approaching = True
                            closing_speed = prev_dist - distance

                # Rule 1: Collision Risk (distance <= collision_warning_distance)
                if distance <= self.collision_warning_distance:
                    event_key = f"collision_risk:pair_{pair_key_suffix}"

                    if not self._is_cooling_down(event_key, timestamp):
                        # Determine heuristic severity
                        if is_approaching:
                            if distance <= (self.collision_warning_distance * 0.5) or closing_speed >= 3.0:
                                severity = "critical"
                            else:
                                severity = "high"
                        else:
                            severity = "warning"

                        self._record_event_timestamp(event_key, timestamp)
                        events.append({
                            "event_type": "collision_risk",
                            "severity": severity,
                            "track_ids": [person.track_id, forklift.track_id],
                            "zone_id": None,
                            "distance": round(distance, 1),
                            "frame_number": frame_number,
                            "timestamp_seconds": round(timestamp, 2),
                            "message": (
                                f"Collision risk ({severity}): Person #{person.track_id} and Forklift #{forklift.track_id} "
                                f"at {distance:.1f}px (approaching={is_approaching})."
                            ),
                        })

                # Rule 2: Proximity Warning (distance <= proximity_warning_distance)
                elif distance <= self.proximity_warning_distance:
                    event_key = f"proximity_warning:pair_{pair_key_suffix}"

                    if not self._is_cooling_down(event_key, timestamp):
                        self._record_event_timestamp(event_key, timestamp)
                        events.append({
                            "event_type": "proximity_warning",
                            "severity": "warning",
                            "track_ids": [person.track_id, forklift.track_id],
                            "zone_id": None,
                            "distance": round(distance, 1),
                            "frame_number": frame_number,
                            "timestamp_seconds": round(timestamp, 2),
                            "message": (
                                f"Proximity warning: Person #{person.track_id} is within warning distance "
                                f"of Forklift #{forklift.track_id} ({distance:.1f}px)."
                            ),
                        })

        return events

    # -------------------------------------------------------------------------
    # Aggregate Summary Builder
    # -------------------------------------------------------------------------

    def build_summary(self) -> SafetySummary:
        """
        Produce aggregate safety statistics for the completed video processing job.
        """
        if not self.safety_enabled:
            return SafetySummary(enabled=False)

        violations = 0
        proximity = 0
        collision = 0
        severity_counts = {"low": 0, "medium": 0, "warning": 0, "high": 0, "critical": 0}

        for ev in self._session_events:
            etype = ev.get("event_type")
            sev = ev.get("severity", "warning").lower()

            if etype == "restricted_zone_violation":
                violations += 1
            elif etype == "proximity_warning":
                proximity += 1
            elif etype == "collision_risk":
                collision += 1

            if sev in severity_counts:
                severity_counts[sev] += 1
            else:
                severity_counts[sev] = 1

        # Map 'warning' into 'medium' if desired for 4-level schema compliance while keeping warning accessible
        medium_total = severity_counts.get("medium", 0) + severity_counts.get("warning", 0)
        final_counts = {
            "low": severity_counts.get("low", 0),
            "medium": medium_total,
            "high": severity_counts.get("high", 0),
            "critical": severity_counts.get("critical", 0),
        }

        return SafetySummary(
            enabled=True,
            total_events=len(self._session_events),
            restricted_zone_violations=violations,
            proximity_warnings=proximity,
            collision_risk_events=collision,
            severity_counts=final_counts,
        )
