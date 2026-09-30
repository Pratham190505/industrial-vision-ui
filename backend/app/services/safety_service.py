"""
Safety Service — persistence, querying, and domain logic for safety events and zones.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import EntityNotFoundError
from app.models.collections import CollectionName, get_collection
from app.schemas.safety import (
    SafetyEvent,
    SafetyEventList,
    SafetySummary,
    SafetyZoneCreate,
    SafetyZoneList,
    SafetyZoneResponse,
    SafetyZoneUpdate,
)

logger = logging.getLogger(__name__)


class SafetyService:
    """Service handling CRUD for safety zones and safety events."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.events_coll = get_collection(CollectionName.SAFETY_EVENTS, db)
        self.zones_coll = get_collection(CollectionName.SAFETY_ZONES, db)
        self.jobs_coll = get_collection(CollectionName.PROCESSING_JOBS, db)

    async def ensure_indexes(self) -> None:
        """Create indexes for safety collections."""
        try:
            await self.events_coll.create_index([("job_id", 1)])
            await self.events_coll.create_index([("user_id", 1)])
            await self.events_coll.create_index([("event_type", 1)])
            await self.events_coll.create_index([("severity", 1)])
            await self.events_coll.create_index([("created_at", -1)])
            await self.zones_coll.create_index([("user_id", 1)])
        except Exception as exc:
            logger.warning("Could not ensure indexes for safety collections: %s", exc)

    # -------------------------------------------------------------------------
    # Safety Zones CRUD
    # -------------------------------------------------------------------------

    async def create_zone(self, user_id: str, data: SafetyZoneCreate) -> SafetyZoneResponse:
        zone_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        doc = {
            "_id": zone_id,
            "user_id": user_id,
            "name": data.name,
            "zone_type": data.zone_type,
            "polygon": data.polygon,
            "enabled": data.enabled,
            "created_at": now,
            "updated_at": now,
        }
        await self.zones_coll.insert_one(doc)
        return SafetyZoneResponse(
            zone_id=zone_id,
            user_id=user_id,
            name=doc["name"],
            zone_type=doc["zone_type"],
            polygon=doc["polygon"],
            enabled=doc["enabled"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )

    async def get_zones(self, user_id: str) -> SafetyZoneList:
        cursor = self.zones_coll.find({"user_id": user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=1000)
        items = []
        for doc in docs:
            items.append(
                SafetyZoneResponse(
                    zone_id=str(doc["_id"]),
                    user_id=str(doc["user_id"]),
                    name=doc["name"],
                    zone_type=doc.get("zone_type", "restricted"),
                    polygon=doc["polygon"],
                    enabled=doc.get("enabled", True),
                    created_at=doc.get("created_at", datetime.now(timezone.utc)),
                    updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
                )
            )
        return SafetyZoneList(items=items, total=len(items))

    async def get_active_zones_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Return list of active zone dicts formatted for the SafetyAnalyzer."""
        cursor = self.zones_coll.find({"user_id": user_id, "enabled": True})
        docs = await cursor.to_list(length=1000)
        zones = []
        for doc in docs:
            zones.append({
                "zone_id": str(doc["_id"]),
                "name": doc.get("name", "Restricted Zone"),
                "polygon": doc.get("polygon", []),
                "enabled": True,
            })
        return zones

    async def get_zone(self, zone_id: str, user_id: str) -> SafetyZoneResponse:
        doc = await self.zones_coll.find_one({"_id": zone_id, "user_id": user_id})
        if not doc:
            raise EntityNotFoundError("SafetyZone", zone_id)
        return SafetyZoneResponse(
            zone_id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            name=doc["name"],
            zone_type=doc.get("zone_type", "restricted"),
            polygon=doc["polygon"],
            enabled=doc.get("enabled", True),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
        )

    async def update_zone(self, zone_id: str, user_id: str, data: SafetyZoneUpdate) -> SafetyZoneResponse:
        doc = await self.zones_coll.find_one({"_id": zone_id, "user_id": user_id})
        if not doc:
            raise EntityNotFoundError("SafetyZone", zone_id)

        update_fields: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        if data.name is not None:
            update_fields["name"] = data.name
        if data.zone_type is not None:
            update_fields["zone_type"] = data.zone_type
        if data.polygon is not None:
            update_fields["polygon"] = data.polygon
        if data.enabled is not None:
            update_fields["enabled"] = data.enabled

        await self.zones_coll.update_one({"_id": zone_id, "user_id": user_id}, {"$set": update_fields})
        updated_doc = await self.zones_coll.find_one({"_id": zone_id, "user_id": user_id})
        return SafetyZoneResponse(
            zone_id=str(updated_doc["_id"]),
            user_id=str(updated_doc["user_id"]),
            name=updated_doc["name"],
            zone_type=updated_doc.get("zone_type", "restricted"),
            polygon=updated_doc["polygon"],
            enabled=updated_doc.get("enabled", True),
            created_at=updated_doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=updated_doc.get("updated_at", datetime.now(timezone.utc)),
        )

    async def delete_zone(self, zone_id: str, user_id: str) -> bool:
        doc = await self.zones_coll.find_one({"_id": zone_id, "user_id": user_id})
        if not doc:
            raise EntityNotFoundError("SafetyZone", zone_id)
        await self.zones_coll.delete_one({"_id": zone_id, "user_id": user_id})
        return True

    # -------------------------------------------------------------------------
    # Safety Events Persistence and Retrieval
    # -------------------------------------------------------------------------

    async def persist_events(
        self,
        events: List[Dict[str, Any]],
        job_id: Optional[str] = None,
        user_id: str = "",
        session_id: Optional[str] = None,
    ) -> int:
        if not events:
            return 0

        now = datetime.now(timezone.utc)
        docs = []
        for ev in events:
            event_id = uuid.uuid4().hex
            docs.append({
                "_id": event_id,
                "job_id": job_id,
                "session_id": session_id or job_id,
                "user_id": user_id,
                "event_type": ev.get("event_type", "safety_event"),
                "severity": ev.get("severity", "warning"),
                "track_ids": ev.get("track_ids", []),
                "zone_id": ev.get("zone_id"),
                "distance": ev.get("distance"),
                "frame_number": ev.get("frame_number", 0),
                "timestamp_seconds": ev.get("timestamp_seconds", 0.0),
                "message": ev.get("message", "Safety event detected."),
                "created_at": now,
            })

        for doc in docs:
            await self.events_coll.insert_one(doc)

        return len(docs)

    async def get_events(
        self,
        user_id: str,
        job_id: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> SafetyEventList:
        query: Dict[str, Any] = {"user_id": user_id}

        if job_id:
            # Verify job ownership
            job = await self.jobs_coll.find_one({"_id": job_id, "user_id": user_id})
            if not job:
                raise EntityNotFoundError("ProcessingJob", job_id)
            query["job_id"] = job_id

        if event_type:
            query["event_type"] = event_type
        if severity:
            query["severity"] = severity

        total = await self.events_coll.count_documents(query)
        cursor = self.events_coll.find(query).sort("created_at", -1).skip(skip).limit(limit)

        items = []
        docs = await cursor.to_list(length=limit)
        for doc in docs:
            items.append(
                SafetyEvent(
                    event_id=str(doc["_id"]),
                    job_id=str(doc.get("job_id", "")),
                    user_id=str(doc.get("user_id", "")),
                    event_type=doc.get("event_type", "safety_event"),
                    severity=doc.get("severity", "warning"),
                    track_ids=doc.get("track_ids", []),
                    zone_id=doc.get("zone_id"),
                    distance=doc.get("distance"),
                    frame_number=doc.get("frame_number", 0),
                    timestamp_seconds=doc.get("timestamp_seconds", 0.0),
                    message=doc.get("message", ""),
                    created_at=doc.get("created_at", datetime.now(timezone.utc)),
                )
            )

        return SafetyEventList(items=items, total=total, skip=skip, limit=limit)

    async def get_event(self, event_id: str, user_id: str) -> SafetyEvent:
        doc = await self.events_coll.find_one({"_id": event_id, "user_id": user_id})
        if not doc:
            raise EntityNotFoundError("SafetyEvent", event_id)
        return SafetyEvent(
            event_id=str(doc["_id"]),
            job_id=str(doc.get("job_id", "")),
            user_id=str(doc.get("user_id", "")),
            event_type=doc.get("event_type", "safety_event"),
            severity=doc.get("severity", "warning"),
            track_ids=doc.get("track_ids", []),
            zone_id=doc.get("zone_id"),
            distance=doc.get("distance"),
            frame_number=doc.get("frame_number", 0),
            timestamp_seconds=doc.get("timestamp_seconds", 0.0),
            message=doc.get("message", ""),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
        )

    async def get_job_summary(self, job_id: str, user_id: str) -> SafetySummary:
        job = await self.jobs_coll.find_one({"_id": job_id, "user_id": user_id})
        if not job:
            raise EntityNotFoundError("ProcessingJob", job_id)

        safety_data = job.get("safety")
        if safety_data and isinstance(safety_data, dict):
            return SafetySummary(**safety_data)

        return SafetySummary(enabled=False)
