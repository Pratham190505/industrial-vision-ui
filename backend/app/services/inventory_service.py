"""
Inventory Service — persistence, querying, and domain logic for inventory monitoring.

Handles MongoDB persistence for inventory snapshots and events, enforces user ownership,
and provides query methods for inventory history and summaries.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import EntityNotFoundError
from app.models.collections import CollectionName, get_collection
from app.schemas.inventory import (
    InventoryEvent,
    InventoryEventListResponse,
    InventoryHistoryResponse,
    InventorySnapshot,
    InventorySummary,
)

logger = logging.getLogger(__name__)


class InventoryService:
    """Service handling inventory monitoring persistence and queries."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.snapshots_coll = get_collection(CollectionName.INVENTORY_SNAPSHOTS, db)
        self.events_coll = get_collection(CollectionName.INVENTORY_EVENTS, db)
        self.jobs_coll = get_collection(CollectionName.PROCESSING_JOBS, db)

    async def ensure_indexes(self) -> None:
        """Create necessary indexes for inventory collections."""
        try:
            await self.snapshots_coll.create_index([("job_id", 1)])
            await self.snapshots_coll.create_index([("user_id", 1)])
            await self.snapshots_coll.create_index([("created_at", -1)])

            await self.events_coll.create_index([("job_id", 1)])
            await self.events_coll.create_index([("user_id", 1)])
            await self.events_coll.create_index([("event_type", 1)])
            await self.events_coll.create_index([("class_name", 1)])
            await self.events_coll.create_index([("created_at", -1)])
            logger.info("Inventory collection indexes ensured.")
        except Exception as exc:
            logger.warning("Could not create inventory collection indexes: %s", exc)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def persist_snapshots(
        self,
        snapshots: List[Dict[str, Any]],
        job_id: str,
        user_id: str,
    ) -> int:
        """
        Persist periodic inventory snapshots into MongoDB.
        """
        if not snapshots:
            return 0

        now = datetime.now(timezone.utc)
        count = 0
        for s in snapshots:
            doc = {
                "_id": uuid.uuid4().hex,
                "job_id": job_id,
                "user_id": user_id,
                "timestamp_seconds": float(s.get("timestamp_seconds", 0.0)),
                "frame_number": int(s.get("frame_number", 0)),
                "counts": s.get("counts", {}),
                "created_at": now,
            }
            await self.snapshots_coll.insert_one(doc)
            count += 1

        return count

    async def persist_events(
        self,
        events: List[Dict[str, Any]],
        job_id: str,
        user_id: str,
    ) -> int:
        """
        Persist inventory events (count changes, low-stock warnings) into MongoDB.
        """
        if not events:
            return 0

        now = datetime.now(timezone.utc)
        count = 0
        for ev in events:
            doc = {
                "_id": uuid.uuid4().hex,
                "job_id": job_id,
                "user_id": user_id,
                "event_type": ev.get("event_type", "inventory_count_change"),
                "class_name": ev.get("class_name", ""),
                "previous_count": ev.get("previous_count"),
                "current_count": int(ev.get("current_count", 0)),
                "change": ev.get("change"),
                "threshold": ev.get("threshold"),
                "frame_number": int(ev.get("frame_number", 0)),
                "timestamp_seconds": float(ev.get("timestamp_seconds", 0.0)),
                "message": ev.get("message", ""),
                "created_at": now,
            }
            await self.events_coll.insert_one(doc)
            count += 1

        return count

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    async def get_inventory_summary(self, job_id: str, user_id: str) -> InventorySummary:
        """
        Retrieve inventory summary for a processing job with ownership verification.
        """
        job = await self.jobs_coll.find_one({"_id": job_id, "user_id": user_id})
        if not job:
            raise EntityNotFoundError("ProcessingJob", job_id)

        inv_data = job.get("inventory")
        if inv_data and isinstance(inv_data, dict):
            return InventorySummary(**inv_data)

        return InventorySummary(
            enabled=False,
            available_classes=[],
            unavailable_classes=[],
            reason="Inventory summary not available for this job.",
        )

    async def get_inventory_snapshots(
        self,
        job_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> InventoryHistoryResponse:
        """
        Retrieve paginated periodic inventory snapshots for a job.
        """
        job = await self.jobs_coll.find_one({"_id": job_id, "user_id": user_id})
        if not job:
            raise EntityNotFoundError("ProcessingJob", job_id)

        query = {"job_id": job_id, "user_id": user_id}
        total = await self.snapshots_coll.count_documents(query)

        cursor = (
            self.snapshots_coll.find(query)
            .sort("timestamp_seconds", 1)
            .skip(skip)
            .limit(limit)
        )

        docs = await cursor.to_list(length=limit)
        snapshots = [InventorySnapshot(**doc) for doc in docs]

        return InventoryHistoryResponse(
            job_id=job_id,
            snapshots=snapshots,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_job_inventory_events(
        self,
        job_id: str,
        user_id: str,
        event_type: Optional[str] = None,
        class_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> InventoryEventListResponse:
        """
        Retrieve paginated inventory events for a specific job.
        """
        job = await self.jobs_coll.find_one({"_id": job_id, "user_id": user_id})
        if not job:
            raise EntityNotFoundError("ProcessingJob", job_id)

        query: Dict[str, Any] = {"job_id": job_id, "user_id": user_id}
        if event_type:
            query["event_type"] = event_type
        if class_name:
            query["class_name"] = class_name

        total = await self.events_coll.count_documents(query)
        cursor = (
            self.events_coll.find(query)
            .sort("timestamp_seconds", 1)
            .skip(skip)
            .limit(limit)
        )

        docs = await cursor.to_list(length=limit)
        events = [InventoryEvent(**doc) for doc in docs]

        return InventoryEventListResponse(
            events=events,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_user_inventory_events(
        self,
        user_id: str,
        event_type: Optional[str] = None,
        class_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> InventoryEventListResponse:
        """
        Retrieve paginated inventory events across all jobs owned by the user.
        """
        query: Dict[str, Any] = {"user_id": user_id}
        if event_type:
            query["event_type"] = event_type
        if class_name:
            query["class_name"] = class_name

        total = await self.events_coll.count_documents(query)
        cursor = (
            self.events_coll.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        docs = await cursor.to_list(length=limit)
        events = [InventoryEvent(**doc) for doc in docs]

        return InventoryEventListResponse(
            events=events,
            total=total,
            skip=skip,
            limit=limit,
        )
