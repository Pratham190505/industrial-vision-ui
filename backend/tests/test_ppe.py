"""
Tests for PPE detection and model inspection.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from app.vision.ppe import PPEDetector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_model(class_names: dict):
    """Create a mock YOLO model with the given class names."""
    model = MagicMock()
    model.names = class_names
    return model


def _make_ppe_detector(**kwargs) -> PPEDetector:
    """Create a PPEDetector with defaults for testing."""
    defaults = dict(
        model_path=None,
        confidence_threshold=0.40,
        device="cpu",
        image_size=640,
    )
    defaults.update(kwargs)
    return PPEDetector(**defaults)


# ---------------------------------------------------------------------------
# Model Inspection & Availability
# ---------------------------------------------------------------------------

class TestPPEDetectorAvailability:
    """Verify that the detector correctly inspects the model for PPE classes."""

    def test_no_model_loaded(self):
        det = _make_ppe_detector()
        assert det.is_available is False
        assert "not loaded" in det.unavailable_reason.lower() or "not configured" in det.unavailable_reason.lower()

    def test_shared_model_with_ppe_classes(self):
        model = _make_mock_model({0: "person", 1: "helmet", 2: "vest"})
        det = _make_ppe_detector()
        det.set_shared_model(model)
        assert det.is_available is True
        assert "helmet" in det.available_categories
        assert "vest" in det.available_categories

    def test_shared_model_without_ppe_classes(self):
        model = _make_mock_model({0: "person", 1: "car", 2: "dog"})
        det = _make_ppe_detector()
        det.set_shared_model(model)
        assert det.is_available is False
        assert "does not contain" in det.unavailable_reason.lower()

    def test_partial_ppe_classes(self):
        """Model has helmet but not vest."""
        model = _make_mock_model({0: "person", 1: "helmet"})
        det = _make_ppe_detector()
        det.set_shared_model(model)
        assert det.is_available is True
        assert "helmet" in det.available_categories
        assert "vest" not in det.available_categories

    def test_safety_helmet_alias(self):
        model = _make_mock_model({0: "person", 1: "safety helmet"})
        det = _make_ppe_detector()
        det.set_shared_model(model)
        assert det.is_available is True
        assert "helmet" in det.available_categories

    def test_safety_vest_alias(self):
        model = _make_mock_model({0: "person", 1: "safety vest"})
        det = _make_ppe_detector()
        det.set_shared_model(model)
        assert det.is_available is True
        assert "vest" in det.available_categories

    def test_model_class_names_property(self):
        model = _make_mock_model({0: "person", 1: "helmet", 2: "vest"})
        det = _make_ppe_detector()
        det.set_shared_model(model)
        names = det.model_class_names
        assert "helmet" in names
        assert "vest" in names
        assert "person" in names

    def test_empty_model_names(self):
        model = MagicMock()
        model.names = {}
        det = _make_ppe_detector()
        det.set_shared_model(model)
        assert det.is_available is False


# ---------------------------------------------------------------------------
# Detection Calls
# ---------------------------------------------------------------------------

class TestPPEDetection:
    """Verify structured detection output."""

    def test_detect_returns_empty_when_unavailable(self):
        det = _make_ppe_detector()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = det.detect(frame)
        assert result == []

    def test_detect_returns_ppe_detections(self):
        """Mock the model.predict path to return PPE detections."""
        det = _make_ppe_detector()
        model = _make_mock_model({0: "person", 1: "helmet", 2: "vest"})
        det.set_shared_model(model)

        # Mock predict result
        mock_result = MagicMock()
        mock_result.names = {0: "person", 1: "helmet", 2: "vest"}
        mock_boxes = MagicMock()
        mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.array([
            [10, 20, 50, 60],   # helmet
            [100, 200, 250, 400],  # vest
            [5, 5, 300, 500],   # person (should be filtered out)
        ])
        mock_boxes.conf.cpu.return_value.numpy.return_value = np.array([0.92, 0.88, 0.95])
        mock_boxes.cls.cpu.return_value.numpy.return_value = np.array([1, 2, 0])
        mock_result.boxes = mock_boxes
        model.predict.return_value = [mock_result]

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = det.detect(frame)

        assert len(detections) == 2  # Only helmet and vest, not person
        categories = {d.ppe_category for d in detections}
        assert categories == {"helmet", "vest"}

    def test_detect_skips_non_ppe_classes(self):
        det = _make_ppe_detector()
        model = _make_mock_model({0: "person", 1: "helmet", 2: "car"})
        det.set_shared_model(model)

        mock_result = MagicMock()
        mock_result.names = {0: "person", 1: "helmet", 2: "car"}
        mock_boxes = MagicMock()
        mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.array([
            [10, 20, 50, 60],  # helmet
            [100, 200, 250, 400],  # car
        ])
        mock_boxes.conf.cpu.return_value.numpy.return_value = np.array([0.90, 0.85])
        mock_boxes.cls.cpu.return_value.numpy.return_value = np.array([1, 2])
        mock_result.boxes = mock_boxes
        model.predict.return_value = [mock_result]

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = det.detect(frame)

        assert len(detections) == 1
        assert detections[0].ppe_category == "helmet"

    def test_detect_handles_empty_results(self):
        det = _make_ppe_detector()
        model = _make_mock_model({0: "helmet"})
        det.set_shared_model(model)

        mock_result = MagicMock()
        mock_result.names = {0: "helmet"}
        mock_result.boxes = None
        model.predict.return_value = [mock_result]

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        detections = det.detect(frame)
        assert detections == []

    def test_detect_invalid_bbox(self):
        """Detector should handle exception during predict gracefully."""
        det = _make_ppe_detector()
        model = _make_mock_model({0: "helmet"})
        det.set_shared_model(model)
        model.predict.side_effect = RuntimeError("mock error")

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        detections = det.detect(frame)
        assert detections == []
