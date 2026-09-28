"""
Safety API Routes — endpoints for safety events, summaries, restricted zones, and PPE.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_current_user, get_db_dep
from app.schemas.safety import (
    SafetyEvent,
    SafetyEventList,
    SafetySummary,
    SafetyZoneCreate,
    SafetyZoneList,
    SafetyZoneResponse,
    SafetyZoneUpdate,
)
from app.schemas.ppe import PPESummary, PPEWorkerComplianceList
from app.services.safety_service import SafetyService
from app.services.ppe_service import PPEService

router = APIRouter(prefix="/safety", tags=["Safety Monitoring"])


# -----------------------------------------------------------------------------
# Safety Events Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/events",
    summary="List Safety Events",
    description="Retrieve safety events for the authenticated user with optional filtering.",
    response_model=SafetyEventList,
)
async def list_safety_events(
    job_id: Optional[str] = Query(None, description="Filter by video processing job ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, warning, high, critical)"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = SafetyService(db)
    return await service.get_events(
        user_id=current_user["user_id"],
        job_id=job_id,
        event_type=event_type,
        severity=severity,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/events/{event_id}",
    summary="Get Safety Event Details",
    description="Retrieve specific safety event by ID with ownership verification.",
    response_model=SafetyEvent,
)
async def get_safety_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = SafetyService(db)
    return await service.get_event(event_id=event_id, user_id=current_user["user_id"])


@router.get(
    "/summary/{job_id}",
    summary="Get Safety Summary for Job",
    description="Retrieve aggregate safety monitoring statistics for a completed video job.",
    response_model=SafetySummary,
)
async def get_safety_summary(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = SafetyService(db)
    return await service.get_job_summary(job_id=job_id, user_id=current_user["user_id"])


# -----------------------------------------------------------------------------
# Safety Zones Management
# -----------------------------------------------------------------------------

@router.post(
    "/zones",
    summary="Create Restricted Safety Zone",
    description="Define a new polygon-based restricted safety zone.",
    response_model=SafetyZoneResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_safety_zone(
    zone_data: SafetyZoneCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = SafetyService(db)
    return await service.create_zone(user_id=current_user["user_id"], data=zone_data)


@router.get(
    "/zones",
    summary="List Safety Zones",
    description="Retrieve all configured safety zones for the authenticated user.",
    response_model=SafetyZoneList,
)
async def list_safety_zones(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = SafetyService(db)
    return await service.get_zones(user_id=current_user["user_id"])


@router.get(
    "/zones/{zone_id}",
    summary="Get Safety Zone",
    description="Retrieve a specific safety zone by ID.",
    response_model=SafetyZoneResponse,
)
async def get_safety_zone(
    zone_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = SafetyService(db)
    return await service.get_zone(zone_id=zone_id, user_id=current_user["user_id"])


@router.put(
    "/zones/{zone_id}",
    summary="Update Safety Zone",
    description="Update polygon vertices, name, or enabled status of a safety zone.",
    response_model=SafetyZoneResponse,
)
async def update_safety_zone(
    zone_id: str,
    zone_data: SafetyZoneUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = SafetyService(db)
    return await service.update_zone(zone_id=zone_id, user_id=current_user["user_id"], data=zone_data)


@router.delete(
    "/zones/{zone_id}",
    summary="Delete Safety Zone",
    description="Permanently remove a safety zone.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_safety_zone(
    zone_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = SafetyService(db)
    await service.delete_zone(zone_id=zone_id, user_id=current_user["user_id"])
    return None


# -----------------------------------------------------------------------------
# PPE Compliance Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/ppe/{job_id}",
    summary="Get PPE Summary for Job",
    description=(
        "Retrieve PPE compliance summary for a completed video processing job. "
        "Returns worker counts, violation totals, and availability status."
    ),
    response_model=PPESummary,
)
async def get_ppe_summary(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = PPEService(db)
    return await service.get_ppe_summary(job_id=job_id, user_id=current_user["user_id"])


@router.get(
    "/ppe/{job_id}/workers",
    summary="Get PPE Worker Compliance for Job",
    description=(
        "Retrieve per-worker PPE compliance information for a video processing job. "
        "Each worker entry includes detected and missing PPE items."
    ),
    response_model=PPEWorkerComplianceList,
)
async def get_ppe_workers(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = PPEService(db)
    return await service.get_worker_compliance(job_id=job_id, user_id=current_user["user_id"])
