from pathlib import Path
from typing import Optional
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.dependencies import get_current_user, get_db_dep
from app.core.config import get_settings
from app.schemas.input import (
    ImageAnalysisResponse,
    ImageHistoryItem,
    ImageHistoryResponse,
)
from app.schemas.processing import VideoUploadResponse
from app.services.detection_service import DetectionService
from app.services.input_service import InputService
from app.services.processing_service import ProcessingService
from app.utils.file_handler import save_upload_video
from app.workers.processing_worker import ProcessingWorker

router = APIRouter(prefix="/inputs", tags=["Inputs & Media Processing"])


def _format_analysis_response(doc: dict) -> ImageAnalysisResponse:
    analysis_id = str(doc["_id"])
    return ImageAnalysisResponse(
        analysis_id=analysis_id,
        status=doc.get("status", "processing"),
        original_image_url=f"/api/v1/inputs/image/{analysis_id}/original",
        annotated_image_url=(
            f"/api/v1/inputs/image/{analysis_id}/annotated"
            if doc.get("status") == "completed"
            else None
        ),
        image_width=doc.get("image_width", 0),
        image_height=doc.get("image_height", 0),
        detection_count=doc.get("detection_count", 0),
        detections=doc.get("detections", []),
        counts_by_class=doc.get("counts_by_class", {}),
        model_name=doc.get("model_name", "yolo11n.pt"),
        inference_time_ms=doc.get("inference_time_ms", 0.0),
        created_at=doc["created_at"],
        error_message=doc.get("error_message"),
    )


@router.post(
    "/image",
    summary="Upload and Process Image with YOLO",
    description=(
        "Upload an image (JPEG, PNG, WEBP) to perform YOLO object detection. "
        "Draws bounding boxes, persists metadata in MongoDB, and returns structured detections."
    ),
    response_model=ImageAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_and_process_image(
    file: UploadFile = File(..., description="Image file to analyze"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    user_id = current_user["user_id"]
    input_service = InputService(db)
    detection_service = DetectionService(db)

    # 1. Validate and save original upload to disk
    (
        analysis_id,
        stored_filename,
        original_abs_path,
        annotated_filename,
        annotated_abs_path,
        size_bytes,
        width,
        height,
    ) = await input_service.save_uploaded_image(file=file, user_id=user_id)

    # 2. Create initial database record (status: processing)
    await input_service.create_analysis_record(
        analysis_id=analysis_id,
        user_id=user_id,
        original_filename=file.filename or "unknown.jpg",
        stored_filename=stored_filename,
        annotated_filename=annotated_filename,
        width=width,
        height=height,
    )

    # 3. Run YOLO inference and image annotation
    result_doc = await detection_service.process_image_analysis(
        analysis_id=analysis_id,
        original_abs_path=original_abs_path,
        annotated_abs_path=annotated_abs_path,
    )

    return _format_analysis_response(result_doc)


@router.post(
    "/video",
    summary="Upload and Queue Video for Processing",
    description=(
        "Upload a video file (.mp4, .avi, .mov, .mkv, .webm) to perform asynchronous YOLO object detection. "
        "Returns HTTP 202 Accepted with a processing job ID."
    ),
    response_model=VideoUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_and_process_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file to analyze"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    user_id = current_user["user_id"]
    settings = get_settings()

    # 1. Validate and save video to disk, extracting metadata
    stored_filename, safe_destination_path, total_bytes, video_metadata = await save_upload_video(
        file=file,
        destination_directory=settings.upload_videos_path,
        max_bytes=settings.max_video_size_bytes,
    )

    # 2. Create processing job record
    job_id = uuid.uuid4().hex
    processed_filename = f"{Path(stored_filename).stem}-annotated.mp4"

    processing_service = ProcessingService(db)
    await processing_service.create_job(
        job_id=job_id,
        user_id=user_id,
        original_filename=file.filename or "unknown.mp4",
        stored_filename=stored_filename,
        processed_filename=processed_filename,
        video_metadata=video_metadata,
    )

    # 3. Schedule background worker
    worker = ProcessingWorker(db=db)
    background_tasks.add_task(worker.run_job, job_id)

    return VideoUploadResponse(
        job_id=job_id,
        status="queued",
        message="Video uploaded and queued for processing.",
    )


@router.get(
    "/image/{analysis_id}",
    summary="Get Image Analysis Details",
    description="Retrieve detection results, counts, and metadata for a specific image analysis.",
    response_model=ImageAnalysisResponse,
)
async def get_image_analysis(
    analysis_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    input_service = InputService(db)
    doc = await input_service.get_image_analysis(analysis_id, current_user["user_id"])
    return _format_analysis_response(doc)


@router.get(
    "/image/{analysis_id}/original",
    summary="Download Original Uploaded Image",
    description="Securely retrieve the raw uploaded image file for the authenticated owner.",
)
async def get_original_image(
    analysis_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    input_service = InputService(db)
    safe_path, media_type = await input_service.get_image_file_path(
        analysis_id, current_user["user_id"], file_type="original"
    )
    return FileResponse(path=safe_path, media_type=media_type, filename=safe_path.name)


@router.get(
    "/image/{analysis_id}/annotated",
    summary="Download YOLO Annotated Image",
    description="Securely retrieve the processed image with visual bounding boxes.",
)
async def get_annotated_image(
    analysis_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    input_service = InputService(db)
    safe_path, media_type = await input_service.get_image_file_path(
        analysis_id, current_user["user_id"], file_type="annotated"
    )
    return FileResponse(path=safe_path, media_type=media_type, filename=safe_path.name)


@router.get(
    "/images",
    summary="List User Image Analyses History",
    description="Retrieve paginated history of image analyses belonging to the authenticated user.",
    response_model=ImageHistoryResponse,
)
async def list_user_images(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    status: Optional[str] = Query(None, description="Optional status filter"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    input_service = InputService(db)
    items, total = await input_service.list_user_images(
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
        status_filter=status,
    )

    history_items = [
        ImageHistoryItem(
            analysis_id=str(item["_id"]),
            status=item.get("status", "processing"),
            detection_count=item.get("detection_count", 0),
            original_image_url=f"/api/v1/inputs/image/{str(item['_id'])}/original",
            annotated_image_url=(
                f"/api/v1/inputs/image/{str(item['_id'])}/annotated"
                if item.get("status") == "completed"
                else None
            ),
            created_at=item["created_at"],
        )
        for item in items
    ]

    return ImageHistoryResponse(
        items=history_items,
        total=total,
        skip=skip,
        limit=limit,
    )


# Backward-compatible alias for earlier stub
@router.post("/images/upload", include_in_schema=False)
async def upload_image_alias(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    return await upload_and_process_image(file=file, current_user=current_user, db=db)
