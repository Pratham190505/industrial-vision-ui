"""
Live Webcam Monitoring API routes.

Provides endpoints for managing real-time monitoring sessions,
submitting video frames from browser webcams, and retrieving live metrics.
"""

import logging
from typing import Optional
import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import numpy as np

from app.api.dependencies import get_current_user, get_db_dep
from app.core.config import get_settings
from app.schemas.live import (
    LiveFrameResponse,
    LiveSessionCreateResponse,
    LiveSessionItem,
    LiveSessionListResponse,
    LiveSessionStopResponse,
)
from app.services.live_session_service import LiveSessionService
from app.services.safety_service import SafetyService
from app.vision.live_camera_pipeline import LiveCameraPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["Live Monitoring"])
_pipeline = LiveCameraPipeline()


# -----------------------------------------------------------------------------
# Session Management Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/sessions",
    summary="Create Live Monitoring Session",
    description="Initialize a new live monitoring session with dedicated tracking state.",
    status_code=status.HTTP_201_CREATED,
    response_model=LiveSessionCreateResponse,
)
async def create_live_session(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = LiveSessionService(db)
    return await service.create_session(user_id=current_user["user_id"])


@router.get(
    "/sessions",
    summary="List User Live Sessions",
    description="Retrieve live monitoring sessions created by the authenticated user.",
    response_model=LiveSessionListResponse,
)
async def list_live_sessions(
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = LiveSessionService(db)
    return await service.list_user_sessions(user_id=current_user["user_id"], skip=skip, limit=limit)


@router.get(
    "/sessions/{session_id}",
    summary="Get Live Session Details",
    description="Retrieve status and metadata for a specific live session.",
    response_model=LiveSessionItem,
)
async def get_live_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = LiveSessionService(db)
    return await service.get_session_info(session_id=session_id, user_id=current_user["user_id"])


@router.post(
    "/sessions/{session_id}/stop",
    summary="Stop Live Monitoring Session",
    description="Terminate an active live session, release tracker resources, and record final summary.",
    response_model=LiveSessionStopResponse,
)
async def stop_live_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    service = LiveSessionService(db)
    return await service.stop_session(session_id=session_id, user_id=current_user["user_id"])


# -----------------------------------------------------------------------------
# Live Frame Processing Endpoint
# -----------------------------------------------------------------------------

@router.post(
    "/frame",
    summary="Process Live Webcam Frame",
    description="Process an individual sampled webcam frame with YOLO tracking, safety, PPE, and inventory checks.",
    response_model=LiveFrameResponse,
)
async def process_live_frame(
    session_id: str = Form(..., description="ID of the active live session"),
    frame: UploadFile = File(..., description="JPEG or WebP webcam frame"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
):
    settings = get_settings()
    user_id = current_user["user_id"]
    service = LiveSessionService(db)

    # 1. Validate session and ownership
    session_state = await service.get_session(session_id=session_id, user_id=user_id)

    # 2. Validate MIME content type
    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    content_type = (frame.content_type or "").lower()
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image content type '{content_type}'. Must be one of: {sorted(allowed_types)}.",
        )

    # 3. Read image bytes and validate size limit (<= 2MB)
    contents = await frame.read()
    if len(contents) > settings.max_live_frame_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Frame size ({len(contents)} bytes) exceeds the maximum allowed limit of {settings.MAX_LIVE_FRAME_SIZE_MB} MB.",
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded frame is empty.",
        )

    # 4. Decode image buffer
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenCV could not decode the uploaded frame. File may be corrupted.",
        )

    # 5. Process frame through live pipeline
    result = _pipeline.process_frame(image, session_state)

    # 6. Persist any new safety events with session_id
    safety_events = result.get("safety", {}).get("events", [])
    if safety_events:
        try:
            safety_service = SafetyService(db)
            await safety_service.persist_events(
                events=safety_events,
                job_id=session_id,
                user_id=user_id,
                session_id=session_id,
            )
        except Exception as ev_err:
            logger.warning("Could not persist live safety events for session %s: %s", session_id, ev_err)

    return result
