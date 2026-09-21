import io
from fastapi.testclient import TestClient


def test_unauthenticated_upload_rejected(client: TestClient, sample_image_bytes):
    response = client.post(
        "/api/v1/inputs/image",
        files={"file": ("warehouse.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert response.status_code == 401
    assert "authentication_error" in response.json()["error_type"]


def test_valid_jpeg_upload(client: TestClient, auth_headers, sample_image_bytes):
    response = client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("warehouse_aisle_1.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert data["status"] in ("completed", "processing")
    assert data["image_width"] == 640
    assert data["image_height"] == 480
    assert data["original_image_url"].startswith("/api/v1/inputs/image/")
    assert data["annotated_image_url"].endswith("/annotated")


def test_valid_png_upload(client: TestClient, auth_headers, sample_png_bytes):
    response = client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("forklift_zone.png", sample_png_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["image_width"] == 320
    assert data["image_height"] == 240
    assert data["status"] == "completed"


def test_unsupported_extension_rejected(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("report.pdf", b"%PDF-1.4 dummy content", "application/pdf")},
    )
    assert response.status_code == 400
    assert "file_validation_error" in response.json()["error_type"]


def test_empty_file_rejected(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_corrupted_image_rejected(client: TestClient, auth_headers):
    corrupt_bytes = b"This is plain text pretending to be an image file."
    response = client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "valid image" in response.json()["detail"].lower() or "corrupted" in response.json()["detail"].lower()


def test_oversized_file_rejected(client: TestClient, auth_headers):
    # 11 MB of zero bytes (exceeds 10 MB limit)
    large_bytes = b"0" * (11 * 1024 * 1024)
    response = client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("huge.jpg", large_bytes, "image/jpeg")},
    )
    assert response.status_code == 413
    assert "file_size_exceeded" in response.json()["error_type"]
