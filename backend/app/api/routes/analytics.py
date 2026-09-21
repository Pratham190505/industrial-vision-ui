from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["Dashboard Analytics"])


@router.get("/overview")
async def get_analytics_overview():
    """
    Get dashboard KPI and analytics overview for frontend.
    TODO: Implementation in Analytics module.
    """
    return {
        "active_cameras": 0,
        "total_detections_today": 0,
        "active_safety_alerts": 0,
        "inventory_total_items": 0,
    }
