import logging
import os
from pathlib import Path
import time
from typing import Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np
from app.core.config import get_settings
from app.core.exceptions import FileValidationError
from app.schemas.detection import BoundingBox
from app.vision.detector import YOLODetector

logger = logging.getLogger(__name__)

PALETTE = [
    (245, 158, 11),  # Amber
    (34, 197, 94),   # Green
    (239, 68, 68),   # Red
    (59, 130, 246),  # Blue
    (168, 85, 247),  # Purple
    (236, 72, 153),  # Pink
    (20, 184, 166),  # Teal
]


class VideoPipeline:
    """
    Sequential video processing pipeline:
    1. Opens input video using OpenCV VideoCapture.
    2. Extracts FPS, dimensions, total frame count.
    3. Reads frames sequentially without loading entire video to memory.
    4. Runs YOLO detector on selected frames based on frame interval.
    5. Annotates bounding boxes, class labels, confidence scores with boundary clamping.
    6. Writes annotated frames to output file using VideoWriter.
    7. Periodically invokes progress callback.
    8. Reliably releases capture and writer in finally block.
    """

    def __init__(self, detector: Optional[YOLODetector] = None, frame_interval: Optional[int] = None):
        self.detector = detector or YOLODetector()
        settings = get_settings()
        self.frame_interval = max(1, frame_interval or settings.VIDEO_FRAME_INTERVAL)

    def _draw_annotations(
        self,
        frame: np.ndarray,
        boxes: List[BoundingBox],
        width: int,
        height: int,
    ) -> np.ndarray:
        """Annotate a single frame with bounding boxes and high-contrast labels."""
        annotated = frame.copy()
        for box in boxes:
            x1 = max(0, min(int(box.x_min), width - 1))
            y1 = max(0, min(int(box.y_min), height - 1))
            x2 = max(0, min(int(box.x_max), width - 1))
            y2 = max(0, min(int(box.y_max), height - 1))

            color = PALETTE[box.class_id % len(PALETTE)]
            class_name = box.class_name or f"class_{box.class_id}"
            label = f"{class_name} {box.confidence:.2f}"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

            label_y1 = max(0, y1 - text_h - baseline - 4)
            label_y2 = y1
            label_x2 = min(width - 1, x1 + text_w + 6)

            cv2.rectangle(annotated, (x1, label_y1), (label_x2, label_y2), color, cv2.FILLED)
            cv2.putText(
                annotated,
                label,
                (x1 + 3, label_y2 - baseline - 1),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )
        return annotated

    def process_video(
        self,
        input_path: str,
        output_path: str,
        job_id: str,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> Dict:
        """
        Process input video from disk and generate annotated output video.
        Guarantees cleanup of capture and writer.
        Returns:
            dict containing total_frames, processed_frames, detection_count, duration_seconds.
        """
        if not os.path.exists(input_path):
            raise FileValidationError(f"Input video file does not exist: {input_path}")

        cap = cv2.VideoCapture(input_path)
        writer = None
        output_file_created = False

        try:
            if not cap.isOpened():
                raise FileValidationError("OpenCV could not open input video. Unsupported format or corrupt file.")

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if width <= 0 or height <= 0:
                ret, sample_frame = cap.read()
                if not ret or sample_frame is None:
                    raise FileValidationError("Could not read frames from video.")
                height, width = sample_frame.shape[:2]
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            if fps <= 0.0 or fps > 240.0:
                fps = 30.0

            if total_frames < 0:
                total_frames = 0

            # Prepare destination directory
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

            if not writer.isOpened():
                raise FileValidationError("OpenCV could not initialize video writer for output format.")

            processed_frames = 0
            total_detections = 0
            current_boxes: List[BoundingBox] = []

            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                # Ensure 3 channels
                if len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                elif len(frame.shape) == 3 and frame.shape[2] == 4:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                # Determine if we should perform detection on this frame
                if processed_frames % self.frame_interval == 0:
                    boxes, counts, _ = self.detector.detect(frame)
                    current_boxes = boxes
                    total_detections += len(boxes)

                annotated_frame = self._draw_annotations(frame, current_boxes, width, height)
                writer.write(annotated_frame)
                processed_frames += 1

                if progress_callback is not None:
                    progress_callback(processed_frames, total_frames, total_detections)

            output_file_created = True

            actual_total = max(total_frames, processed_frames)
            duration_seconds = round(processed_frames / fps, 2) if fps > 0 else 0.0

            return {
                "total_frames": actual_total,
                "processed_frames": processed_frames,
                "detection_count": total_detections,
                "duration_seconds": duration_seconds,
            }

        except Exception as exc:
            logger.error("Video processing failed for job %s: %s", job_id, exc)
            if not output_file_created and os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except OSError:
                    pass
            raise

        finally:
            if cap is not None:
                cap.release()
            if writer is not None:
                writer.release()
