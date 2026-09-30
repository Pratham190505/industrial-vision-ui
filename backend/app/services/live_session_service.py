"""
Live Session Service — In-memory registry and MongoDB persistence for live sessions.

Maintains session-isolated object trackers, safety analyzers, PPE analyzers,
and inventory analyzers during real-time webcam processing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Set
import uuid
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.exceptions import EntityNotFoundError
from app.models.collections import CollectionName, get_collection
from app.schemas.live import (
    LiveSessionCreateResponse,
    LiveSessionItem,
    LiveSessionListResponse,
    LiveSessionStopResponse,
    LiveSessionSummary,
)
from app.services.safety_service import SafetyService
from app.services.tracking_service import get_tracker_config_name
from app.vision.detector import YOLODetector
from app.vision.inventory import InventoryAnalyzer
from app.vision.ppe import PPEAnalyzer, PPEDetector
from app.vision.safety import SafetyAnalyzer
from app.vision.tracker import ObjectTracker

logger = logging.getLogger(__name__)


@dataclass
class LiveSessionState:
    """In-memory state preserved across frames for a single active live session."""
    session_id: str
    user_id: str
    status: str = "active"
    tracker: Optional[ObjectTracker] = None
    safety_analyzer: Optional[SafetyAnalyzer] = None
    ppe_analyzer: Optional[PPEAnalyzer] = None
    inventory_analyzer: Optional[InventoryAnalyzer] = None
    frame_counter: int = 0
    start_time: float = field(default_factory=time.time)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processing_times: List[float] = field(default_factory=list)
    unique_track_ids: Set[int] = field(default_factory=set)
    total_safety_events: int = 0
    total_ppe_events: int = 0
    total_inventory_events: int = 0


class LiveSessionService:
    """
    Manages live webcam monitoring sessions.
    Coordinates temporary in-memory session pipelines and MongoDB persistence.
    """

    # In-memory registry for single-process active sessions
    _active_sessions: Dict[str, LiveSessionState] = {}
    _shared_detector: Optional[YOLODetector] = None

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.sessions_coll = get_collection(CollectionName.LIVE_SESSIONS, db)

    async def ensure_indexes(self) -> None:
        """Create necessary indexes for the live_sessions collection."""
        try:
            await self.sessions_coll.create_index([("user_id", 1)])
            await self.sessions_coll.create_index([("status", 1)])
            await self.sessions_coll.create_index([("created_at", -1)])
            logger.info("Live sessions collection indexes ensured.")
        except Exception as exc:
            logger.warning("Could not create live sessions indexes: %s", exc)

    @classmethod
    def get_shared_detector(cls) -> YOLODetector:
        """Lazily load and share detector weights across sessions to optimize memory."""
        if cls._shared_detector is None:
            detector = YOLODetector()
            detector.load_model()
            cls._shared_detector = detector
        return cls._shared_detector

    # ------------------------------------------------------------------
    # Session Lifecycle
    # ------------------------------------------------------------------

    async def create_session(self, user_id: str) -> LiveSessionCreateResponse:
        """
        Create and initialize a new live monitoring session with its own
        isolated tracker, safety analyzer, PPE analyzer, and inventory analyzer.
        """
        settings = get_settings()
        session_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)

        # 1. Initialize session-isolated tracker
        tracker = None
        detector = self.get_shared_detector()
        if detector.model is not None:
            try:
                tracker_yaml = get_tracker_config_name(settings.TRACKER_TYPE)
                tracker = ObjectTracker(
                    model=detector.model,
                    tracker_config=tracker_yaml,
                    conf=settings.TRACKER_CONFIDENCE_THRESHOLD,
                    iou=settings.TRACKER_IOU_THRESHOLD,
                    device=settings.YOLO_DEVICE,
                    imgsz=settings.YOLO_IMAGE_SIZE,
                    max_det=settings.YOLO_MAX_DETECTIONS,
                )
            except Exception as trk_err:
                logger.warning("Could not initialize live tracker: %s", trk_err)

        # 2. Initialize session-isolated SafetyAnalyzer with user's active zones
        safety_zones = []
        try:
            safety_service = SafetyService(self.db)
            safety_zones = await safety_service.get_active_zones_for_user(user_id)
        except Exception as zone_err:
            logger.warning("Could not load safety zones for live session: %s", zone_err)

        safety_analyzer = SafetyAnalyzer(
            safety_enabled=settings.SAFETY_ENABLED,
            person_classes=settings.person_classes_set,
            forklift_classes=settings.forklift_classes_set,
            proximity_warning_distance=settings.PROXIMITY_WARNING_DISTANCE,
            collision_warning_distance=settings.COLLISION_WARNING_DISTANCE,
            restricted_zone_enabled=settings.RESTRICTED_ZONE_ENABLED,
            event_cooldown_seconds=settings.EVENT_COOLDOWN_SECONDS,
            velocity_window_frames=settings.VELOCITY_WINDOW_FRAMES,
            zones=safety_zones,
        )

        # 3. Initialize session-isolated PPEAnalyzer
        ppe_analyzer = None
        if settings.PPE_ENABLED:
            ppe_det = PPEDetector(
                model_path=settings.PPE_MODEL_PATH or None,
                confidence_threshold=settings.YOLO_CONFIDENCE_THRESHOLD,
                device=settings.YOLO_DEVICE,
                image_size=settings.YOLO_IMAGE_SIZE,
                helmet_classes=settings.ppe_helmet_classes_set,
                vest_classes=settings.ppe_vest_classes_set,
                glove_classes=settings.ppe_glove_classes_set,
                shoe_classes=settings.ppe_shoe_classes_set,
            )
            if settings.PPE_MODEL_PATH:
                ppe_det.load_model()
            elif detector.model is not None:
                ppe_det.set_shared_model(detector.model)
            else:
                ppe_det._is_available = False
                ppe_det._unavailable_reason = "Main YOLO model not loaded."

            ppe_analyzer = PPEAnalyzer(
                ppe_detector=ppe_det,
                required_ppe=settings.required_ppe_set,
                association_iou_threshold=settings.PPE_ASSOCIATION_IOU_THRESHOLD,
                missing_confirmation_frames=settings.PPE_MISSING_CONFIRMATION_FRAMES,
                event_cooldown_seconds=settings.PPE_EVENT_COOLDOWN_SECONDS,
                person_classes=settings.person_classes_set,
            )

        # 4. Initialize session-isolated InventoryAnalyzer
        inventory_analyzer = None
        if settings.INVENTORY_ENABLED:
            inventory_analyzer = InventoryAnalyzer(
                configured_classes=settings.inventory_classes_set,
                confidence_threshold=settings.INVENTORY_CONFIDENCE_THRESHOLD,
                count_mode=settings.INVENTORY_COUNT_MODE,
                snapshot_interval_seconds=settings.INVENTORY_SNAPSHOT_INTERVAL_SECONDS,
                change_threshold=settings.INVENTORY_CHANGE_THRESHOLD,
                low_stock_enabled=settings.INVENTORY_LOW_STOCK_ENABLED,
                low_stock_thresholds=settings.inventory_thresholds,
                event_cooldown_seconds=settings.INVENTORY_EVENT_COOLDOWN_SECONDS,
                enabled=settings.INVENTORY_ENABLED,
            )
            model_names = getattr(detector.model, "names", None) if detector.model is not None else None
            inventory_analyzer.inspect_model_classes(model_names)

        # 5. Register in-memory state
        session_state = LiveSessionState(
            session_id=session_id,
            user_id=user_id,
            status="active",
            tracker=tracker,
            safety_analyzer=safety_analyzer,
            ppe_analyzer=ppe_analyzer,
            inventory_analyzer=inventory_analyzer,
            start_time=time.time(),
            created_at=now,
            last_activity_at=now,
        )
        self._active_sessions[session_id] = session_state

        # 6. Insert initial record in MongoDB
        doc = {
            "_id": session_id,
            "user_id": user_id,
            "status": "active",
            "created_at": now,
            "last_activity_at": now,
            "stopped_at": None,
            "frame_count": 0,
            "duration_seconds": 0.0,
            "total_safety_events": 0,
            "total_ppe_events": 0,
            "total_inventory_events": 0,
            "unique_tracks": 0,
            "average_processing_time_ms": 0.0,
        }
        await self.sessions_coll.insert_one(doc)

        logger.info("Created live monitoring session %s for user %s", session_id, user_id)
        return LiveSessionCreateResponse(
            session_id=session_id,
            status="active",
            created_at=now,
        )

    async def get_session(self, session_id: str, user_id: str) -> LiveSessionState:
        """
        Retrieve and validate an active live session, enforcing ownership and inactivity timeout.
        """
        settings = get_settings()
        now = datetime.now(timezone.utc)

        session = self._active_sessions.get(session_id)
        if session is not None:
            if session.user_id != user_id:
                raise EntityNotFoundError("LiveSession", session_id)

            # Check inactivity timeout
            idle_seconds = (now - session.last_activity_at).total_seconds()
            if idle_seconds > settings.LIVE_SESSION_TIMEOUT_SECONDS:
                logger.info("Session %s expired after %.1fs idle.", session_id, idle_seconds)
                await self.stop_session(session_id, user_id, status_label="expired")
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="Live session has expired due to inactivity.",
                )

            session.last_activity_at = now
            return session

        # Not in memory: check database
        doc = await self.sessions_coll.find_one({"_id": session_id, "user_id": user_id})
        if not doc:
            raise EntityNotFoundError("LiveSession", session_id)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Live session is no longer active (status: {doc.get('status', 'stopped')}).",
        )

    def touch_session(self, session_id: str, user_id: str) -> None:
        """Update last activity timestamp for an active session."""
        session = self._active_sessions.get(session_id)
        if session and session.user_id == user_id:
            session.last_activity_at = datetime.now(timezone.utc)

    async def stop_session(
        self,
        session_id: str,
        user_id: str,
        status_label: str = "stopped",
    ) -> LiveSessionStopResponse:
        """
        Stop a live monitoring session, compute aggregate statistics,
        clean up in-memory tracker/analyzers, and update MongoDB.
        """
        now = datetime.now(timezone.utc)
        session = self._active_sessions.pop(session_id, None)

        if session is not None:
            if session.user_id != user_id:
                # Re-insert to avoid dropping state on unauthorized call
                self._active_sessions[session_id] = session
                raise EntityNotFoundError("LiveSession", session_id)

            duration = max(0.0, round(time.time() - session.start_time, 2))
            frames = session.frame_counter
            avg_time = (
                round(sum(session.processing_times) / len(session.processing_times), 2)
                if session.processing_times
                else 0.0
            )
            unique_tracks = len(session.unique_track_ids)
            safety_evs = session.total_safety_events
            ppe_evs = len(session.ppe_analyzer._session_events) if session.ppe_analyzer else 0
            inv_evs = len(session.inventory_analyzer.events) if session.inventory_analyzer else 0

            # Resource cleanup
            try:
                if session.safety_analyzer:
                    session.safety_analyzer.reset()
                if session.ppe_analyzer:
                    session.ppe_analyzer.reset()
                if session.inventory_analyzer:
                    session.inventory_analyzer.reset()
                session.tracker = None
            except Exception as cln_err:
                logger.warning("Error cleaning up live session resources: %s", cln_err)

            # Persist summary in MongoDB
            update_data = {
                "status": status_label,
                "stopped_at": now,
                "duration_seconds": duration,
                "frame_count": frames,
                "average_processing_time_ms": avg_time,
                "unique_tracks": unique_tracks,
                "total_safety_events": safety_evs,
                "total_ppe_events": ppe_evs,
                "total_inventory_events": inv_evs,
            }
            await self.sessions_coll.update_one({"_id": session_id}, {"$set": update_data})

            summary = LiveSessionSummary(
                session_id=session_id,
                status=status_label,
                duration_seconds=duration,
                frames_processed=frames,
                average_processing_time_ms=avg_time,
                unique_tracks=unique_tracks,
                safety_events=safety_evs,
                ppe_violations=ppe_evs,
                inventory_events=inv_evs,
                created_at=session.created_at,
                stopped_at=now,
            )
            logger.info("Live session %s successfully %s.", session_id, status_label)
            return LiveSessionStopResponse(session_id=session_id, status=status_label, summary=summary)

        # Session was not in memory: check DB to see if it exists
        doc = await self.sessions_coll.find_one({"_id": session_id, "user_id": user_id})
        if not doc:
            raise EntityNotFoundError("LiveSession", session_id)

        summary = LiveSessionSummary(
            session_id=session_id,
            status=doc.get("status", "stopped"),
            duration_seconds=doc.get("duration_seconds", 0.0),
            frames_processed=doc.get("frame_count", 0),
            average_processing_time_ms=doc.get("average_processing_time_ms", 0.0),
            unique_tracks=doc.get("unique_tracks", 0),
            safety_events=doc.get("total_safety_events", 0),
            ppe_violations=doc.get("total_ppe_events", 0),
            inventory_events=doc.get("total_inventory_events", 0),
            created_at=doc.get("created_at"),
            stopped_at=doc.get("stopped_at"),
        )
        return LiveSessionStopResponse(session_id=session_id, status=doc.get("status", "stopped"), summary=summary)

    async def get_session_info(self, session_id: str, user_id: str) -> LiveSessionItem:
        """Retrieve current session metadata and status."""
        session = self._active_sessions.get(session_id)
        if session and session.user_id == user_id:
            duration = max(0.0, round(time.time() - session.start_time, 2))
            return LiveSessionItem(
                session_id=session.session_id,
                user_id=session.user_id,
                status=session.status,
                frame_count=session.frame_counter,
                duration_seconds=duration,
                total_safety_events=session.total_safety_events,
                created_at=session.created_at,
                last_activity_at=session.last_activity_at,
                stopped_at=None,
            )

        doc = await self.sessions_coll.find_one({"_id": session_id, "user_id": user_id})
        if not doc:
            raise EntityNotFoundError("LiveSession", session_id)

        return LiveSessionItem(
            session_id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            status=doc.get("status", "stopped"),
            frame_count=doc.get("frame_count", 0),
            duration_seconds=doc.get("duration_seconds", 0.0),
            total_safety_events=doc.get("total_safety_events", 0),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            last_activity_at=doc.get("last_activity_at"),
            stopped_at=doc.get("stopped_at"),
        )

    async def list_user_sessions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> LiveSessionListResponse:
        """List live sessions owned by the authenticated user."""
        query = {"user_id": user_id}
        total = await self.sessions_coll.count_documents(query)
        cursor = self.sessions_coll.find(query).sort("created_at", -1).skip(skip).limit(limit)

        docs = await cursor.to_list(length=limit)
        items = []
        for doc in docs:
            items.append(
                LiveSessionItem(
                    session_id=str(doc["_id"]),
                    user_id=str(doc["user_id"]),
                    status=doc.get("status", "stopped"),
                    frame_count=doc.get("frame_count", 0),
                    duration_seconds=doc.get("duration_seconds", 0.0),
                    total_safety_events=doc.get("total_safety_events", 0),
                    created_at=doc.get("created_at", datetime.now(timezone.utc)),
                    last_activity_at=doc.get("last_activity_at"),
                    stopped_at=doc.get("stopped_at"),
                )
            )

        return LiveSessionListResponse(items=items, total=total)

    async def cleanup_expired_sessions(self) -> int:
        """Sweep in-memory active sessions and expire idle ones."""
        settings = get_settings()
        now = datetime.now(timezone.utc)
        expired_ids = []

        for sid, sess in list(self._active_sessions.items()):
            if (now - sess.last_activity_at).total_seconds() > settings.LIVE_SESSION_TIMEOUT_SECONDS:
                expired_ids.append((sid, sess.user_id))

        for sid, uid in expired_ids:
            try:
                await self.stop_session(sid, uid, status_label="expired")
            except Exception as exp_err:
                logger.warning("Error cleaning up expired session %s: %s", sid, exp_err)

        return len(expired_ids)
