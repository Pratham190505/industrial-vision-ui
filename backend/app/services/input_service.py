from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid
from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import get_settings
from app.core.exceptions import EntityNotFoundError, FileValidationError
from app.models.collections import CollectionName, get_collection
from app.utils.file_handler import (
    get_annotated_filename,
    get_image_media_type,
    resolve_safe_path,
    save_upload_image,
)

logger = logging.getLogger(__name__)


class InputService:
    """Service handling image upload validation, storage, and retrieval."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = get_collection(CollectionName.IMAGES, db)
        self.settings = get_settings()

    async def ensure_indexes(self) -> None:
        """Create database indexes for optimal querying."""
        try:
            await self.collection.create_index([("user_id", 1)])
            await self.collection.create_index([("created_at", -1)])
            await self.collection.create_index([("status", 1)])
        except Exception as exc:
            logger.warning("Could not ensure indexes on images collection: %s", exc)

    async def save_uploaded_image(
        self,
        file: UploadFile,
        user_id: str,
    ) -> Tuple[str, str, Path, str, Path, int, int, int]:
        """
        Validate and save uploaded image to local storage.
        Returns:
            (analysis_id, stored_filename, original_abs_path, annotated_filename, annotated_abs_path, size_bytes, width, height)
        """
        analysis_id = uuid.uuid4().hex
        stored_filename, original_abs_path, size_bytes, width, height = await save_upload_image(
            file=file,
            destination_directory=self.settings.upload_images_path,
            max_bytes=self.settings.max_image_size_bytes,
        )

        annotated_filename = get_annotated_filename(stored_filename)
        annotated_abs_path = resolve_safe_path(self.settings.processed_images_path, annotated_filename)

        return (
            analysis_id,
            stored_filename,
            original_abs_path,
            annotated_filename,
            annotated_abs_path,
            size_bytes,
            width, height,
        )

    async def create_analysis_record(
        self,
        analysis_id: str,
        user_id: str,
        original_filename: str,
        stored_filename: str,
        annotated_filename: str,
        width: int,
        height: int,
    ) -> Dict:
        """Create the initial image analysis document in MongoDB."""
        now = datetime.now(timezone.utc)
        doc = {
            "_id": analysis_id,
            "user_id": user_id,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "original_path": f"storage/uploads/images/{stored_filename}",
            "annotated_filename": annotated_filename,
            "annotated_path": f"storage/processed/images/{annotated_filename}",
            "status": "processing",
            "image_width": width,
            "image_height": height,
            "detection_count": 0,
            "detections": [],
            "counts_by_class": {},
            "model_name": self.settings.YOLO_MODEL_PATH,
            "inference_time_ms": 0.0,
            "created_at": now,
            "updated_at": now,
            "error_message": None,
        }

        await self.collection.insert_one(doc)
        return doc

    async def get_image_analysis(self, analysis_id: str, user_id: str) -> Dict:
        """
        Retrieve image analysis record for an authenticated user.
        Raises EntityNotFoundError if record does not exist or user is not the owner.
        """
        doc = await self.collection.find_one({"_id": analysis_id, "user_id": user_id})
        if not doc:
            raise EntityNotFoundError("ImageAnalysis", analysis_id)
        return doc

    async def get_image_file_path(
        self,
        analysis_id: str,
        user_id: str,
        file_type: str = "original",
    ) -> Tuple[Path, str]:
        """
        Safely retrieve the absolute filesystem path and MIME type for an image file.
        Verifies ownership and prevents path traversal.
        """
        doc = await self.get_image_analysis(analysis_id, user_id)

        if file_type == "annotated":
            filename = doc.get("annotated_filename")
            base_dir = self.settings.processed_images_path
        else:
            filename = doc.get("stored_filename")
            base_dir = self.settings.upload_images_path

        if not filename:
            raise EntityNotFoundError("ImageFile", analysis_id)

        safe_path = resolve_safe_path(base_dir, filename)
        if not safe_path.exists():
            raise EntityNotFoundError("ImageFile", f"{analysis_id} ({file_type})")

        media_type = get_image_media_type(filename)
        return safe_path, media_type

    async def list_user_images(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None,
    ) -> Tuple[List[Dict], int]:
        """Retrieve paginated list of image analyses belonging to user."""
        query: Dict = {"user_id": user_id}
        if status_filter:
            query["status"] = status_filter

        total = await self.collection.count_documents(query)
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)

        return items, total
