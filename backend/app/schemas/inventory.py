"""
Inventory monitoring Pydantic schemas.

Defines data models for inventory counting, tracking statistics,
periodic snapshots, count changes, low-stock events, and API responses.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InventoryObject(BaseModel):
    """A tracked object identified as inventory in a frame."""
    track_id: int
    class_name: str
    confidence: float
    bbox: Optional[List[float]] = None


class InventoryCount(BaseModel):
    """Summary of visible and unique counts for a specific class."""
    class_name: str
    visible_count: int
    unique_track_count: int


class InventoryClassStats(BaseModel):
    """Detailed cumulative statistics for an inventory class across a video."""
    current_visible_count: int = 0
    max_visible_count: int = 0
    min_visible_count: int = 0
    unique_track_count: int = 0
    frames_with_inventory: int = 0
    average_visible_count: float = 0.0
    first_seen_frame: Optional[int] = None
    last_seen_frame: Optional[int] = None


class InventorySnapshot(BaseModel):
    """Periodic record of visible inventory counts at a given video timestamp."""
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    job_id: str
    user_id: str
    timestamp_seconds: float
    frame_number: int
    counts: Dict[str, int] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class InventoryEvent(BaseModel):
    """Domain event representing count change or low-stock warning."""
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    job_id: str
    user_id: str
    event_type: str  # "inventory_count_change", "inventory_low_stock"
    class_name: str
    previous_count: Optional[int] = None
    current_count: int
    change: Optional[int] = None
    threshold: Optional[int] = None
    frame_number: int
    timestamp_seconds: float
    message: str
    created_at: Optional[datetime] = None


class InventorySummary(BaseModel):
    """Overall inventory monitoring summary for a video processing session."""
    enabled: bool = False
    available_classes: List[str] = Field(default_factory=list)
    unavailable_classes: List[str] = Field(default_factory=list)
    reason: Optional[str] = None
    counts: Dict[str, InventoryClassStats] = Field(default_factory=dict)
    total_inventory_events: int = 0


class InventoryHistoryResponse(BaseModel):
    """Paginated response containing periodic inventory snapshots for a job."""
    job_id: str
    snapshots: List[InventorySnapshot] = Field(default_factory=list)
    total: int = 0
    skip: int = 0
    limit: int = 50


class InventoryEventListResponse(BaseModel):
    """Paginated list of inventory events."""
    events: List[InventoryEvent] = Field(default_factory=list)
    total: int = 0
    skip: int = 0
    limit: int = 50
