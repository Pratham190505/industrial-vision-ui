from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Point2D(BaseModel):
    x: float
    y: float


class SafetyZoneSchema(BaseModel):
    id: Optional[str] = None
    name: str
    camera_id: str
    polygon: List[Point2D]
    zone_type: str  # danger, warning, walkway
    is_active: bool = True


class SafetyEventSchema(BaseModel):
    id: Optional[str] = None
    camera_id: str
    zone_id: str
    zone_name: str
    person_track_id: Optional[int] = None
    event_type: str  # intrusion, loitering, ppe_missing
    severity: str  # low, medium, high, critical
    timestamp: datetime
