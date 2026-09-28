"""
PPE Detector — YOLO-based PPE detection abstraction.

Loads a YOLO model (either the shared main model or a dedicated PPE model)
and returns structured PPE detection results. The model is loaded once and
reused across frames.

IMPORTANT: This module inspects the model's class names to determine whether
PPE classes (helmet, vest, etc.) are actually available. If they are not,
PPE detection is marked unavailable and no detections are fabricated.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from app.schemas.ppe import PPEDetection

logger = logging.getLogger(__name__)

# Module-level cache so we don't reload PPE models per pipeline.
_PPE_MODEL_CACHE: Dict[str, Any] = {}


class PPEDetector:
    """
    YOLO-based PPE detector.

    Parameters
    ----------
    model_path : str or None
        Path to a dedicated PPE YOLO model. If empty/None, the caller is
        expected to supply the shared model via ``set_shared_model()``.
    confidence_threshold : float
        Minimum confidence for PPE detections.
    device : str
        Inference device (cpu / cuda / mps).
    image_size : int
        YOLO inference image size.
    helmet_classes : set[str]
        Class names in the model that correspond to helmets.
    vest_classes : set[str]
        Class names in the model that correspond to vests.
    glove_classes : set[str]
        Class names in the model that correspond to gloves.
    shoe_classes : set[str]
        Class names in the model that correspond to safety shoes.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.40,
        device: str = "cpu",
        image_size: int = 640,
        helmet_classes: Optional[Set[str]] = None,
        vest_classes: Optional[Set[str]] = None,
        glove_classes: Optional[Set[str]] = None,
        shoe_classes: Optional[Set[str]] = None,
    ):
        self.model_path = model_path or ""
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.image_size = image_size

        # Expected PPE class-name sets (all lowercase)
        self.helmet_classes = {c.lower() for c in (helmet_classes or {"helmet", "safety helmet"})}
        self.vest_classes = {c.lower() for c in (vest_classes or {"vest", "safety vest"})}
        self.glove_classes = {c.lower() for c in (glove_classes or {"gloves", "glove"})}
        self.shoe_classes = {c.lower() for c in (shoe_classes or {"boots", "safety shoes"})}

        # Union of all expected PPE class names
        self._all_ppe_names: Set[str] = (
            self.helmet_classes | self.vest_classes | self.glove_classes | self.shoe_classes
        )

        # Reverse lookup: class name -> PPE category
        self._name_to_category: Dict[str, str] = {}
        for name in self.helmet_classes:
            self._name_to_category[name] = "helmet"
        for name in self.vest_classes:
            self._name_to_category[name] = "vest"
        for name in self.glove_classes:
            self._name_to_category[name] = "gloves"
        for name in self.shoe_classes:
            self._name_to_category[name] = "shoes"

        # Model state
        self.model: Any = None
        self._model_names: Dict[int, str] = {}  # class_id -> name from model
        self._available_categories: Set[str] = set()
        self._is_available: bool = False
        self._unavailable_reason: str = "PPE model is not loaded."
        self._uses_shared_model: bool = False

    # -----------------------------------------------------------------
    # Model Loading
    # -----------------------------------------------------------------

    def load_model(self) -> None:
        """Load a dedicated PPE YOLO model from ``self.model_path``."""
        if not self.model_path:
            self._is_available = False
            self._unavailable_reason = "No PPE model path configured."
            return

        cache_key = f"ppe:{self.model_path}:{self.device}"
        if cache_key in _PPE_MODEL_CACHE:
            self.model = _PPE_MODEL_CACHE[cache_key]
            self._inspect_model_classes()
            return

        try:
            from ultralytics import YOLO

            logger.info("Loading PPE YOLO model from %s on %s...", self.model_path, self.device)
            loaded = YOLO(self.model_path)
            _PPE_MODEL_CACHE[cache_key] = loaded
            self.model = loaded
            self._inspect_model_classes()
            logger.info("PPE YOLO model loaded successfully.")
        except ImportError:
            logger.warning("Ultralytics package not installed — PPE detection unavailable.")
            self._is_available = False
            self._unavailable_reason = "Ultralytics package is not installed."
        except Exception as exc:
            logger.warning("Could not load PPE model (%s): %s", self.model_path, exc)
            self._is_available = False
            self._unavailable_reason = f"Failed to load PPE model: {exc}"

    def set_shared_model(self, model: Any) -> None:
        """
        Use the main YOLO model (already loaded) for PPE detection.
        Only works if the model actually contains PPE classes.
        """
        self._uses_shared_model = True
        self.model = model
        self._inspect_model_classes()

    def _inspect_model_classes(self) -> None:
        """Check which PPE classes the loaded model supports."""
        if self.model is None:
            self._is_available = False
            self._unavailable_reason = "PPE model is not loaded."
            return

        try:
            names = getattr(self.model, "names", None)
            if names is None:
                self._is_available = False
                self._unavailable_reason = "Model does not expose class names."
                return

            if isinstance(names, dict):
                self._model_names = {int(k): str(v) for k, v in names.items()}
            elif isinstance(names, (list, tuple)):
                self._model_names = {i: str(n) for i, n in enumerate(names)}
            else:
                self._model_names = {}

            model_name_set = {n.lower() for n in self._model_names.values()}

            # Determine which PPE categories the model can detect
            found_categories: Set[str] = set()
            if model_name_set & self.helmet_classes:
                found_categories.add("helmet")
            if model_name_set & self.vest_classes:
                found_categories.add("vest")
            if model_name_set & self.glove_classes:
                found_categories.add("gloves")
            if model_name_set & self.shoe_classes:
                found_categories.add("shoes")

            self._available_categories = found_categories

            if found_categories:
                self._is_available = True
                self._unavailable_reason = ""
                logger.info(
                    "PPE detector: model supports categories %s from %d total classes.",
                    sorted(found_categories),
                    len(self._model_names),
                )
            else:
                self._is_available = False
                self._unavailable_reason = (
                    "Configured YOLO model does not contain the required PPE classes. "
                    f"Model classes: {sorted(model_name_set)}. "
                    f"Expected PPE classes: {sorted(self._all_ppe_names)}."
                )
                logger.info("PPE detection unavailable: %s", self._unavailable_reason)

        except Exception as exc:
            self._is_available = False
            self._unavailable_reason = f"Error inspecting model classes: {exc}"
            logger.warning("PPE model inspection failed: %s", exc)

    # -----------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        return self._is_available

    @property
    def available_categories(self) -> Set[str]:
        return set(self._available_categories)

    @property
    def unavailable_reason(self) -> str:
        return self._unavailable_reason

    @property
    def model_class_names(self) -> List[str]:
        return sorted(self._model_names.values())

    # -----------------------------------------------------------------
    # Detection
    # -----------------------------------------------------------------

    def detect(self, frame: np.ndarray) -> List[PPEDetection]:
        """
        Run PPE detection on a single video frame.

        Returns structured ``PPEDetection`` objects for all PPE items found.
        Returns an empty list if PPE detection is unavailable.
        """
        if not self._is_available or self.model is None:
            return []

        try:
            results = self.model.predict(
                source=frame,
                conf=self.confidence_threshold,
                device=self.device,
                imgsz=self.image_size,
                verbose=False,
            )

            detections: List[PPEDetection] = []

            if results and len(results) > 0:
                result = results[0]
                names = result.names if hasattr(result, "names") else self._model_names

                if hasattr(result, "boxes") and result.boxes is not None:
                    xyxy_arr = result.boxes.xyxy.cpu().numpy()
                    conf_arr = result.boxes.conf.cpu().numpy()
                    cls_arr = result.boxes.cls.cpu().numpy()

                    for i in range(len(xyxy_arr)):
                        class_id = int(cls_arr[i])
                        class_name = names.get(class_id, f"class_{class_id}")
                        normalised = class_name.strip().lower()

                        # Only emit PPE-relevant detections
                        category = self._name_to_category.get(normalised)
                        if category is None:
                            continue

                        coords = xyxy_arr[i]
                        detections.append(
                            PPEDetection(
                                class_id=class_id,
                                class_name=class_name,
                                ppe_category=category,
                                confidence=round(float(conf_arr[i]), 4),
                                bbox={
                                    "x1": float(coords[0]),
                                    "y1": float(coords[1]),
                                    "x2": float(coords[2]),
                                    "y2": float(coords[3]),
                                },
                            )
                        )

            return detections

        except Exception as exc:
            logger.warning("PPE detection error: %s", exc)
            return []


# =====================================================================
# PPE Analyzer — Association, Compliance & Temporal Confirmation
# =====================================================================


class _TrackPPEState:
    """Mutable per-track PPE state used internally by PPEAnalyzer."""

    __slots__ = (
        "track_id",
        "helmet_missing_frames",
        "vest_missing_frames",
        "gloves_missing_frames",
        "shoes_missing_frames",
        "helmet_last_seen_frame",
        "vest_last_seen_frame",
        "gloves_last_seen_frame",
        "shoes_last_seen_frame",
        "violation_emitted",
    )

    def __init__(self, track_id: int):
        self.track_id = track_id
        self.helmet_missing_frames = 0
        self.vest_missing_frames = 0
        self.gloves_missing_frames = 0
        self.shoes_missing_frames = 0
        self.helmet_last_seen_frame = -1
        self.vest_last_seen_frame = -1
        self.gloves_last_seen_frame = -1
        self.shoes_last_seen_frame = -1
        # category -> bool indicating a violation event was recently created
        self.violation_emitted: Dict[str, bool] = {}


def is_inside_person(
    ppe_bbox: Dict[str, float],
    person_bbox: Any,
) -> bool:
    """
    Check if the centre of a PPE bounding box lies inside a person bounding box.

    Parameters
    ----------
    ppe_bbox : dict with keys x1, y1, x2, y2
    person_bbox : object with attributes x1, y1, x2, y2  (TrackingBoundingBox)
    """
    ppe_cx = (ppe_bbox["x1"] + ppe_bbox["x2"]) / 2.0
    ppe_cy = (ppe_bbox["y1"] + ppe_bbox["y2"]) / 2.0

    px1 = float(person_bbox.x1)
    py1 = float(person_bbox.y1)
    px2 = float(person_bbox.x2)
    py2 = float(person_bbox.y2)

    return px1 <= ppe_cx <= px2 and py1 <= ppe_cy <= py2


def calculate_bbox_overlap(
    ppe_bbox: Dict[str, float],
    person_bbox: Any,
) -> float:
    """
    Calculate intersection-over-area of PPE bbox relative to the person bbox.

    Returns a value in [0, 1] where 1 means the PPE bbox is entirely inside
    the person bbox. Returns 0 when there is no overlap.
    """
    px1 = float(person_bbox.x1)
    py1 = float(person_bbox.y1)
    px2 = float(person_bbox.x2)
    py2 = float(person_bbox.y2)

    ix1 = max(ppe_bbox["x1"], px1)
    iy1 = max(ppe_bbox["y1"], py1)
    ix2 = min(ppe_bbox["x2"], px2)
    iy2 = min(ppe_bbox["y2"], py2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    intersection = (ix2 - ix1) * (iy2 - iy1)
    ppe_area = max((ppe_bbox["x2"] - ppe_bbox["x1"]) * (ppe_bbox["y2"] - ppe_bbox["y1"]), 1e-6)
    return intersection / ppe_area


def associate_ppe_to_persons(
    ppe_detections: List[PPEDetection],
    tracked_persons: List[Any],
    iou_threshold: float = 0.10,
) -> Dict[int, Set[str]]:
    """
    Associate PPE detections with tracked persons using geometric containment.

    For each PPE detection, find the person whose bounding box best contains it.
    A PPE item is assigned to a person if either:
      1. Its centre lies inside the person bounding box, OR
      2. Its overlap with the person bbox exceeds ``iou_threshold``.

    When a PPE detection is ambiguous (overlaps multiple persons equally)
    it is assigned to the person with the highest overlap.

    Returns
    -------
    dict mapping track_id -> set of PPE categories detected on that person.
    """
    result: Dict[int, Set[str]] = {p.track_id: set() for p in tracked_persons}

    for det in ppe_detections:
        best_track_id: Optional[int] = None
        best_overlap: float = 0.0

        for person in tracked_persons:
            bb = person.bounding_box

            # Check centre containment first (fast path)
            if is_inside_person(det.bbox, bb):
                overlap = calculate_bbox_overlap(det.bbox, bb)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_track_id = person.track_id
            else:
                # Fallback: check overlap threshold
                overlap = calculate_bbox_overlap(det.bbox, bb)
                if overlap >= iou_threshold and overlap > best_overlap:
                    best_overlap = overlap
                    best_track_id = person.track_id

        if best_track_id is not None:
            result[best_track_id].add(det.ppe_category)

    return result


class PPEAnalyzer:
    """
    Vision-level PPE compliance analyzer.

    Maintains per-track PPE state, applies temporal confirmation to suppress
    transient missed detections, and emits structured PPE safety events.
    Does not interact with FastAPI or MongoDB.
    """

    def __init__(
        self,
        ppe_detector: PPEDetector,
        required_ppe: Optional[Set[str]] = None,
        association_iou_threshold: float = 0.10,
        missing_confirmation_frames: int = 5,
        event_cooldown_seconds: float = 10.0,
        person_classes: Optional[Set[str]] = None,
    ):
        self.ppe_detector = ppe_detector
        self.required_ppe: Set[str] = required_ppe or {"helmet", "vest"}
        self.association_iou_threshold = association_iou_threshold
        self.missing_confirmation_frames = max(1, missing_confirmation_frames)
        self.event_cooldown_seconds = event_cooldown_seconds
        self.person_classes = {c.lower() for c in (person_classes or {"person"})}

        # Per-track mutable state (reset between jobs)
        self._track_states: Dict[int, _TrackPPEState] = {}

        # Cooldown: event_key -> last emitted timestamp
        self._cooldown_state: Dict[str, float] = {}

        # Accumulated events for the current job session
        self._session_events: List[Dict[str, Any]] = []

        # Final per-worker compliance records
        self._worker_compliance: Dict[int, Dict[str, Any]] = {}

    # -----------------------------------------------------------------
    # Reset
    # -----------------------------------------------------------------

    def reset(self) -> None:
        """Clear all per-job state."""
        self._track_states.clear()
        self._cooldown_state.clear()
        self._session_events.clear()
        self._worker_compliance.clear()

    # -----------------------------------------------------------------
    # Cooldown / deduplication
    # -----------------------------------------------------------------

    def _is_cooling_down(self, event_key: str, timestamp: float) -> bool:
        last = self._cooldown_state.get(event_key)
        if last is None:
            return False
        return (timestamp - last) < self.event_cooldown_seconds

    def _record_cooldown(self, event_key: str, timestamp: float) -> None:
        self._cooldown_state[event_key] = timestamp

    # -----------------------------------------------------------------
    # Per-frame analysis
    # -----------------------------------------------------------------

    def analyze_frame(
        self,
        frame: np.ndarray,
        tracked_objects: List[Any],
        frame_number: int,
        timestamp: float,
    ) -> List[Dict[str, Any]]:
        """
        Run PPE detection on the frame, associate with tracked persons, update
        temporal state, and return any new safety events.

        Parameters
        ----------
        frame : np.ndarray
            BGR video frame.
        tracked_objects : list
            TrackedObject instances from ObjectTracker.
        frame_number : int
            0-indexed frame number.
        timestamp : float
            Elapsed video time in seconds.

        Returns
        -------
        list of dict
            PPE safety events triggered on this frame.
        """
        if not self.ppe_detector.is_available:
            return []

        # Identify persons among tracked objects
        persons = [
            obj for obj in tracked_objects
            if str(getattr(obj, "class_name", "")).strip().lower() in self.person_classes
        ]

        if not persons:
            return []

        # Run PPE detection
        ppe_detections = self.ppe_detector.detect(frame)

        # Associate PPE with persons
        associations = associate_ppe_to_persons(
            ppe_detections, persons, self.association_iou_threshold,
        )

        # Update per-track state and generate events
        frame_events: List[Dict[str, Any]] = []
        active_track_ids = set()

        for person in persons:
            tid = person.track_id
            active_track_ids.add(tid)
            detected_categories = associations.get(tid, set())

            # Ensure state exists
            if tid not in self._track_states:
                self._track_states[tid] = _TrackPPEState(tid)
            state = self._track_states[tid]

            # Update each required PPE category
            for category in self.required_ppe:
                missing_attr = f"{category}_missing_frames"
                seen_attr = f"{category}_last_seen_frame"

                if not hasattr(state, missing_attr):
                    continue

                if category in detected_categories:
                    # PPE detected → reset missing counter
                    setattr(state, missing_attr, 0)
                    setattr(state, seen_attr, frame_number)
                else:
                    # PPE not detected → increment missing counter
                    current_missing = getattr(state, missing_attr, 0)
                    setattr(state, missing_attr, current_missing + 1)

                    # Check temporal confirmation threshold
                    if getattr(state, missing_attr) >= self.missing_confirmation_frames:
                        event_key = f"ppe_{category}_missing:track_{tid}"
                        if not self._is_cooling_down(event_key, timestamp):
                            self._record_cooldown(event_key, timestamp)
                            event = self._create_violation_event(
                                tid, category, frame_number, timestamp,
                            )
                            frame_events.append(event)

            # Update worker compliance record
            detected_list = sorted(detected_categories & self.required_ppe)
            missing_list = sorted(self.required_ppe - detected_categories)

            # Only mark non-compliant if confirmed missing (temporal check)
            confirmed_missing = []
            for cat in missing_list:
                missing_attr = f"{cat}_missing_frames"
                if hasattr(state, missing_attr):
                    if getattr(state, missing_attr) >= self.missing_confirmation_frames:
                        confirmed_missing.append(cat)

            if confirmed_missing:
                status = "non_compliant"
            elif detected_list:
                status = "compliant"
            else:
                status = "unknown"

            self._worker_compliance[tid] = {
                "track_id": tid,
                "required_ppe": sorted(self.required_ppe),
                "detected_ppe": detected_list,
                "missing_ppe": confirmed_missing,
                "status": status,
            }

        # Clean up state for tracks no longer active
        stale_ids = [tid for tid in self._track_states if tid not in active_track_ids]
        for tid in stale_ids:
            del self._track_states[tid]

        # Check for multiple missing PPE → escalate severity
        for ev in frame_events:
            tid = ev["track_ids"][0] if ev["track_ids"] else None
            if tid is not None:
                comp = self._worker_compliance.get(tid)
                if comp and len(comp.get("missing_ppe", [])) > 1:
                    ev["severity"] = "critical"
                    ev["event_type"] = "ppe_violation"
                    ev["message"] = (
                        f"Worker #{tid} is missing multiple required PPE items: "
                        f"{', '.join(comp['missing_ppe'])}."
                    )

        self._session_events.extend(frame_events)
        return frame_events

    # -----------------------------------------------------------------
    # Event creation
    # -----------------------------------------------------------------

    def _create_violation_event(
        self,
        track_id: int,
        missing_category: str,
        frame_number: int,
        timestamp: float,
    ) -> Dict[str, Any]:
        event_type_map = {
            "helmet": "helmet_missing",
            "vest": "vest_missing",
        }
        event_type = event_type_map.get(missing_category, "ppe_violation")

        return {
            "event_type": event_type,
            "severity": "high",
            "track_ids": [track_id],
            "zone_id": None,
            "distance": None,
            "missing_ppe": [missing_category],
            "frame_number": frame_number,
            "timestamp_seconds": round(timestamp, 2),
            "message": (
                f"Worker #{track_id} appears to be missing required "
                f"{missing_category} PPE."
            ),
        }

    # -----------------------------------------------------------------
    # Summary builders
    # -----------------------------------------------------------------

    def build_summary(self) -> Dict[str, Any]:
        """Build aggregate PPE summary for the completed job."""
        if not self.ppe_detector.is_available:
            return {
                "enabled": True,
                "available": False,
                "reason": self.ppe_detector.unavailable_reason,
                "workers_checked": 0,
                "compliant_workers": 0,
                "non_compliant_workers": 0,
                "unknown_workers": 0,
                "helmet_violations": 0,
                "vest_violations": 0,
            }

        compliant = 0
        non_compliant = 0
        unknown = 0
        helmet_violations = 0
        vest_violations = 0

        for comp in self._worker_compliance.values():
            s = comp.get("status", "unknown")
            if s == "compliant":
                compliant += 1
            elif s == "non_compliant":
                non_compliant += 1
                if "helmet" in comp.get("missing_ppe", []):
                    helmet_violations += 1
                if "vest" in comp.get("missing_ppe", []):
                    vest_violations += 1
            else:
                unknown += 1

        return {
            "enabled": True,
            "available": True,
            "reason": None,
            "workers_checked": len(self._worker_compliance),
            "compliant_workers": compliant,
            "non_compliant_workers": non_compliant,
            "unknown_workers": unknown,
            "helmet_violations": helmet_violations,
            "vest_violations": vest_violations,
        }

    def get_worker_compliance_list(self) -> List[Dict[str, Any]]:
        """Return final compliance records for all tracked workers."""
        return list(self._worker_compliance.values())
