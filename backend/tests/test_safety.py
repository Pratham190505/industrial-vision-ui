"""
Unit tests for the SafetyAnalyzer engine (app/vision/safety.py).
Tests point-in-polygon zone checks, proximity detection, heuristic collision risk,
cooldown deduplication, and summary generation.
"""

from unittest.mock import MagicMock
import pytest
from app.schemas.tracking import TrackedObject, TrackingBoundingBox
from app.vision.safety import SafetyAnalyzer


def _make_obj(track_id: int, class_name: str, cx: float, cy: float, w: float = 20.0, h: float = 40.0) -> TrackedObject:
    """Helper to create a TrackedObject with specified center."""
    return TrackedObject(
        track_id=track_id,
        class_id=0 if class_name == "person" else 1,
        class_name=class_name,
        confidence=0.9,
        bounding_box=TrackingBoundingBox(
            x1=cx - w / 2,
            y1=cy - h / 2,
            x2=cx + w / 2,
            y2=cy + h / 2,
        ),
        center_x=cx,
        center_y=cy,
    )


# -----------------------------------------------------------------------------
# Restricted Zones Tests
# -----------------------------------------------------------------------------

def test_restricted_zone_inside_and_outside():
    """Verify pointPolygonTest correctly triggers inside and ignores outside."""
    zone = {
        "zone_id": "zone-loading",
        "name": "Loading Dock",
        "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
        "enabled": True,
    }
    analyzer = SafetyAnalyzer(zones=[zone], event_cooldown_seconds=1.0)

    # Person 1 inside (200, 200)
    p_inside = _make_obj(track_id=1, class_name="person", cx=200, cy=200)
    # Person 2 outside (400, 400)
    p_outside = _make_obj(track_id=2, class_name="person", cx=400, cy=400)

    events = analyzer.analyze_frame(
        tracked_objects=[p_inside, p_outside],
        frame_width=640,
        frame_height=480,
        frame_number=0,
        timestamp=0.0,
    )

    assert len(events) == 1
    ev = events[0]
    assert ev["event_type"] == "restricted_zone_violation"
    assert ev["severity"] == "high"
    assert ev["track_ids"] == [1]
    assert ev["zone_id"] == "zone-loading"
    assert "Person #1 entered restricted zone" in ev["message"]


def test_restricted_zone_exit_and_reentry():
    """Verify person exiting and re-entering zone generates a new violation event."""
    zone = {
        "zone_id": "zone-1",
        "name": "Restricted Zone 1",
        "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
        "enabled": True,
    }
    analyzer = SafetyAnalyzer(zones=[zone], event_cooldown_seconds=10.0)

    # Frame 0: Inside
    p1 = _make_obj(1, "person", 200, 200)
    ev0 = analyzer.analyze_frame([p1], 640, 480, 0, 0.0)
    assert len(ev0) == 1

    # Frame 1: Still inside within cooldown -> no duplicate event
    p1_still = _make_obj(1, "person", 205, 205)
    ev1 = analyzer.analyze_frame([p1_still], 640, 480, 1, 0.5)
    assert len(ev1) == 0

    # Frame 2: Person leaves zone (x=500, y=500)
    p1_out = _make_obj(1, "person", 500, 500)
    ev2 = analyzer.analyze_frame([p1_out], 640, 480, 2, 1.0)
    assert len(ev2) == 0

    # Frame 3: Person enters again (x=200, y=200) -> immediate new event
    p1_back = _make_obj(1, "person", 200, 200)
    ev3 = analyzer.analyze_frame([p1_back], 640, 480, 3, 1.5)
    assert len(ev3) == 1
    assert ev3[0]["event_type"] == "restricted_zone_violation"


def test_invalid_or_disabled_zone_handled_gracefully():
    """Disabled zone or malformed polygon is ignored without errors."""
    disabled_zone = {
        "zone_id": "zone-disabled",
        "name": "Disabled",
        "polygon": [[10, 10], [100, 10], [100, 100]],
        "enabled": False,
    }
    too_few_pts = {
        "zone_id": "zone-malformed",
        "name": "Malformed",
        "polygon": [[10, 10], [50, 50]],
        "enabled": True,
    }
    analyzer = SafetyAnalyzer(zones=[disabled_zone, too_few_pts])
    p1 = _make_obj(1, "person", 20, 20)

    events = analyzer.analyze_frame([p1], 640, 480, 0, 0.0)
    assert len(events) == 0


# -----------------------------------------------------------------------------
# Person-Forklift Proximity Tests
# -----------------------------------------------------------------------------

def test_proximity_warning_within_distance():
    """Person within PROXIMITY_WARNING_DISTANCE (default 100px) triggers warning."""
    analyzer = SafetyAnalyzer(proximity_warning_distance=100.0, collision_warning_distance=50.0)

    # Person at (100, 100), Forklift at (160, 100) -> distance = 60px (between 50 and 100)
    p = _make_obj(10, "person", 100.0, 100.0)
    f = _make_obj(20, "forklift", 160.0, 100.0)

    events = analyzer.analyze_frame([p, f], 640, 480, 0, 0.0)
    assert len(events) == 1
    ev = events[0]
    assert ev["event_type"] == "proximity_warning"
    assert ev["severity"] == "warning"
    assert ev["distance"] == 60.0
    assert ev["track_ids"] == [10, 20]


def test_proximity_outside_distance_ignored():
    """Person far from forklift (> 100px) triggers no events."""
    analyzer = SafetyAnalyzer(proximity_warning_distance=100.0, collision_warning_distance=50.0)

    # Person at (100, 100), Forklift at (300, 300) -> distance ~ 282px
    p = _make_obj(10, "person", 100.0, 100.0)
    f = _make_obj(20, "forklift", 300.0, 300.0)

    events = analyzer.analyze_frame([p, f], 640, 480, 0, 0.0)
    assert len(events) == 0


def test_multiple_people_and_forklifts():
    """Multiple pairs evaluated correctly."""
    analyzer = SafetyAnalyzer(proximity_warning_distance=100.0, collision_warning_distance=50.0)

    # Person 1 (100, 100) near Forklift 1 (150, 100) -> dist = 50 -> collision
    # Person 2 (500, 500) near Forklift 2 (560, 500) -> dist = 60 -> proximity
    p1 = _make_obj(1, "person", 100.0, 100.0)
    f1 = _make_obj(10, "forklift", 150.0, 100.0)
    p2 = _make_obj(2, "person", 500.0, 500.0)
    f2 = _make_obj(20, "forklift", 560.0, 500.0)

    events = analyzer.analyze_frame([p1, f1, p2, f2], 640, 480, 0, 0.0)
    assert len(events) == 2
    types = {ev["event_type"] for ev in events}
    assert "proximity_warning" in types
    assert "collision_risk" in types


# -----------------------------------------------------------------------------
# Collision Risk Heuristic Tests
# -----------------------------------------------------------------------------

def test_collision_risk_approaching_objects():
    """Objects moving toward each other within collision distance trigger high/critical risk."""
    analyzer = SafetyAnalyzer(
        proximity_warning_distance=100.0,
        collision_warning_distance=50.0,
        event_cooldown_seconds=1.0,
        velocity_window_frames=3,
    )

    # Frame 0: Person (100, 100), Forklift (145, 100) -> dist = 45px
    p0 = _make_obj(1, "person", 100.0, 100.0)
    f0 = _make_obj(2, "forklift", 145.0, 100.0)
    ev0 = analyzer.analyze_frame([p0, f0], 640, 480, 0, 0.0)
    assert len(ev0) == 1
    assert ev0[0]["event_type"] == "collision_risk"

    # Frame 1: Person moves right (110, 100), Forklift moves left (130, 100) -> dist = 20px (approaching fast)
    analyzer.reset()  # reset cooldown for test clarity
    p1 = _make_obj(1, "person", 100.0, 100.0)
    f1 = _make_obj(2, "forklift", 140.0, 100.0)
    analyzer.analyze_frame([p1, f1], 640, 480, 0, 0.0)

    p2 = _make_obj(1, "person", 108.0, 100.0)
    f2 = _make_obj(2, "forklift", 125.0, 100.0)
    analyzer._cooldown_state.clear()
    ev2 = analyzer.analyze_frame([p2, f2], 640, 480, 1, 0.1)

    assert len(ev2) == 1
    assert ev2[0]["event_type"] == "collision_risk"
    assert ev2[0]["severity"] in ("high", "critical")


def test_objects_moving_apart_reduces_severity():
    """Objects within collision distance moving away from each other receive lower severity warning."""
    analyzer = SafetyAnalyzer(proximity_warning_distance=100.0, collision_warning_distance=50.0)

    # Frame 0: Person (100, 100), Forklift (120, 100) -> dist = 20
    p0 = _make_obj(1, "person", 100.0, 100.0)
    f0 = _make_obj(2, "forklift", 120.0, 100.0)
    analyzer.analyze_frame([p0, f0], 640, 480, 0, 0.0)

    # Frame 1: Moving apart: Person (90, 100), Forklift (135, 100) -> dist = 45
    analyzer._cooldown_state.clear()
    p1 = _make_obj(1, "person", 90.0, 100.0)
    f1 = _make_obj(2, "forklift", 135.0, 100.0)
    ev1 = analyzer.analyze_frame([p1, f1], 640, 480, 1, 0.1)

    assert len(ev1) == 1
    assert ev1[0]["event_type"] == "collision_risk"
    assert ev1[0]["severity"] == "warning"


# -----------------------------------------------------------------------------
# Deduplication & Summary Tests
# -----------------------------------------------------------------------------

def test_event_deduplication_cooldown():
    """Repeated frames within cooldown period do not produce duplicate events."""
    analyzer = SafetyAnalyzer(
        proximity_warning_distance=100.0,
        event_cooldown_seconds=3.0,
    )

    p = _make_obj(1, "person", 100.0, 100.0)
    f = _make_obj(2, "forklift", 160.0, 100.0)

    # Frame 0: timestamp = 0.0 -> event generated
    ev0 = analyzer.analyze_frame([p, f], 640, 480, 0, 0.0)
    assert len(ev0) == 1

    # Frame 1: timestamp = 1.0 (within 3s cooldown) -> suppressed
    ev1 = analyzer.analyze_frame([p, f], 640, 480, 1, 1.0)
    assert len(ev1) == 0

    # Frame 2: timestamp = 2.5 (still within 3s) -> suppressed
    ev2 = analyzer.analyze_frame([p, f], 640, 480, 2, 2.5)
    assert len(ev2) == 0

    # Frame 3: timestamp = 3.5 (cooldown expired) -> event emitted
    ev3 = analyzer.analyze_frame([p, f], 640, 480, 3, 3.5)
    assert len(ev3) == 1


def test_summary_generation():
    """Verify build_summary aggregates session events accurately."""
    analyzer = SafetyAnalyzer(proximity_warning_distance=100.0, collision_warning_distance=50.0)
    p = _make_obj(1, "person", 100.0, 100.0)
    f = _make_obj(2, "forklift", 170.0, 100.0)

    analyzer.analyze_frame([p, f], 640, 480, 0, 0.0)
    summary = analyzer.build_summary()

    assert summary.enabled is True
    assert summary.total_events == 1
    assert summary.proximity_warnings == 1
    assert summary.collision_risk_events == 0
    assert summary.restricted_zone_violations == 0
    assert summary.severity_counts["medium"] >= 1


def test_disabled_safety_returns_empty():
    """When safety_enabled is False, no events or summary stats are produced."""
    analyzer = SafetyAnalyzer(safety_enabled=False)
    p = _make_obj(1, "person", 100.0, 100.0)
    f = _make_obj(2, "forklift", 120.0, 100.0)

    events = analyzer.analyze_frame([p, f], 640, 480, 0, 0.0)
    assert len(events) == 0

    summary = analyzer.build_summary()
    assert summary.enabled is False
    assert summary.total_events == 0
