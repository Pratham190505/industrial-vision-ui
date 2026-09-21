from fastapi.testclient import TestClient


def test_unauthenticated_video_upload_rejected(client: TestClient, sample_video_bytes):
    response = client.post(
        "/api/v1/inputs/video",
        files={"file": ("warehouse_aisle.mp4", sample_video_bytes, "video/mp4")},
    )
    assert response.status_code == 401
    assert "authentication_error" in response.json()["error_type"]


def test_valid_video_upload_queued(client: TestClient, auth_headers, sample_video_bytes):
    response = client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("loading_dock_cctv.mp4", sample_video_bytes, "video/mp4")},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert "queued for processing" in data["message"].lower()


def test_unsupported_video_extension_rejected(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("report.exe", b"fake binary executable content", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "file_validation_error" in response.json()["error_type"]


def test_empty_video_rejected(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("empty.mp4", b"", "video/mp4")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_corrupted_video_rejected(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("corrupt.mp4", b"not a real video content header", "video/mp4")},
    )
    assert response.status_code == 400
    assert "file_validation_error" in response.json()["error_type"]


def test_oversized_video_rejected(client: TestClient, auth_headers):
    # 201 MB of bytes (exceeds 200 MB limit)
    # Using small streamed generator or size check
    oversized_bytes = b"0" * (201 * 1024 * 1024)
    response = client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("huge.mp4", oversized_bytes, "video/mp4")},
    )
    assert response.status_code == 413
    assert "file_size_exceeded" in response.json()["error_type"]
