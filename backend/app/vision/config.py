from dataclasses import dataclass
from typing import List, Optional
from app.core.config import get_settings


@dataclass
class VisionConfig:
    """Configuration settings for YOLO inference, annotation, and tracking."""
    model_path: str = "yolo11n.pt"
    confidence_threshold: float = 0.40
    iou_threshold: float = 0.45
    device: str = "cpu"
    image_size: int = 640
    max_detections: int = 100
    target_classes: Optional[List[str]] = None  # None = all classes

    @classmethod
    def from_settings(cls) -> "VisionConfig":
        settings = get_settings()
        return cls(
            model_path=settings.YOLO_MODEL_PATH,
            confidence_threshold=settings.YOLO_CONFIDENCE_THRESHOLD,
            iou_threshold=settings.YOLO_IOU_THRESHOLD,
            device=settings.YOLO_DEVICE,
            image_size=settings.YOLO_IMAGE_SIZE,
            max_detections=settings.YOLO_MAX_DETECTIONS,
        )
