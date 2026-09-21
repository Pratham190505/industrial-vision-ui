from fastapi.testclient import TestClient


def test_unauthenticated_processing_access_rejected(client: TestClient):
    assert client.get("/api/v1/processing/some_job_id").status_code == 401
    assert client.get("/api/v1/processing/some_job_id/result").status_code == 401
    assert client.get("/api/v1/processing/some_job_id/video").status_code == 401
    assert client.get("/api/v1/processing").status_code == 401


def test_cross_user_isolation(client: TestClient, auth_headers, other_user_headers, sample_video_bytes):
    # User 1 uploads video
    upload_res = client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("restricted_zone.mp4", sample_video_bytes, "video/mp4")},
    )
    assert upload_res.status_code == 202
    job_id = upload_res.json()["job_id"]

    # User 2 attempts to get User 1's job status -> 404
    user2_status = client.get(f"/api/v1/processing/{job_id}", headers=other_user_headers)
    assert user2_status.status_code == 404

    # User 2 attempts to get User 1's job result -> 404
    user2_result = client.get(f"/api/v1/processing/{job_id}/result", headers=other_user_headers)
    assert user2_result.status_code == 404

    # User 2 attempts to download User 1's video -> 404
    user2_video = client.get(f"/api/v1/processing/{job_id}/video", headers=other_user_headers)
    assert user2_video.status_code == 404


def test_user_history_isolation(client: TestClient, auth_headers, other_user_headers, sample_video_bytes):
    # User 1 uploads video
    client.post(
        "/api/v1/inputs/video",
        headers=auth_headers,
        files={"file": ("user1_cam.mp4", sample_video_bytes, "video/mp4")},
    )

    # User 2 lists jobs
    user2_history = client.get("/api/v1/processing", headers=other_user_headers)
    assert user2_history.status_code == 200
    # User 2 has not uploaded any videos, so total should be 0
    assert user2_history.json()["total"] == 0
    assert len(user2_history.json()["items"]) == 0
