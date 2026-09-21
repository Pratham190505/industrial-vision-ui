import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MongoDBManager:
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None


db_manager = MongoDBManager()


async def connect_to_mongo() -> None:
    """Initialize MongoDB connection pool on application startup."""
    settings = get_settings()
    logger.info("Initializing MongoDB connection to %s", settings.MONGODB_DATABASE)
    try:
        db_manager.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
        )
        db_manager.database = db_manager.client[settings.MONGODB_DATABASE]
        logger.info("MongoDB client created successfully.")
    except Exception as exc:
        logger.warning("Could not establish immediate connection to MongoDB: %s", exc)


async def close_mongo_connection() -> None:
    """Close MongoDB connection pool on application shutdown."""
    if db_manager.client is not None:
        logger.info("Closing MongoDB connection.")
        db_manager.client.close()
        db_manager.client = None
        db_manager.database = None
        logger.info("MongoDB connection closed.")


def get_client() -> Optional[AsyncIOMotorClient]:
    """Retrieve current AsyncIOMotorClient instance."""
    return db_manager.client


def get_database() -> AsyncIOMotorDatabase:
    """
    Retrieve current AsyncIOMotorDatabase instance.
    Initializes fallback client if called before startup lifecycle.
    """
    if db_manager.database is None:
        settings = get_settings()
        db_manager.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
        )
        db_manager.database = db_manager.client[settings.MONGODB_DATABASE]
    return db_manager.database


async def check_database_health() -> bool:
    """
    Verify MongoDB connectivity by executing a ping command.
    Returns True if reachable, False otherwise without exposing internal exceptions.
    """
    try:
        db = get_database()
        # Ping with short timeout
        await db.command("ping")
        return True
    except Exception as exc:
        logger.warning("MongoDB health check ping failed: %s", exc)
        return False


async def get_db() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency that provides an async database instance.
    """
    return get_database()
