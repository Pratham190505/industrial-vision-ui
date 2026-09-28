import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Optional
import anyio
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import get_settings
from app.core.database import get_database
from app.models.collections import CollectionName, get_collection
from app.utils.file_handler import resolve_safe_path
from app.vision.video_pipeline import VideoPipeline

logger = logging.getLogger(__name__)


class ProcessingWorker:
    """
    Worker executing video processing tasks in the background.
    Runs compute-heavy OpenCV/YOLO video inference in a worker thread
    while keeping the FastAPI event loop responsive for status queries.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None, pipeline: Optional[VideoPipeline] = None):
        self.db = db
        self.pipeline = pipeline or VideoPipeline()
        self.settings = get_settings()

    async def run_job(self, job_id: str) -> None:
        """
        Execute video processing job by ID.
        Updates state transitions: queued -> processing -> completed / failed.
        """
        db = self.db if self.db is not None else get_database()
        collection = get_collection(CollectionName.PROCESSING_JOBS, db)

        job = await collection.find_one({"_id": job_id})
        if not job:
            logger.error("Processing job %s not found in database.", job_id)
            return

        now = datetime.now(timezone.utc)
        await collection.update_one(
            {"_id": job_id},
            {"$set": {"status": "processing", "started_at": now, "updated_at": now}},
        )

        stored_filename = job.get("original_path", "").split("/")[-1]
        processed_filename = job.get("processed_filename")

        original_abs = resolve_safe_path(self.settings.upload_videos_path, stored_filename)
        processed_abs = resolve_safe_path(self.settings.processed_videos_path, processed_filename)

        loop = asyncio.get_running_loop()
        last_update_time = [0.0]
        last_progress = [-1]

        def sync_progress_callback(processed: int, total: int, detections: int) -> None:
            current_time = time.time()
            progress = int((processed / total) * 100) if total > 0 else None
            # Throttle updates: every 0.5s or significant percentage change
            should_update = (
                (current_time - last_update_time[0] >= 0.5)
                or (progress is not None and abs(progress - last_progress[0]) >= 5)
            )

            if should_update:
                last_update_time[0] = current_time
                if progress is not None:
                    last_progress[0] = progress

                update_dict = {
                    "processed_frames": processed,
                    "detection_count": detections,
                    "updated_at": datetime.now(timezone.utc),
                }
                if progress is not None:
                    update_dict["progress"] = min(99, max(0, progress))

                asyncio.run_coroutine_threadsafe(
                    collection.update_one({"_id": job_id}, {"$set": update_dict}),
                    loop,
                )

        from app.services.safety_service import SafetyService
        safety_service = SafetyService(db)
        user_id = job.get("user_id", "")
        if user_id:
            try:
                active_zones = await safety_service.get_active_zones_for_user(user_id)
                self.pipeline.set_safety_zones(active_zones)
            except Exception as zone_err:
                logger.warning("Could not load safety zones for job %s: %s", job_id, zone_err)

        try:
            stats = await anyio.to_thread.run_sync(
                self.pipeline.process_video,
                str(original_abs),
                str(processed_abs),
                job_id,
                sync_progress_callback,
            )

            finished_at = datetime.now(timezone.utc)
            update_fields = {
                "status": "completed",
                "progress": 100,
                "processed_frames": stats.get("processed_frames", 0),
                "total_frames": stats.get("total_frames", 0),
                "detection_count": stats.get("detection_count", 0),
                "duration_seconds": stats.get("duration_seconds", 0.0),
                "completed_at": finished_at,
                "updated_at": finished_at,
            }

            # Persist tracking summary if available
            tracking_data = stats.get("tracking")
            if tracking_data is not None:
                update_fields["tracking"] = tracking_data

            # Persist safety summary if available
            safety_data = stats.get("safety")
            if safety_data is not None:
                update_fields["safety"] = safety_data

            # Persist PPE summary and worker compliance if available
            ppe_data = stats.get("ppe")
            if ppe_data is not None:
                update_fields["ppe"] = ppe_data
            ppe_workers = stats.get("ppe_workers")
            if ppe_workers is not None:
                update_fields["ppe_workers"] = ppe_workers

            # Persist safety events
            safety_events = stats.get("safety_events", [])
            if safety_events and user_id:
                try:
                    await safety_service.persist_events(safety_events, job_id, user_id)
                except Exception as ev_err:
                    logger.error("Failed to persist safety events for job %s: %s", job_id, ev_err)

            # Persist PPE violation events
            ppe_events = stats.get("ppe_events", [])
            if ppe_events and user_id:
                try:
                    from app.services.ppe_service import PPEService
                    ppe_service = PPEService(db)
                    await ppe_service.persist_ppe_events(ppe_events, job_id, user_id)
                except Exception as ppe_err:
                    logger.error("Failed to persist PPE events for job %s: %s", job_id, ppe_err)

            # Persist inventory summary, snapshots, and events
            inventory_data = stats.get("inventory")
            if inventory_data is not None:
                update_fields["inventory"] = inventory_data

            inventory_snapshots = stats.get("inventory_snapshots", [])
            inventory_events = stats.get("inventory_events", [])
            if (inventory_snapshots or inventory_events) and user_id:
                try:
                    from app.services.inventory_service import InventoryService
                    inv_service = InventoryService(db)
                    if inventory_snapshots:
                        await inv_service.persist_snapshots(inventory_snapshots, job_id, user_id)
                    if inventory_events:
                        await inv_service.persist_events(inventory_events, job_id, user_id)
                except Exception as inv_err:
                    logger.error("Failed to persist inventory snapshots/events for job %s: %s", job_id, inv_err)

            await collection.update_one(
                {"_id": job_id},
                {"$set": update_fields},
            )
            logger.info("Successfully completed processing job %s.", job_id)

        except Exception as exc:
            logger.error("Processing job %s encountered an error: %s", job_id, exc, exc_info=True)
            if processed_abs.exists():
                try:
                    processed_abs.unlink()
                except OSError:
                    pass

            failed_at = datetime.now(timezone.utc)
            await collection.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "error_message": "Video processing failed. Please upload a supported video file and try again.",
                        "updated_at": failed_at,
                    }
                },
            )
