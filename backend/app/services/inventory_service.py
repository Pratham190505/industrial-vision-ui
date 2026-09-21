import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.collections import CollectionName, get_collection

logger = logging.getLogger(__name__)


class InventoryService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = get_collection(CollectionName.INVENTORY_SNAPSHOTS, db)
