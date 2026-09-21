import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import (
    analytics,
    auth,
    cameras,
    detections,
    health,
    inputs,
    inventory,
    processing,
    safety,
)
from app.core.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.core.exceptions import setup_exception_handlers
from app.utils.file_handler import ensure_storage_directories

# Configure standard structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("warehousevision")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handling startup initializations and graceful shutdowns.
    """
    settings = get_settings()
    logger.info("Starting up %s (env=%s, debug=%s)", settings.APP_NAME, settings.ENVIRONMENT, settings.DEBUG)

    # 1. Ensure all local media storage directories exist
    ensure_storage_directories()
    logger.info("Storage directories validated and ready.")

    # 2. Connect to MongoDB persistence layer
    await connect_to_mongo()
    try:
        from app.core.database import get_database
        from app.services.input_service import InputService
        from app.services.processing_service import ProcessingService
        db_instance = get_database()
        await InputService(db_instance).ensure_indexes()
        await ProcessingService(db_instance).ensure_indexes()
    except Exception as exc:
        logger.warning("Could not initialize collection indexes: %s", exc)

    yield

    # 3. Graceful shutdown
    logger.info("Shutting down %s...", settings.APP_NAME)
    await close_mongo_connection()
    logger.info("Shutdown completed successfully.")


def create_application() -> FastAPI:
    """Application factory configuring middleware, exception handlers, and routing."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "AI-powered warehouse monitoring application backend providing YOLO object detection, "
            "tracking, safety zone alerts, inventory counts, and video analytics."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # Setup custom domain exception handlers
    setup_exception_handlers(app)

    # CORS configuration
    allowed_origins = [settings.FRONTEND_URL]
    if settings.ENVIRONMENT == "development":
        # Allow default Vite dev ports in development mode
        allowed_origins.extend(["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"])
    # Deduplicate while preserving order
    allowed_origins = list(dict.fromkeys(allowed_origins))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1 routers
    v1_prefix = settings.API_V1_STR
    app.include_router(health.router, prefix=v1_prefix)
    app.include_router(auth.router, prefix=v1_prefix)
    app.include_router(inputs.router, prefix=v1_prefix)
    app.include_router(detections.router, prefix=v1_prefix)
    app.include_router(processing.router, prefix=v1_prefix)
    app.include_router(cameras.router, prefix=v1_prefix)
    app.include_router(safety.router, prefix=v1_prefix)
    app.include_router(inventory.router, prefix=v1_prefix)
    app.include_router(analytics.router, prefix=v1_prefix)

    @app.get("/", tags=["Root"])
    async def root():
        """Root status endpoint returning service description and documentation links."""
        return {
            "name": settings.APP_NAME,
            "status": "online",
            "environment": settings.ENVIRONMENT,
            "docs_url": "/docs",
            "health_check": f"{settings.API_V1_STR}/health",
        }

    return app


app = create_application()
