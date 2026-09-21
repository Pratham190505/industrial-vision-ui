import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.collections import CollectionName, get_collection

logger = logging.getLogger(__name__)


class SafetyService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.zones_coll = get_collection(CollectionName.SAFETY_ZONES, db)
        self.events_coll = get_collection(CollectionName.SAFETY_EVENTS, db)
