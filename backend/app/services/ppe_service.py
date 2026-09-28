"""
PPE Service — persistence, querying, and domain logic for PPE compliance data.

Handles MongoDB persistence for PPE events and summaries, and provides
query methods for PPE API endpoints.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import EntityNotFoundError
from app.models.collections import CollectionName, get_collection
from app.schemas.ppe import (
    PPESummary,
    PPEWorkerCompliance,
    PPEWorkerComplianceList,
)

logger = logging.getLogger(__name__)


class PPEService:
    """Service handling PPE compliance querying and persistence."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.events_coll = get_collection(CollectionName.SAFETY_EVENTS, db)
        self.jobs_coll = get_collection(CollectionName.PROCESSING_JOBS, db)

    # -----------------------------------------------------------------
    # PPE Events Persistence
    # -----------------------------------------------------------------

    async def persist_ppe_events(
        self,
        events: List[Dict[str, Any]],
        job_id: str,
        user_id: str,
    ) -> int:
        """Persist PPE violation events into the safety_events collection."""
        if not events:
            return 0

        now = datetime.now(timezone.utc)
        count = 0
        for ev in events:
            event_id = uuid.uuid4().hex
            doc = {
                "_id": event_id,
                "job_id": job_id,
                "user_id": user_id,
                "event_type": ev.get("event_type", "ppe_violation"),
                "severity": ev.get("severity", "high"),
                "track_ids": ev.get("track_ids", []),
                "zone_id": ev.get("zone_id"),
                "distance": ev.get("distance"),
                "missing_ppe": ev.get("missing_ppe", []),
                "frame_number": ev.get("frame_number", 0),
                "timestamp_seconds": ev.get("timestamp_seconds", 0.0),
                "message": ev.get("message", "PPE violation detected."),
                "created_at": now,
            }
            await self.events_coll.insert_one(doc)
            count += 1

        return count

    # -----------------------------------------------------------------
    # PPE Summary Retrieval
    # -----------------------------------------------------------------

    async def get_ppe_summary(self, job_id: str, user_id: str) -> PPESummary:
        """Retrieve PPE summary from processing job document."""
        job = await self.jobs_coll.find_one({"_id": job_id, "user_id": user_id})
        if not job:
            raise EntityNotFoundError("ProcessingJob", job_id)

        ppe_data = job.get("ppe")
        if ppe_data and isinstance(ppe_data, dict):
            return PPESummary(**ppe_data)

        return PPESummary(enabled=False, available=False, reason="PPE data not available for this job.")

    # -----------------------------------------------------------------
    # PPE Worker Compliance Retrieval
    # -----------------------------------------------------------------

    async def get_worker_compliance(self, job_id: str, user_id: str) -> PPEWorkerComplianceList:
        """
        Retrieve per-worker PPE compliance from the processing job document.

        Worker compliance is stored as an array in the job's ``ppe_workers`` field.
        """
        job = await self.jobs_coll.find_one({"_id": job_id, "user_id": user_id})
        if not job:
            raise EntityNotFoundError("ProcessingJob", job_id)

        workers_data = job.get("ppe_workers", [])
        items = []
        for w in workers_data:
            items.append(
                PPEWorkerCompliance(
                    track_id=w.get("track_id", 0),
                    required_ppe=w.get("required_ppe", []),
                    detected_ppe=w.get("detected_ppe", []),
                    missing_ppe=w.get("missing_ppe", []),
                    status=w.get("status", "unknown"),
                )
            )

        return PPEWorkerComplianceList(items=items, total=len(items))
