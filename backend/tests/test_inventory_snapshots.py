"""
Tests for InventoryAnalyzer periodic snapshots, count-change detection, and low-stock monitoring.
"""

import pytest
from app.vision.inventory import InventoryAnalyzer


class MockTrackedObject:
    def __init__(self, track_id: int, class_name: str, confidence: float = 0.90):
        self.track_id = track_id
        self.class_name = class_name
        self.confidence = confidence


# -----------------------------------------------------------------------------
# Snapshots Interval Tests
# -----------------------------------------------------------------------------

def test_periodic_snapshots_at_interval():
    analyzer = InventoryAnalyzer(
        configured_classes=["box"],
        snapshot_interval_seconds=10.0,
    )
    analyzer.inspect_model_classes(["box"])

    # Frame 0 at t=0.0 -> snapshot 1
    analyzer.analyze_frame([MockTrackedObject(1, "box")], frame_number=0, timestamp_seconds=0.0)
    assert len(analyzer.snapshots) == 1
    assert analyzer.snapshots[0]["counts"]["box"] == 1

    # Frame 10 at t=2.0 -> no new snapshot (< 10s)
    analyzer.analyze_frame([MockTrackedObject(1, "box")], frame_number=10, timestamp_seconds=2.0)
    assert len(analyzer.snapshots) == 1

    # Frame 20 at t=8.5 -> no new snapshot (< 10s)
    analyzer.analyze_frame([MockTrackedObject(1, "box")], frame_number=20, timestamp_seconds=8.5)
    assert len(analyzer.snapshots) == 1

    # Frame 30 at t=10.1 -> interval reached, snapshot 2 created!
    analyzer.analyze_frame([MockTrackedObject(1, "box"), MockTrackedObject(2, "box")], frame_number=30, timestamp_seconds=10.1)
    assert len(analyzer.snapshots) == 2
    assert analyzer.snapshots[1]["counts"]["box"] == 2
    assert analyzer.snapshots[1]["frame_number"] == 30
    assert analyzer.snapshots[1]["timestamp_seconds"] == 10.1


def test_snapshots_contain_all_available_classes():
    analyzer = InventoryAnalyzer(
        configured_classes=["box", "pallet"],
        snapshot_interval_seconds=5.0,
    )
    analyzer.inspect_model_classes(["box", "pallet"])

    analyzer.analyze_frame([MockTrackedObject(1, "box")], frame_number=0, timestamp_seconds=0.0)
    snap = analyzer.snapshots[0]
    assert snap["counts"] == {"box": 1, "pallet": 0}


# -----------------------------------------------------------------------------
# Count Change Detection Tests
# -----------------------------------------------------------------------------

def test_count_increase_event():
    analyzer = InventoryAnalyzer(
        configured_classes=["box"],
        snapshot_interval_seconds=5.0,
        change_threshold=2,
        event_cooldown_seconds=5.0,
        low_stock_enabled=False,
    )
    analyzer.inspect_model_classes(["box"])

    # Snapshot 1 at t=0.0 with 2 boxes
    analyzer.analyze_frame([MockTrackedObject(1, "box"), MockTrackedObject(2, "box")], frame_number=0, timestamp_seconds=0.0)
    change_events = [e for e in analyzer.events if e["event_type"] == "inventory_count_change"]
    assert len(change_events) == 0

    # Snapshot 2 at t=5.0 with 5 boxes (+3 increase, >= threshold 2)
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(1, 6)], frame_number=150, timestamp_seconds=5.0)

    change_events = [e for e in analyzer.events if e["event_type"] == "inventory_count_change"]
    assert len(change_events) == 1
    ev = change_events[0]
    assert ev["class_name"] == "box"
    assert ev["previous_count"] == 2
    assert ev["current_count"] == 5
    assert ev["change"] == 3
    assert "increased by 3" in ev["message"]


def test_count_decrease_event():
    analyzer = InventoryAnalyzer(
        configured_classes=["box"],
        snapshot_interval_seconds=5.0,
        change_threshold=1,
        event_cooldown_seconds=5.0,
    )
    analyzer.inspect_model_classes(["box"])

    # Snapshot 1 at t=0.0 with 10 boxes
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(10)], frame_number=0, timestamp_seconds=0.0)

    # Snapshot 2 at t=5.0 with 6 boxes (-4 decrease)
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(6)], frame_number=150, timestamp_seconds=5.0)

    change_events = [e for e in analyzer.events if e["event_type"] == "inventory_count_change"]
    assert len(change_events) == 1
    ev = change_events[0]
    assert ev["previous_count"] == 10
    assert ev["current_count"] == 6
    assert ev["change"] == -4
    assert "decreased by 4" in ev["message"]


def test_insignificant_change_does_not_trigger_event():
    analyzer = InventoryAnalyzer(
        configured_classes=["box"],
        snapshot_interval_seconds=5.0,
        change_threshold=3,  # Requires at least 3 difference
    )
    analyzer.inspect_model_classes(["box"])

    # Snapshot 1: 5 boxes
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(5)], frame_number=0, timestamp_seconds=0.0)

    # Snapshot 2: 6 boxes (+1 difference < threshold 3)
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(6)], frame_number=150, timestamp_seconds=5.0)

    change_events = [e for e in analyzer.events if e["event_type"] == "inventory_count_change"]
    assert len(change_events) == 0


def test_change_event_cooldown():
    analyzer = InventoryAnalyzer(
        configured_classes=["box"],
        snapshot_interval_seconds=2.0,
        change_threshold=1,
        event_cooldown_seconds=10.0,
    )
    analyzer.inspect_model_classes(["box"])

    # Snapshot 1: 5 boxes
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(5)], frame_number=0, timestamp_seconds=0.0)

    # Snapshot 2 at t=2.0: 2 boxes -> triggers change event
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(2)], frame_number=60, timestamp_seconds=2.0)
    change_events = [e for e in analyzer.events if e["event_type"] == "inventory_count_change"]
    assert len(change_events) == 1

    # Snapshot 3 at t=4.0: 7 boxes (+5 change, but within 10s cooldown) -> no duplicate event
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(7)], frame_number=120, timestamp_seconds=4.0)
    change_events = [e for e in analyzer.events if e["event_type"] == "inventory_count_change"]
    assert len(change_events) == 1

    # Snapshot 4 at t=12.5: 1 box (cooldown expired) -> triggers new change event
    analyzer.analyze_frame([MockTrackedObject(1, "box")], frame_number=375, timestamp_seconds=12.5)
    change_events = [e for e in analyzer.events if e["event_type"] == "inventory_count_change"]
    assert len(change_events) == 2


# -----------------------------------------------------------------------------
# Low-Stock Monitoring Tests
# -----------------------------------------------------------------------------

def test_low_stock_above_threshold_no_event():
    analyzer = InventoryAnalyzer(
        configured_classes=["box"],
        low_stock_enabled=True,
        low_stock_thresholds={"box": 3},
    )
    analyzer.inspect_model_classes(["box"])

    # 4 boxes visible > threshold 3
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(4)], frame_number=0, timestamp_seconds=0.0)
    low_stock = [e for e in analyzer.events if e["event_type"] == "inventory_low_stock"]
    assert len(low_stock) == 0


def test_low_stock_at_or_below_threshold():
    analyzer = InventoryAnalyzer(
        configured_classes=["box"],
        low_stock_enabled=True,
        low_stock_thresholds={"box": 5},
    )
    analyzer.inspect_model_classes(["box"])

    # 3 boxes visible <= threshold 5
    analyzer.analyze_frame([MockTrackedObject(i, "box") for i in range(3)], frame_number=0, timestamp_seconds=0.0)
    low_stock = [e for e in analyzer.events if e["event_type"] == "inventory_low_stock"]
    assert len(low_stock) == 1
    assert low_stock[0]["current_count"] == 3
    assert low_stock[0]["threshold"] == 5
    assert "below the configured threshold" in low_stock[0]["message"]


def test_low_stock_cooldown_prevents_spam():
    analyzer = InventoryAnalyzer(
        configured_classes=["box"],
        low_stock_enabled=True,
        low_stock_thresholds={"box": 5},
        event_cooldown_seconds=10.0,
    )
    analyzer.inspect_model_classes(["box"])

    # Frame 0: 2 boxes -> triggers low stock event
    analyzer.analyze_frame([MockTrackedObject(1, "box"), MockTrackedObject(2, "box")], frame_number=0, timestamp_seconds=0.0)
    assert len([e for e in analyzer.events if e["event_type"] == "inventory_low_stock"]) == 1

    # Frames across next 9 seconds: low stock condition persists but in cooldown
    for frame_idx, t in enumerate([1.0, 3.0, 5.0, 8.0, 9.5], start=1):
        analyzer.analyze_frame([MockTrackedObject(1, "box"), MockTrackedObject(2, "box")], frame_number=frame_idx * 30, timestamp_seconds=t)
        assert len([e for e in analyzer.events if e["event_type"] == "inventory_low_stock"]) == 1

    # At t=10.5: cooldown passed -> triggers another low stock event
    analyzer.analyze_frame([MockTrackedObject(1, "box"), MockTrackedObject(2, "box")], frame_number=315, timestamp_seconds=10.5)
    assert len([e for e in analyzer.events if e["event_type"] == "inventory_low_stock"]) == 2


def test_multiple_classes_distinct_low_stock_thresholds():
    analyzer = InventoryAnalyzer(
        configured_classes=["box", "pallet"],
        low_stock_enabled=True,
        low_stock_thresholds={"box": 2, "pallet": 5},
    )
    analyzer.inspect_model_classes(["box", "pallet"])

    # Frame with 4 boxes (above box threshold 2) and 3 pallets (below pallet threshold 5)
    objects = [
        MockTrackedObject(1, "box"), MockTrackedObject(2, "box"), MockTrackedObject(3, "box"), MockTrackedObject(4, "box"),
        MockTrackedObject(5, "pallet"), MockTrackedObject(6, "pallet"), MockTrackedObject(7, "pallet"),
    ]
    analyzer.analyze_frame(objects, frame_number=0, timestamp_seconds=0.0)

    low_events = [e for e in analyzer.events if e["event_type"] == "inventory_low_stock"]
    assert len(low_events) == 1
    assert low_events[0]["class_name"] == "pallet"
    assert low_events[0]["current_count"] == 3
    assert low_events[0]["threshold"] == 5
