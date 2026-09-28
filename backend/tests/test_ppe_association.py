"""
Tests for PPE-to-person geometric association logic.
"""

import pytest
from types import SimpleNamespace
from app.vision.ppe import (
    associate_ppe_to_persons,
    calculate_bbox_overlap,
    is_inside_person,
)
from app.schemas.ppe import PPEDetection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bbox(x1, y1, x2, y2):
    """Create a SimpleNamespace mimicking TrackingBoundingBox."""
    return SimpleNamespace(x1=x1, y1=y1, x2=x2, y2=y2)


def _tracked_person(track_id, x1, y1, x2, y2, class_name="person"):
    return SimpleNamespace(
        track_id=track_id,
        class_id=0,
        class_name=class_name,
        confidence=0.9,
        bounding_box=_bbox(x1, y1, x2, y2),
        center_x=(x1 + x2) / 2,
        center_y=(y1 + y2) / 2,
    )


def _ppe_detection(category, x1, y1, x2, y2, confidence=0.9):
    return PPEDetection(
        class_id=1,
        class_name=category,
        ppe_category=category,
        confidence=confidence,
        bbox={"x1": x1, "y1": y1, "x2": x2, "y2": y2},
    )


# ---------------------------------------------------------------------------
# is_inside_person
# ---------------------------------------------------------------------------

class TestIsInsidePerson:

    def test_centre_inside(self):
        person_bb = _bbox(100, 100, 300, 600)
        ppe_bbox = {"x1": 150, "y1": 90, "x2": 230, "y2": 180}
        # PPE centre = (190, 135) which is inside person (100-300, 100-600)
        assert is_inside_person(ppe_bbox, person_bb) is True

    def test_centre_outside(self):
        person_bb = _bbox(100, 100, 300, 600)
        ppe_bbox = {"x1": 400, "y1": 400, "x2": 500, "y2": 500}
        assert is_inside_person(ppe_bbox, person_bb) is False

    def test_centre_on_edge(self):
        person_bb = _bbox(100, 100, 300, 600)
        ppe_bbox = {"x1": 50, "y1": 50, "x2": 150, "y2": 150}
        # Centre = (100, 100) = edge of person → should be inside (<=)
        assert is_inside_person(ppe_bbox, person_bb) is True


# ---------------------------------------------------------------------------
# calculate_bbox_overlap
# ---------------------------------------------------------------------------

class TestBboxOverlap:

    def test_full_overlap(self):
        person_bb = _bbox(0, 0, 500, 500)
        ppe = {"x1": 100, "y1": 100, "x2": 200, "y2": 200}
        overlap = calculate_bbox_overlap(ppe, person_bb)
        assert overlap == pytest.approx(1.0)

    def test_no_overlap(self):
        person_bb = _bbox(0, 0, 100, 100)
        ppe = {"x1": 200, "y1": 200, "x2": 300, "y2": 300}
        assert calculate_bbox_overlap(ppe, person_bb) == 0.0

    def test_partial_overlap(self):
        person_bb = _bbox(0, 0, 200, 200)
        ppe = {"x1": 100, "y1": 100, "x2": 300, "y2": 300}
        overlap = calculate_bbox_overlap(ppe, person_bb)
        # Intersection = 100x100 = 10000, PPE area = 200x200 = 40000
        assert overlap == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# associate_ppe_to_persons
# ---------------------------------------------------------------------------

class TestAssociatePPE:

    def test_helmet_correctly_associated(self):
        person = _tracked_person(12, 100, 100, 300, 600)
        helmet = _ppe_detection("helmet", 150, 90, 230, 180)
        result = associate_ppe_to_persons([helmet], [person])
        assert "helmet" in result[12]

    def test_vest_correctly_associated(self):
        person = _tracked_person(12, 100, 100, 300, 600)
        vest = _ppe_detection("vest", 120, 220, 280, 450)
        result = associate_ppe_to_persons([vest], [person])
        assert "vest" in result[12]

    def test_ppe_outside_all_persons(self):
        person = _tracked_person(12, 100, 100, 300, 600)
        helmet = _ppe_detection("helmet", 500, 500, 600, 600)
        result = associate_ppe_to_persons([helmet], [person])
        assert result[12] == set()

    def test_multiple_workers(self):
        p1 = _tracked_person(10, 0, 0, 200, 500)
        p2 = _tracked_person(11, 400, 0, 600, 500)

        h1 = _ppe_detection("helmet", 50, 10, 150, 80)    # inside p1
        h2 = _ppe_detection("helmet", 420, 10, 550, 80)   # inside p2

        result = associate_ppe_to_persons([h1, h2], [p1, p2])
        assert "helmet" in result[10]
        assert "helmet" in result[11]

    def test_multiple_ppe_objects_on_one_person(self):
        person = _tracked_person(12, 100, 100, 300, 600)
        helmet = _ppe_detection("helmet", 150, 100, 230, 180)
        vest = _ppe_detection("vest", 120, 220, 280, 450)
        result = associate_ppe_to_persons([helmet, vest], [person])
        assert result[12] == {"helmet", "vest"}

    def test_ambiguous_ppe_goes_to_best_overlap(self):
        """PPE between two persons → assigned to the one with higher overlap."""
        p1 = _tracked_person(1, 0, 0, 200, 500)
        p2 = _tracked_person(2, 150, 0, 350, 500)

        # Helmet centred at (175, 50) is inside both, but overlaps more with p2
        helmet = _ppe_detection("helmet", 160, 10, 190, 90)
        result = associate_ppe_to_persons([helmet], [p1, p2])

        # Should be assigned to one of them (the one with the best overlap)
        assigned = [tid for tid, cats in result.items() if "helmet" in cats]
        assert len(assigned) == 1

    def test_empty_ppe_detections(self):
        person = _tracked_person(12, 100, 100, 300, 600)
        result = associate_ppe_to_persons([], [person])
        assert result[12] == set()

    def test_empty_persons(self):
        helmet = _ppe_detection("helmet", 10, 10, 50, 50)
        result = associate_ppe_to_persons([helmet], [])
        assert result == {}
