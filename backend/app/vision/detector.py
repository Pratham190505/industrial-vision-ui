import logging
import time
from typing import Dict, List, Optional, Tuple
import numpy as np
from app.schemas.detection import BoundingBox
from app.vision.config import VisionConfig

logger = logging.getLogger(__name__)

# Global model cache to avoid reloading weights per image
_MODEL_CACHE: Dict[str, any] = {}


class YOLODetector:
    """
    YOLO Object Detector wrapper for WarehouseVision AI.
    Reuses model instance across requests.
    Supports real Ultralytics YOLO inference with test/fallback support.
    """

    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig.from_settings()
        self.model = None

    def load_model(self) -> None:
        """Load YOLO model weights into memory if not already cached."""
        model_key = f"{self.config.model_path}_{self.config.device}"
        if model_key in _MODEL_CACHE:
            self.model = _MODEL_CACHE[model_key]
            return

        try:
            from ultralytics import YOLO
            logger.info("Loading YOLO model from %s on %s...", self.config.model_path, self.config.device)
            loaded_model = YOLO(self.config.model_path)
            _MODEL_CACHE[model_key] = loaded_model
            self.model = loaded_model
            logger.info("YOLO model loaded successfully.")
        except ImportError:
            logger.warning("Ultralytics package is not installed. Running in mock/fallback mode.")
            self.model = None
        except Exception as exc:
            logger.warning("Could not load YOLO model (%s): %s. Fallback mode enabled.", self.config.model_path, exc)
            self.model = None

    def detect(self, image: np.ndarray) -> Tuple[List[BoundingBox], Dict[str, int], float]:
        """
        Run object detection on an image (BGR format).
        Returns:
            (boxes, counts_by_class, inference_time_ms)
        """
        if self.model is None:
            self.load_model()

        start_time = time.perf_counter()

        if self.model is None:
            # Fallback when model is not available (e.g. mock test environments)
            inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return [], {}, inference_time_ms

        try:
            # Run inference
            results = self.model.predict(
                source=image,
                conf=self.config.confidence_threshold,
                iou=self.config.iou_threshold,
                device=self.config.device,
                imgsz=self.config.image_size,
                max_det=self.config.max_detections,
                verbose=False,
            )

            boxes: List[BoundingBox] = []
            counts_by_class: Dict[str, int] = {}

            if results and len(results) > 0:
                result = results[0]
                names = result.names if hasattr(result, "names") else {}

                if hasattr(result, "boxes") and result.boxes is not None:
                    xyxy_arr = result.boxes.xyxy.cpu().numpy()
                    conf_arr = result.boxes.conf.cpu().numpy()
                    cls_arr = result.boxes.cls.cpu().numpy()

                    for i in range(len(xyxy_arr)):
                        coords = xyxy_arr[i]
                        conf = float(conf_arr[i])
                        class_id = int(cls_arr[i])
                        class_name = names.get(class_id, f"class_{class_id}")

                        # If target_classes specified, filter accordingly
                        if self.config.target_classes and class_name not in self.config.target_classes:
                            continue

                        box = BoundingBox(
                            x_min=float(coords[0]),
                            y_min=float(coords[1]),
                            x_max=float(coords[2]),
                            y_max=float(coords[3]),
                            confidence=round(conf, 4),
                            class_id=class_id,
                            class_name=class_name,
                        )
                        boxes.append(box)
                        counts_by_class[class_name] = counts_by_class.get(class_name, 0) + 1

            inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return boxes, counts_by_class, inference_time_ms

        except Exception as exc:
            logger.error("Error during YOLO inference: %s", exc)
            inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return [], {}, inference_time_ms
