import os
from pathlib import Path
import pytest
import cv2
import numpy as np
from app.core.exceptions import FileValidationError
from app.schemas.detection import BoundingBox
from app.vision.detector import YOLODetector
from app.vision.image_pipeline import ImagePipeline


class MockDetector(YOLODetector):
    """Test detector returning predefined mock detections."""

    def __init__(self, mock_boxes=None):
        super().__init__()
        self.mock_boxes = mock_boxes or []

    def detect(self, image: np.ndarray):
        counts = {}
        for box in self.mock_boxes:
            counts[box.class_name] = counts.get(box.class_name, 0) + 1
        return self.mock_boxes, counts, 12.5


def test_pipeline_with_mock_detections(tmp_path):
    # Create test image
    input_file = tmp_path / "test_input.jpg"
    output_file = tmp_path / "test_output.jpg"

    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.imwrite(str(input_file), dummy_img)

    mock_boxes = [
        BoundingBox(
            x_min=50.0,
            y_min=60.0,
            x_max=200.0,
            y_max=300.0,
            confidence=0.88,
            class_id=0,
            class_name="person",
        ),
        BoundingBox(
            x_min=250.0,
            y_min=100.0,
            x_max=400.0,
            y_max=350.0,
            confidence=0.92,
            class_id=1,
            class_name="forklift",
        ),
    ]

    pipeline = ImagePipeline(detector=MockDetector(mock_boxes))
    width, height, count, boxes, counts_by_class, inf_time = pipeline.process_image(
        image_path=str(input_file),
        annotated_output_path=str(output_file),
    )

    assert width == 640
    assert height == 480
    assert count == 2
    assert len(boxes) == 2
    assert counts_by_class["person"] == 1
    assert counts_by_class["forklift"] == 1
    assert inf_time == 12.5
    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_pipeline_zero_detections(tmp_path):
    input_file = tmp_path / "zero_det.jpg"
    output_file = tmp_path / "zero_det_annotated.jpg"

    dummy_img = np.ones((300, 400, 3), dtype=np.uint8) * 200
    cv2.imwrite(str(input_file), dummy_img)

    pipeline = ImagePipeline(detector=MockDetector(mock_boxes=[]))
    width, height, count, boxes, counts_by_class, inf_time = pipeline.process_image(
        image_path=str(input_file),
        annotated_output_path=str(output_file),
    )

    assert count == 0
    assert len(boxes) == 0
    assert counts_by_class == {}
    assert output_file.exists()


def test_pipeline_boundary_clamping(tmp_path):
    input_file = tmp_path / "clamping.jpg"
    output_file = tmp_path / "clamping_annotated.jpg"

    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(input_file), dummy_img)

    # Box coordinates exceeding image bounds
    out_of_bounds_box = [
        BoundingBox(
            x_min=-50.0,
            y_min=-30.0,
            x_max=250.0,
            y_max=300.0,
            confidence=0.75,
            class_id=0,
            class_name="pallet",
        )
    ]

    pipeline = ImagePipeline(detector=MockDetector(out_of_bounds_box))
    width, height, count, boxes, counts_by_class, _ = pipeline.process_image(
        image_path=str(input_file),
        annotated_output_path=str(output_file),
    )
    assert count == 1
    assert output_file.exists()


def test_pipeline_missing_file():
    pipeline = ImagePipeline()
    with pytest.raises(FileValidationError):
        pipeline.process_image("non_existent_image_path.jpg", "output.jpg")
