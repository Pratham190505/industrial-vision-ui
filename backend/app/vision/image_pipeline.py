import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from app.core.exceptions import FileValidationError
from app.schemas.detection import BoundingBox
from app.vision.detector import YOLODetector

logger = logging.getLogger(__name__)

# Class color palette for visual clarity and high contrast
PALETTE = [
    (245, 158, 11),  # Amber (Warehouse theme)
    (34, 197, 94),   # Green
    (239, 68, 68),   # Red
    (59, 130, 246),  # Blue
    (168, 85, 247),  # Purple
    (236, 72, 153),  # Pink
    (20, 184, 166),  # Teal
]


class ImagePipeline:
    """
    Complete image-processing pipeline:
    1. Loads image with OpenCV
    2. Runs YOLO object detection
    3. Annotates bounding boxes and labels with boundary clamping
    4. Saves annotated image to processed storage
    5. Returns structured detection data
    """

    def __init__(self, detector: Optional[YOLODetector] = None):
        self.detector = detector or YOLODetector()

    def process_image(
        self,
        image_path: str,
        annotated_output_path: str,
    ) -> Tuple[int, int, int, List[BoundingBox], Dict[str, int], float]:
        """
        Process an image from image_path, write annotated output to annotated_output_path.
        Returns:
            (image_width, image_height, detection_count, boxes, counts_by_class, inference_time_ms)
        """
        if not os.path.exists(image_path):
            raise FileValidationError(f"Source image file not found: {image_path}")

        # 1. Load image using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            raise FileValidationError("Could not decode image with OpenCV. File may be corrupted.")

        # Ensure 3-channel BGR format
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif len(img.shape) == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        height, width = img.shape[:2]

        # 2. Run object detection
        boxes, counts_by_class, inference_time_ms = self.detector.detect(img)

        # 3. Annotate image
        annotated_img = img.copy()
        for box in boxes:
            # Strictly clamp coordinates within image boundaries
            x1 = max(0, min(int(box.x_min), width - 1))
            y1 = max(0, min(int(box.y_min), height - 1))
            x2 = max(0, min(int(box.x_max), width - 1))
            y2 = max(0, min(int(box.y_max), height - 1))

            color = PALETTE[box.class_id % len(PALETTE)]
            class_name = box.class_name or f"class_{box.class_id}"
            label = f"{class_name} {box.confidence:.2f}"

            # Draw bounding box
            cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 2)

            # Draw label background
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

            # Keep text label inside top boundary
            label_y1 = max(0, y1 - text_h - baseline - 4)
            label_y2 = y1
            label_x2 = min(width - 1, x1 + text_w + 6)

            cv2.rectangle(annotated_img, (x1, label_y1), (label_x2, label_y2), color, cv2.FILLED)
            cv2.putText(
                annotated_img,
                label,
                (x1 + 3, label_y2 - baseline - 1),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )

        # 4. Save annotated image to processed destination
        output_dir = Path(annotated_output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        success = cv2.imwrite(annotated_output_path, annotated_img)
        if not success:
            raise FileValidationError(f"Failed to write annotated image to disk: {annotated_output_path}")

        detection_count = len(boxes)
        return width, height, detection_count, boxes, counts_by_class, inference_time_ms
