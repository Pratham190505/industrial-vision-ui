from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class VideoUploadResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: str = "Video uploaded and queued for processing."


class ProcessingStatusResponse(BaseModel):
    job_id: str
    status: str  # queued, processing, completed, failed, cancelled
    progress: Optional[int] = None  # 0 to 100 or None if total_frames unknown
    processed_frames: int = 0
    total_frames: int = 0
    message: str = "Processing video."


class ProcessingResultResponse(BaseModel):
    job_id: str
    status: str
    processed_video_url: Optional[str] = None
    total_frames: int = 0
    processed_frames: int = 0
    detection_count: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


class ProcessingJobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    original_filename: str
    status: str
    progress: Optional[int] = None
    processed_frames: int = 0
    total_frames: int = 0
    detection_count: int = 0
    duration_seconds: float = 0.0
    created_at: datetime
    completed_at: Optional[datetime] = None


class PaginatedProcessingHistory(BaseModel):
    items: List[ProcessingJobItem]
    total: int
    skip: int
    limit: int


# Backward-compatible alias
class ProcessingJobResponse(BaseModel):
    job_id: str
    media_id: Optional[str] = None
    status: str
    progress_percent: float = 0.0
    total_frames: int = 0
    processed_frames: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
