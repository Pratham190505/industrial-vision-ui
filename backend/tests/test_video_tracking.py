"""
Integration tests for the VideoPipeline with Object Tracking enabled.
Verifies end-to-end video tracking behavior, tracking statistics accumulation,
annotated video output with track IDs, and fallback mechanisms.
"""

from unittest.mock import MagicMock, patch
import cv2
import numpy as np
import pytest

from app.schemas.tracking import TrackingSummary
from app.vision.video_pipeline import VideoPipeline


def _create_mock_boxes(box_data):
    """
    Helper to construct a mock ultralytics Boxes object.
    box_data: list of (x1, y1, x2, y2, track_id, conf, class_id)
    """
    mock_boxes = MagicMock()
    if not box_data:
        mock_boxes.__len__.return_value = 0
        mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.empty((0, 4))
        mock_boxes.conf.cpu.return_value.numpy.return_value = np.empty((0,))
        mock_boxes.cls.cpu.return_value.numpy.return_value = np.empty((0,))
        mock_boxes.id = None
        return mock_boxes

    xyxy = np.array([[b[0], b[1], b[2], b[3]] for b in box_data], dtype=float)
    ids = np.array([b[4] for b in box_data], dtype=int)
    confs = np.array([b[5] for b in box_data], dtype=float)
    clss = np.array([b[6] for b in box_data], dtype=int)

    mock_boxes.__len__.return_value = len(box_data)
    mock_boxes.xyxy.cpu.return_value.numpy.return_value = xyxy
    mock_boxes.conf.cpu.return_value.numpy.return_value = confs
    mock_boxes.cls.cpu.return_value.numpy.return_value = clss

    mock_id_tensor = MagicMock()
    mock_id_tensor.cpu.return_value.numpy.return_value.astype.return_value.flatten.return_value = ids
    mock_boxes.id = mock_id_tensor
    return mock_boxes


def _create_mock_result(box_data, names=None):
    """Create a mock ultralytics Results object."""
    mock_res = MagicMock()
    mock_res.boxes = _create_mock_boxes(box_data)
    mock_res.names = names or {0: "person", 1: "forklift"}
    return mock_res


def test_video_pipeline_tracking_enabled_produces_summary(tmp_path, sample_video_path):
    """
    Verify that VideoPipeline with tracking enabled:
    - Runs model.track() across frames
    - Emits a tracking summary in the returned dictionary
    - Records persistent track IDs and correct statistics
    """
    # 5 frames in sample video:
    # Frame 0: person #1, forklift #2
    # Frame 1: person #1, forklift #2
    # Frame 2: person #1, forklift #2, person #3
    # Frame 3: person #1, person #3
    # Frame 4: forklift #2
    results_per_frame = [
        _create_mock_result([(10, 10, 50, 50, 1, 0.90, 0), (60, 60, 120, 100, 2, 0.85, 1)]),
        _create_mock_result([(12, 10, 52, 50, 1, 0.91, 0), (62, 60, 122, 100, 2, 0.86, 1)]),
        _create_mock_result([(14, 10, 54, 50, 1, 0.89, 0), (64, 60, 124, 100, 2, 0.84, 1), (5, 5, 25, 25, 3, 0.75, 0)]),
        _create_mock_result([(15, 10, 55, 50, 1, 0.92, 0), (6, 5, 26, 25, 3, 0.78, 0)]),
        _create_mock_result([(65, 60, 125, 100, 2, 0.88, 1)]),
    ]

    mock_model = MagicMock()
    mock_model.track.side_effect = [[res] for res in results_per_frame]

    mock_detector = MagicMock()
    mock_detector.model = mock_model

    output_path = tmp_path / "tracked_output.mp4"
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=1, tracking_enabled=True)

    progress_log = []
    def on_progress(processed, total, detections):
        progress_log.append((processed, total, detections))

    stats = pipeline.process_video(
        input_path=str(sample_video_path),
        output_path=str(output_path),
        job_id="test_tracking_job_1",
        progress_callback=on_progress,
    )

    assert stats["processed_frames"] == 5
    assert stats["detection_count"] == 10  # 2 + 2 + 3 + 2 + 1 = 10
    assert output_path.exists()
    assert len(progress_log) == 5

    # Check tracking summary structure
    assert "tracking" in stats
    tracking = stats["tracking"]
    assert tracking["enabled"] is True
    assert tracking["tracker_type"] == "bytetrack"
    assert tracking["unique_track_count"] == 3  # tracks 1, 2, 3
    assert tracking["max_active_tracks"] == 3  # frame 2 had 3 tracks
    assert tracking["tracked_detections"] == 10
    assert tracking["tracks_by_class"] == {"person": 2, "forklift": 1}
    assert tracking["frames_with_tracks"] == 5
    assert tracking["average_objects_per_frame"] == 2.0

    # Output video verification
    cap = cv2.VideoCapture(str(output_path))
    assert cap.isOpened()
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 5
    ret, frame = cap.read()
    assert ret is True
    assert frame.shape[:2] == (120, 160)
    cap.release()


def test_tracker_initialized_once_per_video_with_persist(tmp_path, sample_video_path):
    """Ensure ObjectTracker is created once and model.track() is called with persist=True."""
    mock_res = _create_mock_result([(10, 10, 50, 50, 1, 0.90, 0)])
    mock_model = MagicMock()
    mock_model.track.return_value = [mock_res]

    mock_detector = MagicMock()
    mock_detector.model = mock_model

    output_path = tmp_path / "tracked_once.mp4"
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=1, tracking_enabled=True)

    with patch.object(pipeline, "_create_tracker", wraps=pipeline._create_tracker) as mock_create:
        pipeline.process_video(
            input_path=str(sample_video_path),
            output_path=str(output_path),
            job_id="test_init_once",
        )
        assert mock_create.call_count == 1

    # model.track should be called for each of the 5 frames with persist=True
    assert mock_model.track.call_count == 5
    for call in mock_model.track.call_args_list:
        assert call.kwargs.get("persist") is True
        assert call.kwargs.get("tracker") == "bytetrack.yaml"


def test_tracking_disabled_explicitly(tmp_path, sample_video_path):
    """When tracking_enabled=False, pipeline falls back to detection-only."""
    mock_detector = MagicMock()
    mock_detector.detect.return_value = ([], {}, 5.0)

    output_path = tmp_path / "untracked.mp4"
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=1, tracking_enabled=False)

    stats = pipeline.process_video(
        input_path=str(sample_video_path),
        output_path=str(output_path),
        job_id="test_untracked",
    )

    assert stats["processed_frames"] == 5
    assert stats["tracking"]["enabled"] is False
    assert stats["tracking"]["tracker_type"] == "none"
    assert mock_detector.detect.call_count == 5


def test_fallback_when_tracker_creation_fails(tmp_path, sample_video_path):
    """If tracker creation raises an error, pipeline falls back to detection-only."""
    mock_detector = MagicMock()
    mock_detector.detect.return_value = ([], {}, 5.0)

    output_path = tmp_path / "fallback.mp4"
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=1, tracking_enabled=True)

    with patch.object(pipeline, "_create_tracker", return_value=None):
        stats = pipeline.process_video(
            input_path=str(sample_video_path),
            output_path=str(output_path),
            job_id="test_fallback",
        )

        assert stats["processed_frames"] == 5
        assert stats["tracking"]["enabled"] is False
        assert mock_detector.detect.call_count == 5
        assert output_path.exists()


def test_empty_detections_in_tracking(tmp_path, sample_video_path):
    """Verify tracking pipeline handles frames with zero detected objects."""
    empty_res = _create_mock_result([])
    mock_model = MagicMock()
    mock_model.track.return_value = [empty_res]

    mock_detector = MagicMock()
    mock_detector.model = mock_model

    output_path = tmp_path / "empty_tracked.mp4"
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=1, tracking_enabled=True)

    stats = pipeline.process_video(
        input_path=str(sample_video_path),
        output_path=str(output_path),
        job_id="test_empty_tracking",
    )

    assert stats["processed_frames"] == 5
    assert stats["detection_count"] == 0
    assert stats["tracking"]["enabled"] is True
    assert stats["tracking"]["unique_track_count"] == 0
    assert stats["tracking"]["max_active_tracks"] == 0
    assert stats["tracking"]["tracked_detections"] == 0
    assert stats["tracking"]["frames_with_tracks"] == 0
    assert stats["tracking"]["average_objects_per_frame"] == 0.0


def test_video_pipeline_with_safety_analysis(tmp_path, sample_video_path):
    """Verify VideoPipeline runs SafetyAnalyzer, draws safety annotations, and produces safety summary."""
    zone = {
        "zone_id": "zone_danger",
        "name": "Heavy Machinery",
        "polygon": [[5, 5], [60, 5], [60, 60], [5, 60]],
        "enabled": True,
    }
    # Person 1 at (20, 20) inside zone_danger
    # Forklift 2 at (70, 20) -> distance = 50px (at collision threshold)
    mock_res = _create_mock_result([(10, 10, 30, 30, 1, 0.90, 0), (60, 10, 80, 30, 2, 0.85, 1)])
    mock_model = MagicMock()
    mock_model.track.return_value = [mock_res]

    mock_detector = MagicMock()
    mock_detector.model = mock_model

    output_path = tmp_path / "safety_tracked.mp4"
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=1, tracking_enabled=True, safety_zones=[zone])

    stats = pipeline.process_video(
        input_path=str(sample_video_path),
        output_path=str(output_path),
        job_id="test_safety_pipeline_job",
    )

    assert stats["processed_frames"] == 5
    assert output_path.exists()
    assert "safety" in stats
    safety = stats["safety"]
    assert safety["enabled"] is True
    assert safety["total_events"] >= 1
    assert safety["restricted_zone_violations"] >= 1
    assert len(stats["safety_events"]) >= 1


def test_video_pipeline_with_inventory_analysis(tmp_path, sample_video_path):
    """Verify VideoPipeline runs InventoryAnalyzer on tracked objects and returns inventory summary & snapshots."""
    names = {0: "person", 1: "forklift", 2: "box"}
    mock_res = _create_mock_result([(10, 10, 30, 30, 101, 0.90, 2)], names=names)
    mock_model = MagicMock()
    mock_model.track.return_value = [mock_res]
    mock_model.names = names

    mock_detector = MagicMock()
    mock_detector.model = mock_model

    output_path = tmp_path / "inventory_tracked.mp4"
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=1, tracking_enabled=True)

    stats = pipeline.process_video(
        input_path=str(sample_video_path),
        output_path=str(output_path),
        job_id="test_inventory_pipeline_job",
    )

    assert stats["processed_frames"] == 5
    assert output_path.exists()
    assert "inventory" in stats
    inv = stats["inventory"]
    assert inv["enabled"] is True
    assert "box" in inv["available_classes"]
    assert inv["counts"]["box"]["unique_track_count"] == 1
    assert "inventory_snapshots" in stats
    assert len(stats["inventory_snapshots"]) >= 1
