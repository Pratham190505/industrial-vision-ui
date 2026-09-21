from enum import Enum
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from app.core.database import get_database


class CollectionName(str, Enum):
    """Names of all persistent MongoDB collections in WarehouseVision AI."""

    USERS = "users"
    INPUT_SESSIONS = "input_sessions"
    IMAGES = "images"
    VIDEOS = "videos"
    PROCESSING_JOBS = "processing_jobs"
    DETECTIONS = "detections"
    CAMERAS = "cameras"
    SAFETY_ZONES = "safety_zones"
    SAFETY_EVENTS = "safety_events"
    INVENTORY_SNAPSHOTS = "inventory_snapshots"
    ALERTS = "alerts"
    REPORTS = "reports"


def get_collection(
    name: CollectionName,
    database: AsyncIOMotorDatabase | None = None,
) -> AsyncIOMotorCollection:
    """
    Retrieve a typed collection reference from the provided or default database.
    """
    db = database if database is not None else get_database()
    return db[name.value]
