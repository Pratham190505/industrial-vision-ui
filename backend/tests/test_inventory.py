"""
Tests for InventoryAnalyzer vision layer.

Tests counting, tracking unique IDs, statistics, and model availability.
"""

import pytest
from app.vision.inventory import InventoryAnalyzer


class MockTrackedObject:
    def __init__(self, track_id: int, class_name: str, confidence: float = 0.90, bbox=None):
        self.track_id = track_id
        self.class_name = class_name
        self.confidence = confidence
        self.bbox = bbox or [10.0, 10.0, 50.0, 50.0]

    def to_xyxy(self):
        return self.bbox


# -----------------------------------------------------------------------------
# Model Availability Tests
# -----------------------------------------------------------------------------

def test_model_inspection_all_available():
    analyzer = InventoryAnalyzer(configured_classes=["box", "pallet", "crate"])
    model_classes = {0: "person", 1: "box", 2: "pallet", 3: "crate", 4: "forklift"}
    analyzer.inspect_model_classes(model_classes)

    assert analyzer.is_available is True
    assert analyzer.available_classes == {"box", "pallet", "crate"}
    assert analyzer.unavailable_classes == set()
    assert analyzer.reason is None


def test_model_inspection_none_available():
    analyzer = InventoryAnalyzer(configured_classes=["pallet", "crate"])
    # Generic COCO model has person, bicycle, car, but not pallet or crate
    model_classes = {0: "person", 1: "bicycle", 2: "car"}
    analyzer.inspect_model_classes(model_classes)

    assert analyzer.is_available is False
    assert analyzer.available_classes == set()
    assert analyzer.unavailable_classes == {"pallet", "crate"}
    assert "not available" in analyzer.reason.lower()


def test_model_inspection_partial_available():
    analyzer = InventoryAnalyzer(configured_classes=["box", "pallet", "crate"])
    model_classes = ["person", "box", "car"]  # list format
    analyzer.inspect_model_classes(model_classes)

    assert analyzer.is_available is True
    assert analyzer.available_classes == {"box"}
    assert analyzer.unavailable_classes == {"pallet", "crate"}
    assert analyzer.reason is None


def test_model_inspection_disabled():
    analyzer = InventoryAnalyzer(configured_classes=["box"], enabled=False)
    analyzer.inspect_model_classes(["box"])

    assert analyzer.is_available is False
    assert "disabled" in analyzer.reason.lower()


def test_model_inspection_empty_or_none():
    analyzer = InventoryAnalyzer(configured_classes=["box"])
    analyzer.inspect_model_classes(None)

    assert analyzer.is_available is False
    assert "not loaded" in analyzer.reason.lower() or "no model" in analyzer.reason.lower()


# -----------------------------------------------------------------------------
# Counting Tests
# -----------------------------------------------------------------------------

def test_zero_inventory_objects():
    analyzer = InventoryAnalyzer(configured_classes=["box", "pallet"])
    analyzer.inspect_model_classes(["box", "pallet", "person"])

    # Frame with person only
    tracked = [MockTrackedObject(1, "person", 0.95)]
    res = analyzer.analyze_frame(tracked, frame_number=0, timestamp_seconds=0.0)

    assert res["visible_counts"] == {"box": 0, "pallet": 0}
    assert len(res["tracked_objects"]) == 0

    summary = analyzer.build_summary()
    assert summary["counts"]["box"]["current_visible_count"] == 0
    assert summary["counts"]["box"]["unique_track_count"] == 0


def test_single_inventory_object():
    analyzer = InventoryAnalyzer(configured_classes=["box", "pallet"])
    analyzer.inspect_model_classes(["box", "pallet"])

    tracked = [MockTrackedObject(track_id=10, class_name="box", confidence=0.88)]
    res = analyzer.analyze_frame(tracked, frame_number=0, timestamp_seconds=0.0)

    assert res["visible_counts"]["box"] == 1
    assert res["visible_counts"]["pallet"] == 0
    assert len(res["tracked_objects"]) == 1
    assert res["tracked_objects"][0]["track_id"] == 10

    summary = analyzer.build_summary()
    assert summary["counts"]["box"]["current_visible_count"] == 1
    assert summary["counts"]["box"]["unique_track_count"] == 1


def test_multiple_objects_and_classes():
    analyzer = InventoryAnalyzer(configured_classes=["box", "pallet"])
    analyzer.inspect_model_classes(["box", "pallet"])

    tracked = [
        MockTrackedObject(track_id=1, class_name="box", confidence=0.92),
        MockTrackedObject(track_id=2, class_name="box", confidence=0.85),
        MockTrackedObject(track_id=3, class_name="pallet", confidence=0.78),
    ]
    res = analyzer.analyze_frame(tracked, frame_number=0, timestamp_seconds=0.0)

    assert res["visible_counts"]["box"] == 2
    assert res["visible_counts"]["pallet"] == 1

    summary = analyzer.build_summary()
    assert summary["counts"]["box"]["current_visible_count"] == 2
    assert summary["counts"]["box"]["unique_track_count"] == 2
    assert summary["counts"]["pallet"]["current_visible_count"] == 1
    assert summary["counts"]["pallet"]["unique_track_count"] == 1


def test_duplicate_track_ids_do_not_increase_unique_count():
    analyzer = InventoryAnalyzer(configured_classes=["box"])
    analyzer.inspect_model_classes(["box"])

    # Frame 0: Box #1 and #2 visible
    analyzer.analyze_frame(
        [MockTrackedObject(1, "box"), MockTrackedObject(2, "box")],
        frame_number=0,
        timestamp_seconds=0.0,
    )
    # Frame 1: Same Box #1 and #2 still visible
    analyzer.analyze_frame(
        [MockTrackedObject(1, "box"), MockTrackedObject(2, "box")],
        frame_number=1,
        timestamp_seconds=0.033,
    )
    # Frame 2: Box #1 visible and Box #3 appears
    analyzer.analyze_frame(
        [MockTrackedObject(1, "box"), MockTrackedObject(3, "box")],
        frame_number=2,
        timestamp_seconds=0.066,
    )

    summary = analyzer.build_summary()
    # In frame 2, currently visible is 2 boxes (#1 and #3)
    assert summary["counts"]["box"]["current_visible_count"] == 2
    # Unique tracks across session is 3 (#1, #2, #3)
    assert summary["counts"]["box"]["unique_track_count"] == 3


def test_confidence_threshold_filtering():
    analyzer = InventoryAnalyzer(configured_classes=["box"], confidence_threshold=0.60)
    analyzer.inspect_model_classes(["box"])

    tracked = [
        MockTrackedObject(1, "box", confidence=0.75),  # above threshold
        MockTrackedObject(2, "box", confidence=0.45),  # below threshold
    ]
    res = analyzer.analyze_frame(tracked, frame_number=0, timestamp_seconds=0.0)

    assert res["visible_counts"]["box"] == 1
    assert len(res["tracked_objects"]) == 1
    assert res["tracked_objects"][0]["track_id"] == 1


# -----------------------------------------------------------------------------
# Statistics Tests
# -----------------------------------------------------------------------------

def test_inventory_statistics_calculation():
    analyzer = InventoryAnalyzer(configured_classes=["box"])
    analyzer.inspect_model_classes(["box"])

    # Frame 0: 3 boxes
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in [1, 2, 3]], frame_number=0, timestamp_seconds=0.0)
    # Frame 1: 5 boxes
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in [1, 2, 3, 4, 5]], frame_number=1, timestamp_seconds=0.1)
    # Frame 2: 2 boxes
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in [1, 2]], frame_number=2, timestamp_seconds=0.2)
    # Frame 3: 0 boxes
    analyzer.analyze_frame([], frame_number=3, timestamp_seconds=0.3)

    summary = analyzer.build_summary()
    box_stats = summary["counts"]["box"]

    assert box_stats["current_visible_count"] == 0
    assert box_stats["max_visible_count"] == 5
    assert box_stats["min_visible_count"] == 2
    assert box_stats["unique_track_count"] == 5
    assert box_stats["frames_with_inventory"] == 3
    # Total visible instances = 3 + 5 + 2 + 0 = 10 across 4 frames -> avg 2.5
    assert box_stats["average_visible_count"] == 2.5
    assert box_stats["first_seen_frame"] == 0
    assert box_stats["last_seen_frame"] == 2


def test_reset_clears_inventory_state():
    analyzer = InventoryAnalyzer(configured_classes=["box"])
    analyzer.inspect_model_classes(["box"])

    analyzer.analyze_frame([MockTrackedObject(1, "box")], frame_number=0, timestamp_seconds=0.0)
    assert analyzer.build_summary()["counts"]["box"]["unique_track_count"] == 1

    analyzer.reset()
    summary = analyzer.build_summary()
    assert summary["counts"]["box"]["unique_track_count"] == 0
    assert summary["counts"]["box"]["current_visible_count"] == 0
    assert len(analyzer.snapshots) == 0
    assert len(analyzer.events) == 0
