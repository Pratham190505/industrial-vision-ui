"""
Tests for LiveCameraPipeline — real-time single frame inference and analysis integration.
"""

from unittest.mock import MagicMock
import numpy as np
import pytest

from app.schemas.tracking import TrackedObject, TrackingBoundingBox
from app.services.live_session_service import LiveSessionState
from app.vision.live_camera_pipeline import LiveCameraPipeline


@pytest.fixture
def blank_frame():
    """Create a 480x640 BGR blank test frame."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


def test_pipeline_invalid_frame():
    pipeline = LiveCameraPipeline()
    state = LiveSessionState(session_id="test_sess", user_id="test_usr")

    with pytest.raises(ValueError):
        pipeline.process_frame(None, state)

    with pytest.raises(ValueError):
        pipeline.process_frame(np.array([]), state)


def test_pipeline_single_frame_tracking(blank_frame):
    pipeline = LiveCameraPipeline()
    state = LiveSessionState(session_id="sess_track", user_id="usr_track")

    # Mock tracker returning a single tracked person
    mock_tracker = MagicMock()
    mock_obj = TrackedObject(
        track_id=12,
        class_id=0,
        class_name="person",
        confidence=0.92,
        bounding_box=TrackingBoundingBox(x1=100.0, y1=150.0, x2=220.0, y2=400.0),
        center_x=160.0,
        center_y=275.0,
    )
    mock_result = MagicMock()
    mock_result.tracked_objects = [mock_obj]
    mock_tracker.track_frame.return_value = mock_result
    state.tracker = mock_tracker

    res = pipeline.process_frame(blank_frame, state)

    assert res["session_id"] == "sess_track"
    assert res["frame_number"] == 1
    assert res["frame_width"] == 640
    assert res["frame_height"] == 480
    assert len(res["objects"]) == 1

    obj = res["objects"][0]
    assert obj["track_id"] == 12
    assert obj["class_name"] == "person"
    assert obj["confidence"] == 0.92
    assert obj["bbox"]["x1"] == 100.0
    assert obj["center"]["x"] == 160.0
    assert 12 in state.unique_track_ids


def test_pipeline_tracker_persistence(blank_frame):
    pipeline = LiveCameraPipeline()
    state = LiveSessionState(session_id="sess_persist", user_id="usr_persist")

    mock_tracker = MagicMock()
    state.tracker = mock_tracker

    # Frame 1: Object #10 appears
    obj1 = TrackedObject(
        track_id=10,
        class_id=0,
        class_name="forklift",
        confidence=0.88,
        bounding_box=TrackingBoundingBox(x1=50, y1=50, x2=200, y2=200),
        center_x=125,
        center_y=125,
    )
    res1 = MagicMock()
    res1.tracked_objects = [obj1]
    mock_tracker.track_frame.return_value = res1

    out1 = pipeline.process_frame(blank_frame, state)
    assert out1["frame_number"] == 1
    assert out1["objects"][0]["track_id"] == 10

    # Frame 2: Object #10 moves to center x=130
    obj2 = TrackedObject(
        track_id=10,
        class_id=0,
        class_name="forklift",
        confidence=0.89,
        bounding_box=TrackingBoundingBox(x1=55, y1=50, x2=205, y2=200),
        center_x=130,
        center_y=125,
    )
    res2 = MagicMock()
    res2.tracked_objects = [obj2]
    mock_tracker.track_frame.return_value = res2

    out2 = pipeline.process_frame(blank_frame, state)
    assert out2["frame_number"] == 2
    assert out2["objects"][0]["track_id"] == 10
    assert state.unique_track_ids == {10}


def test_pipeline_safety_integration(blank_frame):
    pipeline = LiveCameraPipeline()
    state = LiveSessionState(session_id="sess_safe", user_id="usr_safe")

    mock_safety = MagicMock()
    mock_safety.safety_enabled = True
    mock_safety.analyze_frame.return_value = [
        {
            "event_type": "restricted_zone_violation",
            "severity": "critical",
            "track_ids": [5],
            "message": "Person 5 in Restricted Zone A",
            "distance": None,
            "zone_id": "zone_a",
        }
    ]
    state.safety_analyzer = mock_safety

    out = pipeline.process_frame(blank_frame, state)
    safety = out["safety"]
    assert safety["risk_level"] == "critical"
    assert len(safety["events"]) == 1
    assert safety["events"][0]["event_type"] == "restricted_zone_violation"
    assert state.total_safety_events == 1


def test_pipeline_inventory_and_ppe_integration(blank_frame):
    pipeline = LiveCameraPipeline()
    state = LiveSessionState(session_id="sess_full", user_id="usr_full")

    # Inventory mock
    mock_inventory = MagicMock()
    mock_inventory.enabled = True
    mock_inventory.is_available = True
    mock_inventory.analyze_frame.return_value = {
        "visible_counts": {"box": 8, "pallet": 3},
    }
    mock_inventory.unique_track_ids = {"box": {1, 2, 3, 4, 5, 6, 7, 8}, "pallet": {10, 11, 12}}
    mock_inventory.available_classes = ["box", "pallet"]
    state.inventory_analyzer = mock_inventory

    # PPE mock
    mock_ppe = MagicMock()
    mock_ppe.ppe_detector.is_available = True
    mock_ppe._worker_compliance = {
        1: {
            "track_id": 1,
            "status": "non_compliant",
            "required_ppe": ["helmet", "vest"],
            "detected_ppe": ["vest"],
            "missing_ppe": ["helmet"],
        }
    }
    state.ppe_analyzer = mock_ppe

    out = pipeline.process_frame(blank_frame, state)

    # Check inventory output
    assert out["inventory"]["enabled"] is True
    assert out["inventory"]["counts"]["box"] == 8
    assert out["inventory"]["unique_counts"]["pallet"] == 3

    # Check PPE output
    assert out["ppe"]["enabled"] is True
    assert out["ppe"]["violations_count"] == 1
    assert out["ppe"]["workers"][0]["track_id"] == 1
    assert out["ppe"]["workers"][0]["missing_ppe"] == ["helmet"]


def test_pipeline_resilience_on_analyzer_error(blank_frame):
    pipeline = LiveCameraPipeline()
    state = LiveSessionState(session_id="sess_err", user_id="usr_err")

    mock_safety = MagicMock()
    mock_safety.safety_enabled = True
    mock_safety.analyze_frame.side_effect = RuntimeError("Safety model crash")
    state.safety_analyzer = mock_safety

    # The pipeline should NOT crash; it should catch the error and return safe response
    out = pipeline.process_frame(blank_frame, state)
    assert "error" in out["safety"]
    assert out["safety"]["risk_level"] == "normal"
