from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.dependencies import get_current_user, get_db_dep
from app.schemas.processing import (
    PaginatedProcessingHistory,
    ProcessingJobItem,
    ProcessingResultResponse,
    ProcessingStatusResponse,
)
from app.services.processing_service import ProcessingService

router = APIRouter(prefix="/processing", tags=["Processing Jobs"])


@router.get(
    "",
    summary="List Processing Jobs",
    description="Retrieve paginated history of video processing jobs for the authenticated user.",
    response_model=PaginatedProcessingHistory,
)
@router.get(
    "/jobs",
    include_in_schema=False,
    response_model=PaginatedProcessingHistory,
)
async def list_processing_jobs(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    status: Optional[str] = Query(None, description="Optional status filter"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = ProcessingService(db)
    items, total = await service.list_user_jobs(
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
        status_filter=status,
    )

    history_items = [
        ProcessingJobItem(
            job_id=str(item["_id"]),
            original_filename=item.get("original_filename", "video.mp4"),
            status=item.get("status", "queued"),
            progress=item.get("progress"),
            processed_frames=item.get("processed_frames", 0),
            total_frames=item.get("total_frames", 0),
            detection_count=item.get("detection_count", 0),
            duration_seconds=item.get("duration_seconds", 0.0),
            created_at=item["created_at"],
            completed_at=item.get("completed_at"),
        )
        for item in items
    ]

    return PaginatedProcessingHistory(
        items=history_items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{job_id}",
    summary="Get Processing Status",
    description="Check status and frame progress of an asynchronous video processing job.",
    response_model=ProcessingStatusResponse,
)
@router.get(
    "/jobs/{job_id}",
    include_in_schema=False,
    response_model=ProcessingStatusResponse,
)
async def get_processing_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = ProcessingService(db)
    job = await service.get_job(job_id=job_id, user_id=current_user["user_id"])

    status_str = job.get("status", "queued")
    message_map = {
        "queued": "Video is queued for processing.",
        "processing": "Processing video.",
        "completed": "Video processing completed successfully.",
        "failed": job.get("error_message") or "Video processing failed.",
        "cancelled": "Video processing was cancelled.",
    }

    return ProcessingStatusResponse(
        job_id=job_id,
        status=status_str,
        progress=job.get("progress"),
        processed_frames=job.get("processed_frames", 0),
        total_frames=job.get("total_frames", 0),
        message=message_map.get(status_str, "Processing video."),
    )


@router.get(
    "/{job_id}/result",
    summary="Get Completed Video Processing Result",
    description="Retrieve processed video statistics, detection counts, and video download URL.",
    response_model=ProcessingResultResponse,
)
async def get_processing_result(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = ProcessingService(db)
    job = await service.get_job(job_id=job_id, user_id=current_user["user_id"])

    job_status = job.get("status", "queued")

    if job_status in ("queued", "processing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video processing is still in progress (status: {job_status}).",
        )

    if job_status == "failed":
        return ProcessingResultResponse(
            job_id=job_id,
            status="failed",
            processed_video_url=None,
            total_frames=job.get("total_frames", 0),
            processed_frames=job.get("processed_frames", 0),
            detection_count=0,
            duration_seconds=job.get("duration_seconds", 0.0),
            error_message=job.get("error_message") or "Video processing failed.",
        )

    return ProcessingResultResponse(
        job_id=job_id,
        status="completed",
        processed_video_url=f"/api/v1/processing/{job_id}/video",
        total_frames=job.get("total_frames", 0),
        processed_frames=job.get("processed_frames", 0),
        detection_count=job.get("detection_count", 0),
        duration_seconds=job.get("duration_seconds", 0.0),
        error_message=None,
    )


@router.get(
    "/{job_id}/video",
    summary="Download or Stream Processed Video",
    description="Securely stream or download the annotated video file.",
)
async def get_processed_video(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = ProcessingService(db)
    safe_path, media_type = await service.get_video_file_path(job_id=job_id, user_id=current_user["user_id"])
    return FileResponse(path=safe_path, media_type=media_type, filename=safe_path.name)
