from unittest.mock import MagicMock
import cv2
import numpy as np
import pytest
from app.core.exceptions import FileValidationError
from app.schemas.detection import BoundingBox
from app.vision.video_pipeline import VideoPipeline


def test_pipeline_with_mock_detections(tmp_path, sample_video_path):
    mock_detector = MagicMock()
    mock_detector.detect.return_value = (
        [
            BoundingBox(
                x_min=10.0,
                y_min=10.0,
                x_max=50.0,
                y_max=50.0,
                confidence=0.88,
                class_id=0,
                class_name="person",
            )
        ],
        {"person": 1},
        12.5,
    )

    output_path = tmp_path / "annotated_output.mp4"
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=1)

    progress_records = []

    def on_progress(processed, total, detections):
        progress_records.append((processed, total, detections))

    stats = pipeline.process_video(
        input_path=str(sample_video_path),
        output_path=str(output_path),
        job_id="test_job_1",
        progress_callback=on_progress,
    )

    assert stats["processed_frames"] == 5
    assert stats["detection_count"] == 5
    assert output_path.exists()
    assert len(progress_records) == 5

    # Verify output video is readable with OpenCV
    cap = cv2.VideoCapture(str(output_path))
    assert cap.isOpened()
    ret, frame = cap.read()
    assert ret is True
    assert frame.shape[:2] == (120, 160)
    cap.release()


def test_pipeline_zero_detections(tmp_path, sample_video_path):
    mock_detector = MagicMock()
    mock_detector.detect.return_value = ([], {}, 5.0)

    output_path = tmp_path / "zero_detections.mp4"
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=1)

    stats = pipeline.process_video(
        input_path=str(sample_video_path),
        output_path=str(output_path),
        job_id="test_job_zero",
    )

    assert stats["processed_frames"] == 5
    assert stats["detection_count"] == 0
    assert output_path.exists()


def test_pipeline_frame_sampling(tmp_path, sample_video_path):
    mock_detector = MagicMock()
    mock_detector.detect.return_value = (
        [
            BoundingBox(
                x_min=5.0,
                y_min=5.0,
                x_max=30.0,
                y_max=30.0,
                confidence=0.92,
                class_id=1,
                class_name="forklift",
            )
        ],
        {"forklift": 1},
        8.0,
    )

    output_path = tmp_path / "sampled_output.mp4"
    # Process every 2nd frame (frames 0, 2, 4 -> 3 calls to detect)
    pipeline = VideoPipeline(detector=mock_detector, frame_interval=2)

    stats = pipeline.process_video(
        input_path=str(sample_video_path),
        output_path=str(output_path),
        job_id="test_job_sampled",
    )

    assert stats["processed_frames"] == 5
    assert mock_detector.detect.call_count == 3
    assert output_path.exists()


def test_pipeline_missing_file(tmp_path):
    pipeline = VideoPipeline()
    with pytest.raises(FileValidationError):
        pipeline.process_video(
            input_path=str(tmp_path / "non_existent.mp4"),
            output_path=str(tmp_path / "out.mp4"),
            job_id="test_missing",
        )
