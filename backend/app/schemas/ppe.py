"""
Pydantic schemas for PPE (Personal Protective Equipment) compliance monitoring.

Defines detection, worker compliance, and aggregate summary data structures.
No raw Ultralytics objects are exposed through these models.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PPEComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


class PPEDetection(BaseModel):
    """A single PPE item detected in a video frame."""
    class_id: int
    class_name: str
    ppe_category: str = Field(..., description="Normalized PPE category: helmet, vest, gloves, shoes, goggles")
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: Dict[str, float] = Field(
        ...,
        description="Bounding box with keys x1, y1, x2, y2",
    )


class PPEWorkerCompliance(BaseModel):
    """PPE compliance state for a single tracked worker."""
    track_id: int
    required_ppe: List[str] = Field(default_factory=list)
    detected_ppe: List[str] = Field(default_factory=list)
    missing_ppe: List[str] = Field(default_factory=list)
    status: PPEComplianceStatus = PPEComplianceStatus.UNKNOWN


class PPEWorkerComplianceList(BaseModel):
    """List of worker compliance records for a job."""
    items: List[PPEWorkerCompliance]
    total: int = 0


class PPESummary(BaseModel):
    """Aggregate PPE monitoring statistics for a video processing job."""
    enabled: bool = False
    available: bool = False
    reason: Optional[str] = None
    workers_checked: int = 0
    compliant_workers: int = 0
    non_compliant_workers: int = 0
    unknown_workers: int = 0
    helmet_violations: int = 0
    vest_violations: int = 0


class PPEAvailability(BaseModel):
    """Reports whether the PPE subsystem can actually detect PPE classes."""
    enabled: bool = False
    available: bool = False
    reason: Optional[str] = None
    supported_categories: List[str] = Field(default_factory=list)
    model_classes: List[str] = Field(default_factory=list)
