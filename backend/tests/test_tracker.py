"""
Unit tests for app.vision.tracker.ObjectTracker.

All tests mock the Ultralytics model to avoid GPU/model dependencies.
"""

from unittest.mock import MagicMock, PropertyMock
import numpy as np
import pytest

from app.vision.tracker import ObjectTracker


# ---------------------------------------------------------------------------
# Helpers — build mock Ultralytics results
# ---------------------------------------------------------------------------

def _make_mock_tensor(values):
    """Return a mock tensor with .cpu().numpy() returning *values* as ndarray."""
    arr = np.array(values)
    inner = MagicMock()
    inner.numpy.return_value = arr
    tensor = MagicMock()
    tensor.cpu.return_value = inner
    return tensor


def _make_mock_result(detections, names=None):
    """
    Build a single mock Ultralytics Result object.

    Parameters
    ----------
    detections : list[dict]
        Each dict: ``{"xyxy": [x1,y1,x2,y2], "conf": float, "cls": int, "id": int}``
    names : dict
        Class-id → class-name map.  Defaults to ``{0: "person", 1: "forklift"}``.
    """
    if names is None:
        names = {0: "person", 1: "forklift", 2: "box"}

    boxes = MagicMock()
    boxes.xyxy = _make_mock_tensor([d["xyxy"] for d in detections])
    boxes.conf = _make_mock_tensor([d["conf"] for d in detections])
    boxes.cls = _make_mock_tensor([d["cls"] for d in detections])

    ids = [d.get("id") for d in detections]
    if any(tid is not None for tid in ids):
        boxes.id = _make_mock_tensor(ids)
    else:
        boxes.id = None

    result = MagicMock()
    result.names = names
    result.boxes = boxes
    return result


def _build_model(results_sequence=None):
    """
    Return a mock YOLO model whose ``.track()`` returns sequential results.

    If *results_sequence* is ``None`` a single empty result list is used.
    """
    model = MagicMock()
    if results_sequence is None:
        model.track.return_value = []
    else:
        model.track.side_effect = results_sequence
    return model


# ---------------------------------------------------------------------------
# Tests — Initialisation
# ---------------------------------------------------------------------------

class TestTrackerInit:

    def test_init_requires_model(self):
        with pytest.raises(ValueError, match="requires a loaded YOLO model"):
            ObjectTracker(model=None)

    def test_init_stores_config(self):
        model = MagicMock()
        tracker = ObjectTracker(
            model=model,
            tracker_config="bytetrack.yaml",
            conf=0.3,
            iou=0.6,
        )
        assert tracker.tracker_config == "bytetrack.yaml"
        assert tracker.conf == 0.3
        assert tracker.iou == 0.6

    def test_init_default_values(self):
        model = MagicMock()
        tracker = ObjectTracker(model=model)
        assert tracker.tracker_config == "bytetrack.yaml"
        assert tracker.conf == 0.25
        assert tracker.iou == 0.5
        assert tracker.device == "cpu"


# ---------------------------------------------------------------------------
# Tests — track_frame output structure
# ---------------------------------------------------------------------------

class TestTrackFrame:

    def test_returns_track_frame_result(self):
        result = _make_mock_result([
            {"xyxy": [10, 20, 50, 80], "conf": 0.9, "cls": 0, "id": 1},
        ])
        model = _build_model([[result]])
        tracker = ObjectTracker(model=model)

        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        out = tracker.track_frame(frame, frame_index=0)

        assert out.frame_index == 0
        assert out.object_count == 1
        assert len(out.tracked_objects) == 1

    def test_tracked_object_fields(self):
        result = _make_mock_result([
            {"xyxy": [100, 120, 230, 450], "conf": 0.88, "cls": 0, "id": 5},
        ])
        model = _build_model([[result]])
        tracker = ObjectTracker(model=model)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        out = tracker.track_frame(frame)

        obj = out.tracked_objects[0]
        assert obj.track_id == 5
        assert obj.class_id == 0
        assert obj.class_name == "person"
        assert obj.confidence == 0.88
        assert obj.bounding_box.x1 == 100.0
        assert obj.bounding_box.y1 == 120.0
        assert obj.bounding_box.x2 == 230.0
        assert obj.bounding_box.y2 == 450.0
        assert obj.center_x == 165.0
        assert obj.center_y == 285.0

    def test_track_id_differs_from_class_id(self):
        """track_id != class_id — critical invariant."""
        result = _make_mock_result([
            {"xyxy": [10, 10, 50, 50], "conf": 0.9, "cls": 0, "id": 12},
        ])
        model = _build_model([[result]])
        tracker = ObjectTracker(model=model)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        obj = tracker.track_frame(frame).tracked_objects[0]

        assert obj.class_id == 0
        assert obj.track_id == 12
        assert obj.class_id != obj.track_id

    def test_multiple_objects(self):
        result = _make_mock_result([
            {"xyxy": [10, 10, 50, 50], "conf": 0.9, "cls": 0, "id": 1},
            {"xyxy": [60, 60, 100, 100], "conf": 0.85, "cls": 0, "id": 2},
            {"xyxy": [110, 110, 150, 150], "conf": 0.7, "cls": 1, "id": 3},
        ])
        model = _build_model([[result]])
        tracker = ObjectTracker(model=model)

        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        out = tracker.track_frame(frame)

        assert out.object_count == 3
        ids = {o.track_id for o in out.tracked_objects}
        assert ids == {1, 2, 3}

    def test_empty_detections(self):
        model = _build_model([[]])
        tracker = ObjectTracker(model=model)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        out = tracker.track_frame(frame)

        assert out.object_count == 0
        assert out.tracked_objects == []

    def test_no_track_ids_assigned(self):
        """When the tracker has no IDs (boxes.id is None), return empty."""
        result = _make_mock_result([
            {"xyxy": [10, 10, 50, 50], "conf": 0.9, "cls": 0, "id": None},
        ])
        # Force boxes.id to None (no tracking IDs assigned)
        result.boxes.id = None
        model = _build_model([[result]])
        tracker = ObjectTracker(model=model)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        out = tracker.track_frame(frame)
        assert out.object_count == 0

    def test_bounding_box_validity(self):
        result = _make_mock_result([
            {"xyxy": [10, 20, 50, 80], "conf": 0.9, "cls": 0, "id": 1},
        ])
        model = _build_model([[result]])
        tracker = ObjectTracker(model=model)

        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        obj = tracker.track_frame(frame).tracked_objects[0]
        bb = obj.bounding_box

        assert bb.x1 < bb.x2
        assert bb.y1 < bb.y2
        assert bb.x1 >= 0
        assert bb.y1 >= 0


# ---------------------------------------------------------------------------
# Tests — Persistence across frames
# ---------------------------------------------------------------------------

class TestTrackerPersistence:

    def test_persist_flag_is_set(self):
        """Verify model.track() is called with persist=True."""
        model = MagicMock()
        model.track.return_value = []
        tracker = ObjectTracker(model=model)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        tracker.track_frame(frame)

        _, kwargs = model.track.call_args
        assert kwargs.get("persist") is True

    def test_tracker_config_passed(self):
        model = MagicMock()
        model.track.return_value = []
        tracker = ObjectTracker(model=model, tracker_config="botsort.yaml")

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        tracker.track_frame(frame)

        _, kwargs = model.track.call_args
        assert kwargs.get("tracker") == "botsort.yaml"


# ---------------------------------------------------------------------------
# Tests — Error handling
# ---------------------------------------------------------------------------

class TestTrackerErrors:

    def test_track_frame_exception_returns_empty(self):
        model = MagicMock()
        model.track.side_effect = RuntimeError("GPU exploded")
        tracker = ObjectTracker(model=model)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        out = tracker.track_frame(frame)

        assert out.object_count == 0
        assert out.tracked_objects == []
