import asyncio
import pytest
from fastapi.testclient import TestClient
from app.workers.processing_worker import ProcessingWorker


def test_job_upload_and_status(client: TestClient, auth_headers, sample_video_bytes):
    # 1. Upload video
    upload_res = client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("warehouse_aisle_7.mp4", sample_video_bytes, "video/mp4")},
    )
    assert upload_res.status_code == 202
    job_id = upload_res.json()["job_id"]

    # 2. Check initial status (queued or processing)
    status_res = client.get(f"/api/v1/processing/{job_id}", headers=auth_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] in ("queued", "processing", "completed")


@pytest.mark.anyio
async def test_worker_execution_lifecycle(mock_mongodb, sample_video_path):
    from app.services.processing_service import ProcessingService

    db = mock_mongodb
    service = ProcessingService(db)

    job_id = "test_lifecycle_job"
    user_id = "usr_test_12345"
    metadata = {
        "width": 160,
        "height": 120,
        "fps": 10.0,
        "total_frames": 5,
        "duration_seconds": 0.5,
    }

    # Create job in database
    await service.create_job(
        job_id=job_id,
        user_id=user_id,
        original_filename="aisle.mp4",
        stored_filename=sample_video_path.name,
        processed_filename=f"{sample_video_path.stem}-annotated.mp4",
        video_metadata=metadata,
    )

    # Ensure upload file is in expected directory
    import shutil
    from app.core.config import get_settings
    settings = get_settings()
    dest = settings.upload_videos_path / sample_video_path.name
    shutil.copy(sample_video_path, dest)

    worker = ProcessingWorker(db=db)
    await worker.run_job(job_id)

    updated_job = await service.get_job(job_id, user_id)
    assert updated_job["status"] == "completed"
    assert updated_job["progress"] == 100
    assert updated_job["processed_frames"] == 5


def test_incomplete_job_result_rejected(client: TestClient, auth_headers, sample_video_bytes):
    # Upload video
    upload_res = client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("in_progress.mp4", sample_video_bytes, "video/mp4")},
    )
    job_id = upload_res.json()["job_id"]

    # Result should return 400 if queried before completion
    result_res = client.get(f"/api/v1/processing/{job_id}/result", headers=auth_headers)
    # Status can be completed immediately if worker is fast or 400 if still processing
    if result_res.status_code == 400:
        assert "in progress" in result_res.json()["detail"].lower()
    else:
        assert result_res.status_code == 200
        assert result_res.json()["status"] == "completed"


def test_missing_job_returns_404(client: TestClient, auth_headers):
    res = client.get("/api/v1/processing/non_existent_job_id", headers=auth_headers)
    assert res.status_code == 404
    assert "entity_not_found" in res.json()["error_type"]


def test_list_processing_jobs(client: TestClient, auth_headers, sample_video_bytes):
    client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("history_vid.mp4", sample_video_bytes, "video/mp4")},
    )

    res = client.get("/api/v1/processing?skip=0&limit=10", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
