from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    class_id: int
    class_name: str
    track_id: Optional[int] = None


class DetectionResult(BaseModel):
    media_id: str
    counts_by_class: Dict[str, int] = {}
    boxes: List[BoundingBox] = []
    annotated_media_url: Optional[str] = None
    inference_time_ms: float = 0.0
    image_width: int = 0
    image_height: int = 0
