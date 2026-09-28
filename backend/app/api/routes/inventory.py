"""
Inventory API Routes — endpoints for inventory summaries, periodic snapshots, and events.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_current_user, get_db_dep
from app.schemas.inventory import (
    InventoryEventListResponse,
    InventoryHistoryResponse,
    InventorySummary,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory Monitoring"])


# -----------------------------------------------------------------------------
# User Inventory Events (Must precede /{job_id} to avoid path collision)
# -----------------------------------------------------------------------------

@router.get(
    "/events",
    summary="List Inventory Events",
    description="Retrieve inventory events across all jobs owned by the authenticated user.",
    response_model=InventoryEventListResponse,
)
async def list_user_inventory_events(
    event_type: Optional[str] = Query(None, description="Filter by event type (inventory_count_change, inventory_low_stock)"),
    class_name: Optional[str] = Query(None, description="Filter by inventory object class name"),
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of events to return"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = InventoryService(db)
    return await service.get_user_inventory_events(
        user_id=current_user["user_id"],
        event_type=event_type,
        class_name=class_name,
        skip=skip,
        limit=limit,
    )


# -----------------------------------------------------------------------------
# Job Inventory Summary
# -----------------------------------------------------------------------------

@router.get(
    "/{job_id}",
    summary="Get Job Inventory Summary",
    description="Retrieve cumulative inventory summary and statistics for a specific processing job.",
    response_model=InventorySummary,
)
async def get_job_inventory_summary(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = InventoryService(db)
    return await service.get_inventory_summary(
        job_id=job_id,
        user_id=current_user["user_id"],
    )


# -----------------------------------------------------------------------------
# Job Inventory Snapshots
# -----------------------------------------------------------------------------

@router.get(
    "/{job_id}/snapshots",
    summary="Get Job Inventory Snapshots",
    description="Retrieve periodic inventory snapshots recording visible object counts over time.",
    response_model=InventoryHistoryResponse,
)
async def get_job_inventory_snapshots(
    job_id: str,
    skip: int = Query(0, ge=0, description="Number of snapshots to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of snapshots to return"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = InventoryService(db)
    return await service.get_inventory_snapshots(
        job_id=job_id,
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
    )


# -----------------------------------------------------------------------------
# Job Inventory Events
# -----------------------------------------------------------------------------

@router.get(
    "/{job_id}/events",
    summary="Get Job Inventory Events",
    description="Retrieve inventory events (count changes, low stock) for a specific processing job.",
    response_model=InventoryEventListResponse,
)
async def get_job_inventory_events(
    job_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    class_name: Optional[str] = Query(None, description="Filter by class name"),
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of events to return"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = InventoryService(db)
    return await service.get_job_inventory_events(
        job_id=job_id,
        user_id=current_user["user_id"],
        event_type=event_type,
        class_name=class_name,
        skip=skip,
        limit=limit,
    )
