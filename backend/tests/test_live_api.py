"""
Tests for Live Monitoring API endpoints (/api/v1/live).
"""

import io
from PIL import Image
import pytest


def create_jpeg_bytes(width=320, height=240, color=(120, 150, 180)):
    """Generate in-memory JPEG bytes."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_create_session_unauthenticated(client):
    res = client.post("/api/v1/live/sessions")
    assert res.status_code == 401


def test_create_session_authenticated(client, auth_headers):
    res = client.post("/api/v1/live/sessions", headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert "session_id" in data
    assert data["status"] == "active"


def test_get_session_details(client, auth_headers, other_user_headers):
    # Create session with user 1
    create_res = client.post("/api/v1/live/sessions", headers=auth_headers)
    assert create_res.status_code == 201
    session_id = create_res.json()["session_id"]

    # Retrieve with user 1
    get_res = client.get(f"/api/v1/live/sessions/{session_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == session_id
    assert get_res.json()["status"] == "active"

    # User 2 cannot access user 1's session
    other_res = client.get(f"/api/v1/live/sessions/{session_id}", headers=other_user_headers)
    assert other_res.status_code == 404


def test_list_sessions(client, auth_headers):
    # Create two sessions
    client.post("/api/v1/live/sessions", headers=auth_headers)
    client.post("/api/v1/live/sessions", headers=auth_headers)

    res = client.get("/api/v1/live/sessions", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 2


def test_post_frame_validation(client, auth_headers):
    create_res = client.post("/api/v1/live/sessions", headers=auth_headers)
    session_id = create_res.json()["session_id"]

    # 1. Invalid content type
    bad_type_res = client.post(
        "/api/v1/live/frame",
        headers=auth_headers,
        data={"session_id": session_id},
        files={"frame": ("test.txt", b"plain text content", "text/plain")},
    )
    assert bad_type_res.status_code == 400
    assert "Unsupported image content type" in bad_type_res.json()["detail"]

    # 2. Empty frame
    empty_res = client.post(
        "/api/v1/live/frame",
        headers=auth_headers,
        data={"session_id": session_id},
        files={"frame": ("empty.jpg", b"", "image/jpeg")},
    )
    assert empty_res.status_code == 400
    assert "empty" in empty_res.json()["detail"].lower()

    # 3. Oversized frame (> 2MB)
    huge_payload = b"x" * (2 * 1024 * 1024 + 1024)
    oversized_res = client.post(
        "/api/v1/live/frame",
        headers=auth_headers,
        data={"session_id": session_id},
        files={"frame": ("large.jpg", huge_payload, "image/jpeg")},
    )
    assert oversized_res.status_code == 413
    assert "exceeds the maximum" in oversized_res.json()["detail"]


def test_post_frame_success(client, auth_headers):
    create_res = client.post("/api/v1/live/sessions", headers=auth_headers)
    session_id = create_res.json()["session_id"]

    jpeg_bytes = create_jpeg_bytes(640, 480)
    frame_res = client.post(
        "/api/v1/live/frame",
        headers=auth_headers,
        data={"session_id": session_id},
        files={"frame": ("frame1.jpg", jpeg_bytes, "image/jpeg")},
    )

    assert frame_res.status_code == 200
    data = frame_res.json()
    assert data["session_id"] == session_id
    assert data["frame_number"] == 1
    assert data["frame_width"] == 640
    assert data["frame_height"] == 480
    assert "objects" in data
    assert "safety" in data
    assert "inventory" in data
    assert "ppe" in data
    assert data["processing_time_ms"] >= 0


def test_stop_session(client, auth_headers):
    create_res = client.post("/api/v1/live/sessions", headers=auth_headers)
    session_id = create_res.json()["session_id"]

    stop_res = client.post(f"/api/v1/live/sessions/{session_id}/stop", headers=auth_headers)
    assert stop_res.status_code == 200
    data = stop_res.json()
    assert data["session_id"] == session_id
    assert data["status"] == "stopped"
    assert "summary" in data
    assert data["summary"]["status"] == "stopped"

    # Subsequent frame to stopped session should fail with 400
    jpeg_bytes = create_jpeg_bytes()
    after_stop_res = client.post(
        "/api/v1/live/frame",
        headers=auth_headers,
        data={"session_id": session_id},
        files={"frame": ("frame.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert after_stop_res.status_code == 400
    assert "no longer active" in after_stop_res.json()["detail"]
