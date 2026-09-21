from fastapi.testclient import TestClient


def test_get_image_analysis_success(client: TestClient, auth_headers, sample_image_bytes):
    # 1. Upload an image
    upload_res = client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("warehouse_aisle_3.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert upload_res.status_code == 200
    analysis_id = upload_res.json()["analysis_id"]

    # 2. Retrieve analysis by ID
    get_res = client.get(f"/api/v1/inputs/image/{analysis_id}", headers=auth_headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["analysis_id"] == analysis_id
    assert data["status"] in ("completed", "processing")
    assert data["image_width"] == 640
    assert data["image_height"] == 480


def test_get_image_analysis_other_user_rejected(
    client: TestClient, auth_headers, other_user_headers, sample_image_bytes
):
    # User 1 uploads
    upload_res = client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("restricted_zone.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert upload_res.status_code == 200
    analysis_id = upload_res.json()["analysis_id"]

    # User 2 attempts to retrieve User 1's analysis -> 404 Not Found
    get_res = client.get(f"/api/v1/inputs/image/{analysis_id}", headers=other_user_headers)
    assert get_res.status_code == 404
    assert "entity_not_found" in get_res.json()["error_type"]


def test_get_image_files_original_and_annotated(
    client: TestClient, auth_headers, other_user_headers, sample_image_bytes
):
    # Upload image
    upload_res = client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("loading_dock.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert upload_res.status_code == 200
    analysis_id = upload_res.json()["analysis_id"]

    # Owner downloads original
    orig_res = client.get(f"/api/v1/inputs/image/{analysis_id}/original", headers=auth_headers)
    assert orig_res.status_code == 200
    assert orig_res.headers["content-type"] in ("image/jpeg", "image/jpg")
    assert len(orig_res.content) > 0

    # Owner downloads annotated
    annotated_res = client.get(f"/api/v1/inputs/image/{analysis_id}/annotated", headers=auth_headers)
    assert annotated_res.status_code == 200
    assert annotated_res.headers["content-type"] in ("image/jpeg", "image/jpg")
    assert len(annotated_res.content) > 0

    # Other user cannot download either file -> 404
    other_orig = client.get(f"/api/v1/inputs/image/{analysis_id}/original", headers=other_user_headers)
    assert other_orig.status_code == 404

    other_annot = client.get(f"/api/v1/inputs/image/{analysis_id}/annotated", headers=other_user_headers)
    assert other_annot.status_code == 404


def test_list_user_images_history(client: TestClient, auth_headers, sample_image_bytes):
    # Upload an image to ensure at least one exists
    client.post(
        "/api/v1/inputs/image",
        headers=auth_headers,
        files={"file": ("history_item.jpg", sample_image_bytes, "image/jpeg")},
    )

    response = client.get("/api/v1/inputs/images?skip=0&limit=10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["skip"] == 0
    assert data["limit"] == 10
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    first_item = data["items"][0]
    assert "analysis_id" in first_item
    assert "original_image_url" in first_item
    assert "created_at" in first_item


def test_missing_analysis_not_found(client: TestClient, auth_headers):
    response = client.get("/api/v1/inputs/image/non_existent_uuid_9999", headers=auth_headers)
    assert response.status_code == 404
    assert "entity_not_found" in response.json()["error_type"]
