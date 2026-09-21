from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.core.database import check_database_health

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    summary="Application Health Check",
    description="Check whether the WarehouseVision AI API service is online and healthy.",
    status_code=status.HTTP_200_OK,
)
async def check_api_health():
    settings = get_settings()
    return {
        "status": "healthy",
        "service": f"{settings.APP_NAME} API",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
    }


@router.get(
    "/database",
    summary="Database Connectivity Check",
    description="Check whether the MongoDB persistence layer is reachable.",
)
async def check_mongo_health():
    is_connected = await check_database_health()
    if is_connected:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "database": "connected"},
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "degraded", "database": "disconnected"},
    )
