from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import get_settings
from app.core.exceptions import EntityNotFoundError, FileValidationError
from app.models.collections import CollectionName, get_collection
from app.utils.file_handler import get_video_media_type, resolve_safe_path

logger = logging.getLogger(__name__)


class ProcessingService:
    """Service managing video processing jobs, state transitions, and file resolution."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = get_collection(CollectionName.PROCESSING_JOBS, db)
        self.settings = get_settings()

    async def ensure_indexes(self) -> None:
        """Ensure indexes for processing_jobs collection."""
        try:
            await self.collection.create_index([("user_id", 1)])
            await self.collection.create_index([("status", 1)])
            await self.collection.create_index([("created_at", -1)])
        except Exception as exc:
            logger.warning("Could not ensure indexes on processing_jobs collection: %s", exc)

    async def create_job(
        self,
        job_id: str,
        user_id: str,
        original_filename: str,
        stored_filename: str,
        processed_filename: str,
        video_metadata: dict,
    ) -> Dict:
        """Create initial processing job record with status 'queued'."""
        now = datetime.now(timezone.utc)
        doc = {
            "_id": job_id,
            "user_id": user_id,
            "media_type": "video",
            "original_filename": original_filename,
            "original_path": f"storage/uploads/videos/{stored_filename}",
            "processed_filename": processed_filename,
            "processed_path": f"storage/processed/videos/{processed_filename}",
            "status": "queued",
            "progress": 0,
            "total_frames": video_metadata.get("total_frames", 0),
            "processed_frames": 0,
            "fps": video_metadata.get("fps", 30.0),
            "width": video_metadata.get("width", 0),
            "height": video_metadata.get("height", 0),
            "duration_seconds": video_metadata.get("duration_seconds", 0.0),
            "detection_count": 0,
            "model_name": self.settings.YOLO_MODEL_PATH,
            "error_message": None,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "updated_at": now,
        }
        await self.collection.insert_one(doc)
        return doc

    async def get_job(self, job_id: str, user_id: str) -> Dict:
        """
        Retrieve a processing job for an authenticated user.
        Raises EntityNotFoundError if missing or owned by another user.
        """
        doc = await self.collection.find_one({"_id": job_id, "user_id": user_id})
        if not doc:
            raise EntityNotFoundError("ProcessingJob", job_id)
        return doc

    async def get_video_file_path(self, job_id: str, user_id: str) -> Tuple[Path, str]:
        """
        Safely retrieve the absolute filesystem path and MIME type for a processed video.
        Ensures job ownership and completed state before returning.
        """
        doc = await self.get_job(job_id, user_id)

        if doc.get("status") != "completed":
            raise EntityNotFoundError("ProcessedVideo", f"{job_id} (not completed)")

        filename = doc.get("processed_filename")
        if not filename:
            raise EntityNotFoundError("ProcessedVideo", job_id)

        safe_path = resolve_safe_path(self.settings.processed_videos_path, filename)
        if not safe_path.exists():
            raise EntityNotFoundError("ProcessedVideo", f"{job_id} (file not found on disk)")

        media_type = get_video_media_type(filename)
        return safe_path, media_type

    async def list_user_jobs(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None,
    ) -> Tuple[List[Dict], int]:
        """Retrieve paginated list of processing jobs belonging to authenticated user."""
        query: Dict = {"user_id": user_id}
        if status_filter:
            query["status"] = status_filter

        total = await self.collection.count_documents(query)
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        return items, total
