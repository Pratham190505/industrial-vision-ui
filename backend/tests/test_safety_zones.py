"""
Tests for Safety Zone schema validation and geometry handling (tests/test_safety_zones.py).
"""

import pytest
from pydantic import ValidationError

from app.schemas.safety import SafetyZoneCreate, SafetyZoneUpdate
from app.vision.safety import SafetyAnalyzer
from app.schemas.tracking import TrackedObject, TrackingBoundingBox


def _make_person(cx: float, cy: float) -> TrackedObject:
    return TrackedObject(
        track_id=1,
        class_id=0,
        class_name="person",
        confidence=0.95,
        bounding_box=TrackingBoundingBox(x1=cx - 10, y1=cy - 20, x2=cx + 10, y2=cy + 20),
        center_x=cx,
        center_y=cy,
    )


# -----------------------------------------------------------------------------
# Schema Validation Tests
# -----------------------------------------------------------------------------

def test_safety_zone_create_valid():
    """Valid zone definition passes schema validation."""
    data = {
        "name": "Loading Bay A",
        "zone_type": "restricted",
        "polygon": [[50.0, 50.0], [250.0, 50.0], [250.0, 200.0], [50.0, 200.0]],
        "enabled": True,
    }
    zone = SafetyZoneCreate(**data)
    assert zone.name == "Loading Bay A"
    assert zone.zone_type == "restricted"
    assert len(zone.polygon) == 4
    assert zone.enabled is True


def test_safety_zone_create_rejects_empty_name():
    """Empty or whitespace-only name raises validation error."""
    with pytest.raises(ValidationError):
        SafetyZoneCreate(
            name="   ",
            zone_type="restricted",
            polygon=[[0, 0], [10, 0], [10, 10]],
        )


def test_safety_zone_create_rejects_less_than_three_points():
    """Polygon with fewer than 3 vertices raises validation error."""
    with pytest.raises(ValidationError):
        SafetyZoneCreate(
            name="Invalid Zone",
            zone_type="restricted",
            polygon=[[10.0, 10.0], [20.0, 20.0]],
        )


def test_safety_zone_create_rejects_negative_coordinates():
    """Negative coordinates raise validation error."""
    with pytest.raises(ValidationError):
        SafetyZoneCreate(
            name="Negative Vertex Zone",
            zone_type="restricted",
            polygon=[[-10.0, 10.0], [20.0, 20.0], [20.0, 50.0]],
        )


def test_safety_zone_create_rejects_non_numeric_coordinates():
    """Non-numeric coordinate strings raise validation error."""
    with pytest.raises(ValidationError):
        SafetyZoneCreate(
            name="Non-numeric Zone",
            zone_type="restricted",
            polygon=[["abc", 10.0], [20.0, 20.0], [20.0, 50.0]],
        )


def test_safety_zone_create_rejects_unsupported_type():
    """Non-'restricted' zone_type raises validation error."""
    with pytest.raises(ValidationError):
        SafetyZoneCreate(
            name="Hazard Zone",
            zone_type="ppe_mandatory",  # Not supported yet in Prompt 7
            polygon=[[0, 0], [10, 0], [10, 10]],
        )


def test_safety_zone_update_validations():
    """SafetyZoneUpdate validates partial updates correctly."""
    up = SafetyZoneUpdate(name="Renamed Zone", enabled=False)
    assert up.name == "Renamed Zone"
    assert up.enabled is False

    with pytest.raises(ValidationError):
        SafetyZoneUpdate(polygon=[[0, 0], [1, 1]])  # < 3 points


# -----------------------------------------------------------------------------
# Complex Polygon Geometric Tests
# -----------------------------------------------------------------------------

def test_triangle_and_irregular_polygon_containment():
    """Verify points inside and outside non-rectangular polygons."""
    # Triangular zone with vertices at (100, 100), (300, 100), (200, 300)
    triangle_zone = {
        "zone_id": "triangle-1",
        "name": "Triangle Zone",
        "polygon": [[100, 100], [300, 100], [200, 300]],
        "enabled": True,
    }
    analyzer = SafetyAnalyzer(zones=[triangle_zone])

    # Centroid of triangle is around (200, 166.7) -> inside
    p_inside = _make_person(200.0, 160.0)
    ev_in = analyzer.analyze_frame([p_inside], 640, 480, 0, 0.0)
    assert len(ev_in) == 1
    assert ev_in[0]["zone_id"] == "triangle-1"

    # Point outside triangle at (100, 250) -> outside
    analyzer.reset()
    p_outside = _make_person(100.0, 250.0)
    ev_out = analyzer.analyze_frame([p_outside], 640, 480, 0, 0.0)
    assert len(ev_out) == 0
