from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.collections import CollectionName, get_collection
from app.vision.image_pipeline import ImagePipeline

logger = logging.getLogger(__name__)


class DetectionService:
    """Service orchestrating YOLO detection pipeline execution and database updates."""

    def __init__(self, db: AsyncIOMotorDatabase, pipeline: Optional[ImagePipeline] = None):
        self.db = db
        self.collection = get_collection(CollectionName.IMAGES, db)
        self.pipeline = pipeline or ImagePipeline()

    async def process_image_analysis(
        self,
        analysis_id: str,
        original_abs_path: Path,
        annotated_abs_path: Path,
    ) -> Dict:
        """
        Runs YOLO inference and annotation pipeline on the uploaded image.
        Updates the MongoDB record to completed or failed.
        """
        try:
            # 1. Run pipeline
            width, height, detection_count, boxes, counts_by_class, inference_time_ms = (
                self.pipeline.process_image(
                    image_path=str(original_abs_path),
                    annotated_output_path=str(annotated_abs_path),
                )
            )

            # 2. Serialize bounding boxes for storage
            boxes_data = [box.model_dump() for box in boxes]
            now = datetime.now(timezone.utc)

            # 3. Update database record to completed
            update_data = {
                "status": "completed",
                "image_width": width,
                "image_height": height,
                "detection_count": detection_count,
                "detections": boxes_data,
                "counts_by_class": counts_by_class,
                "inference_time_ms": inference_time_ms,
                "updated_at": now,
            }

            await self.collection.update_one(
                {"_id": analysis_id},
                {"$set": update_data},
            )

            # Fetch and return updated document
            updated_doc = await self.collection.find_one({"_id": analysis_id})
            return updated_doc or update_data

        except Exception as exc:
            logger.error("Failed to process image analysis %s: %s", analysis_id, exc)

            # Clean up partial annotated file if created
            if annotated_abs_path.exists():
                try:
                    annotated_abs_path.unlink()
                except OSError:
                    pass

            now = datetime.now(timezone.utc)
            error_data = {
                "status": "failed",
                "error_message": "Image processing encountered an unexpected error.",
                "updated_at": now,
            }

            await self.collection.update_one(
                {"_id": analysis_id},
                {"$set": error_data},
            )

            failed_doc = await self.collection.find_one({"_id": analysis_id})
            return failed_doc or error_data
