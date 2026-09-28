"""
Pydantic schemas for Safety Monitoring, Restricted Zones, and Collision Risk.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SafetySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyEventType(str, Enum):
    RESTRICTED_ZONE_VIOLATION = "restricted_zone_violation"
    PROXIMITY_WARNING = "proximity_warning"
    COLLISION_RISK = "collision_risk"
    PPE_VIOLATION = "ppe_violation"
    HELMET_MISSING = "helmet_missing"
    VEST_MISSING = "vest_missing"


# -----------------------------------------------------------------------------
# Safety Zone Schemas
# -----------------------------------------------------------------------------

class SafetyZoneBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable zone label")
    zone_type: str = Field(default="restricted", description="Zone type identifier")
    polygon: List[List[float]] = Field(
        ...,
        description="List of [x, y] coordinates defining polygon vertices (min 3 points)",
    )
    enabled: bool = Field(default=True, description="Whether zone is actively monitored")

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Zone name cannot be empty or only whitespace.")
        return clean

    @field_validator("zone_type")
    @classmethod
    def validate_zone_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("restricted",):
            raise ValueError(f"Unsupported zone_type '{v}'. Supported types: ['restricted']")
        return clean

    @field_validator("polygon")
    @classmethod
    def validate_polygon_geometry(cls, v: List[List[float]]) -> List[List[float]]:
        if not isinstance(v, list) or len(v) < 3:
            raise ValueError("Polygon must contain at least 3 coordinate vertices.")
        cleaned = []
        for idx, pt in enumerate(v):
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise ValueError(f"Vertex {idx} must be a 2D coordinate [x, y].")
            try:
                x = float(pt[0])
                y = float(pt[1])
            except (ValueError, TypeError):
                raise ValueError(f"Vertex {idx} coordinates must be numeric.")
            if x < 0 or y < 0:
                raise ValueError(f"Vertex {idx} coordinates must be non-negative: [{x}, {y}]")
            cleaned.append([x, y])
        return cleaned


class SafetyZoneCreate(SafetyZoneBase):
    pass


class SafetyZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    zone_type: Optional[str] = None
    polygon: Optional[List[List[float]]] = None
    enabled: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("Zone name cannot be empty.")
            return clean
        return v

    @field_validator("zone_type")
    @classmethod
    def validate_zone_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().lower()
            if clean not in ("restricted",):
                raise ValueError(f"Unsupported zone_type '{v}'. Supported: ['restricted']")
            return clean
        return v

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, v: Optional[List[List[float]]]) -> Optional[List[List[float]]]:
        if v is not None:
            return SafetyZoneBase.validate_polygon_geometry(v)
        return v


class SafetyZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zone_id: str
    user_id: str
    name: str
    zone_type: str
    polygon: List[List[float]]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class SafetyZoneList(BaseModel):
    items: List[SafetyZoneResponse]
    total: int


# -----------------------------------------------------------------------------
# Safety Event Schemas
# -----------------------------------------------------------------------------

class SafetyEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    job_id: str
    user_id: Optional[str] = None
    event_type: str
    severity: str
    track_ids: List[int] = Field(default_factory=list)
    zone_id: Optional[str] = None
    distance: Optional[float] = None
    frame_number: int
    timestamp_seconds: float
    message: str
    created_at: datetime


class SafetyEventList(BaseModel):
    items: List[SafetyEvent]
    total: int
    skip: int = 0
    limit: int = 50


# -----------------------------------------------------------------------------
# Safety Summary Schemas
# -----------------------------------------------------------------------------

class SafetySummary(BaseModel):
    """Aggregate safety monitoring statistics for a video processing job."""
    enabled: bool = True
    total_events: int = 0
    restricted_zone_violations: int = 0
    proximity_warnings: int = 0
    collision_risk_events: int = 0
    severity_counts: Dict[str, int] = Field(
        default_factory=lambda: {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
        }
    )
