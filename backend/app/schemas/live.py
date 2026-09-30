"""
Live webcam monitoring Pydantic schemas.

Defines data models for live frame streaming, tracked objects,
safety/PPE/inventory real-time analysis, session lifecycle, and summaries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LiveBBox(BaseModel):
    """Bounding box pixel coordinates in frame space."""
    x1: float
    y1: float
    x2: float
    y2: float


class LiveCenter(BaseModel):
    """Centre point coordinates of a tracked object."""
    x: float
    y: float


class LiveTrackedObject(BaseModel):
    """Individual tracked object identified in a live frame."""
    track_id: int
    class_name: str
    confidence: float
    bbox: LiveBBox
    center: LiveCenter


class LiveSafetyResult(BaseModel):
    """Safety evaluation results for the current live frame."""
    events: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "normal"
    error: Optional[str] = None


class LivePPEResult(BaseModel):
    """PPE compliance evaluation for workers in the current live frame."""
    enabled: bool = True
    available: bool = False
    workers: List[Dict[str, Any]] = Field(default_factory=list)
    violations_count: int = 0
    error: Optional[str] = None


class LiveInventoryResult(BaseModel):
    """Inventory count evaluation for the current live frame."""
    enabled: bool = True
    available: bool = True
    counts: Dict[str, int] = Field(default_factory=dict)
    unique_counts: Dict[str, int] = Field(default_factory=dict)
    error: Optional[str] = None


class LiveFrameResponse(BaseModel):
    """Real-time computer vision analysis payload returned for each live frame."""
    session_id: str
    frame_number: int
    processing_time_ms: float
    frame_width: int
    frame_height: int
    objects: List[LiveTrackedObject] = Field(default_factory=list)
    safety: LiveSafetyResult = Field(default_factory=LiveSafetyResult)
    ppe: LivePPEResult = Field(default_factory=LivePPEResult)
    inventory: LiveInventoryResult = Field(default_factory=LiveInventoryResult)


class LiveSessionSummary(BaseModel):
    """Cumulative summary generated upon stopping a live monitoring session."""
    session_id: str
    status: str = "stopped"
    duration_seconds: float = 0.0
    frames_processed: int = 0
    average_processing_time_ms: float = 0.0
    unique_tracks: int = 0
    safety_events: int = 0
    ppe_violations: int = 0
    inventory_events: int = 0
    created_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


class LiveSessionCreateResponse(BaseModel):
    """Response returned upon creating a new live monitoring session."""
    session_id: str
    status: str = "active"
    created_at: datetime


class LiveSessionStopResponse(BaseModel):
    """Response returned upon stopping a live monitoring session."""
    session_id: str
    status: str = "stopped"
    summary: Optional[LiveSessionSummary] = None


class LiveSessionItem(BaseModel):
    """Brief metadata representing an active or past live monitoring session."""
    model_config = ConfigDict(populate_by_name=True)

    session_id: str
    user_id: str
    status: str
    frame_count: int = 0
    duration_seconds: float = 0.0
    total_safety_events: int = 0
    created_at: datetime
    last_activity_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


class LiveSessionListResponse(BaseModel):
    """List of live sessions for the authenticated user."""
    items: List[LiveSessionItem] = Field(default_factory=list)
    total: int = 0
