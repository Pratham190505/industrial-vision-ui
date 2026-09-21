from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
from app.schemas.detection import BoundingBox


class MediaUploadResponse(BaseModel):
    file_id: str
    filename: str
    original_filename: str
    file_type: str
    size_bytes: int
    storage_path: str
    created_at: datetime


class ImageAnalysisResponse(BaseModel):
    analysis_id: str
    status: str  # completed, processing, failed
    original_image_url: str
    annotated_image_url: Optional[str] = None
    image_width: int
    image_height: int
    detection_count: int
    detections: List[BoundingBox] = []
    counts_by_class: Dict[str, int] = {}
    model_name: str
    inference_time_ms: float
    created_at: datetime
    error_message: Optional[str] = None


class ImageHistoryItem(BaseModel):
    analysis_id: str
    status: str
    detection_count: int
    original_image_url: str
    annotated_image_url: Optional[str] = None
    created_at: datetime


class ImageHistoryResponse(BaseModel):
    items: List[ImageHistoryItem]
    total: int
    skip: int
    limit: int
