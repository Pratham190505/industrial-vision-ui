import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.collections import CollectionName, get_collection

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.detections = get_collection(CollectionName.DETECTIONS, db)
        self.safety_events = get_collection(CollectionName.SAFETY_EVENTS, db)
        self.inventory = get_collection(CollectionName.INVENTORY_SNAPSHOTS, db)
