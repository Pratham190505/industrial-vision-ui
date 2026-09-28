"""
Unit tests for app.services.tracking_service — statistics collection and
configuration helpers.
"""

import pytest

from app.schemas.tracking import (
    TrackFrameResult,
    TrackedObject,
    TrackingBoundingBox,
)
from app.services.tracking_service import (
    TrackingStatisticsCollector,
    get_tracker_config_name,
)


# ---------------------------------------------------------------------------
# Helper — build TrackedObject
# ---------------------------------------------------------------------------

def _obj(track_id, class_name="person", class_id=0, conf=0.9, bbox=(10, 10, 50, 50)):
    x1, y1, x2, y2 = bbox
    return TrackedObject(
        track_id=track_id,
        class_id=class_id,
        class_name=class_name,
        confidence=conf,
        bounding_box=TrackingBoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
        center_x=round((x1 + x2) / 2.0, 2),
        center_y=round((y1 + y2) / 2.0, 2),
    )


# ---------------------------------------------------------------------------
# Tests — TrackingStatisticsCollector
# ---------------------------------------------------------------------------

class TestStatisticsCollector:

    def test_empty_video(self):
        c = TrackingStatisticsCollector()
        summary = c.build_summary()
        assert summary.unique_track_count == 0
        assert summary.max_active_tracks == 0
        assert summary.tracked_detections == 0
        assert summary.frames_with_tracks == 0
        assert summary.average_objects_per_frame == 0.0
        assert summary.tracks_by_class == {}

    def test_single_frame_single_object(self):
        c = TrackingStatisticsCollector()
        c.update(TrackFrameResult(
            frame_index=0,
            tracked_objects=[_obj(1)],
            object_count=1,
        ))
        summary = c.build_summary()
        assert summary.unique_track_count == 1
        assert summary.max_active_tracks == 1
        assert summary.tracked_detections == 1
        assert summary.frames_with_tracks == 1
        assert summary.average_objects_per_frame == 1.0
        assert summary.tracks_by_class == {"person": 1}

    def test_multiple_frames_same_objects(self):
        c = TrackingStatisticsCollector()
        for i in range(5):
            c.update(TrackFrameResult(
                frame_index=i,
                tracked_objects=[_obj(1), _obj(2), _obj(3, "forklift", 1)],
                object_count=3,
            ))
        summary = c.build_summary()
        assert summary.unique_track_count == 3
        assert summary.max_active_tracks == 3
        assert summary.tracked_detections == 15
        assert summary.frames_with_tracks == 5
        assert summary.average_objects_per_frame == 3.0
        assert summary.tracks_by_class == {"person": 2, "forklift": 1}

    def test_max_active_tracks(self):
        c = TrackingStatisticsCollector()
        # Frame 0: 2 objects
        c.update(TrackFrameResult(
            frame_index=0,
            tracked_objects=[_obj(1), _obj(2)],
            object_count=2,
        ))
        # Frame 1: 5 objects (max)
        c.update(TrackFrameResult(
            frame_index=1,
            tracked_objects=[_obj(1), _obj(2), _obj(3), _obj(4), _obj(5)],
            object_count=5,
        ))
        # Frame 2: 1 object
        c.update(TrackFrameResult(
            frame_index=2,
            tracked_objects=[_obj(1)],
            object_count=1,
        ))
        summary = c.build_summary()
        assert summary.max_active_tracks == 5

    def test_empty_frames_counted(self):
        c = TrackingStatisticsCollector()
        # 3 empty frames, 2 with objects
        c.update(TrackFrameResult(frame_index=0, tracked_objects=[], object_count=0))
        c.update(TrackFrameResult(frame_index=1, tracked_objects=[_obj(1)], object_count=1))
        c.update(TrackFrameResult(frame_index=2, tracked_objects=[], object_count=0))
        c.update(TrackFrameResult(frame_index=3, tracked_objects=[_obj(1)], object_count=1))
        c.update(TrackFrameResult(frame_index=4, tracked_objects=[], object_count=0))

        summary = c.build_summary()
        assert summary.frames_with_tracks == 2
        assert summary.average_objects_per_frame == 0.4  # 2 / 5

    def test_tracks_by_class_dynamic(self):
        """Class names come from the model, not hard-coded."""
        c = TrackingStatisticsCollector()
        c.update(TrackFrameResult(
            frame_index=0,
            tracked_objects=[
                _obj(1, "chair", 56),
                _obj(2, "laptop", 63),
                _obj(3, "chair", 56),
            ],
            object_count=3,
        ))
        summary = c.build_summary()
        assert summary.tracks_by_class == {"chair": 2, "laptop": 1}

    def test_reset_clears_state(self):
        c = TrackingStatisticsCollector()
        c.update(TrackFrameResult(
            frame_index=0,
            tracked_objects=[_obj(1), _obj(2)],
            object_count=2,
        ))
        c.reset()
        summary = c.build_summary()
        assert summary.unique_track_count == 0
        assert summary.tracked_detections == 0

    def test_tracker_type_in_summary(self):
        c = TrackingStatisticsCollector(tracker_type="botsort")
        summary = c.build_summary()
        assert summary.tracker_type == "botsort"

    def test_summary_enabled_flag(self):
        c = TrackingStatisticsCollector()
        summary = c.build_summary()
        assert summary.enabled is True


# ---------------------------------------------------------------------------
# Tests — get_tracker_config_name
# ---------------------------------------------------------------------------

class TestTrackerConfigName:

    def test_bytetrack(self):
        assert get_tracker_config_name("bytetrack") == "bytetrack.yaml"

    def test_botsort(self):
        assert get_tracker_config_name("botsort") == "botsort.yaml"

    def test_case_insensitive(self):
        assert get_tracker_config_name("ByteTrack") == "bytetrack.yaml"
        assert get_tracker_config_name("BOTSORT") == "botsort.yaml"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown tracker type"):
            get_tracker_config_name("deepsort")

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError):
            get_tracker_config_name("../../etc/passwd")
