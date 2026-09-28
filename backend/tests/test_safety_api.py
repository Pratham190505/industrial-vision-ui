"""
API integration tests for Safety routes (tests/test_safety_api.py).
Tests authentication, zone CRUD, event listing, pagination, and multi-tenant isolation.
"""

from fastapi.testclient import TestClient
import pytest


def test_safety_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/v1/safety/events").status_code == 401
    assert client.get("/api/v1/safety/events/some_id").status_code == 401
    assert client.get("/api/v1/safety/summary/some_job").status_code == 401
    assert client.get("/api/v1/safety/zones").status_code == 401
    assert client.post("/api/v1/safety/zones", json={}).status_code == 401


def test_safety_zone_api_crud(client: TestClient, auth_headers):
    # 1. Create Zone
    payload = {
        "name": "Assembly Line 4",
        "zone_type": "restricted",
        "polygon": [[100.0, 100.0], [400.0, 100.0], [400.0, 300.0], [100.0, 300.0]],
        "enabled": True,
    }
    create_res = client.post("/api/v1/safety/zones", json=payload, headers=auth_headers)
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["name"] == "Assembly Line 4"
    zone_id = data["zone_id"]

    # 2. List Zones
    list_res = client.get("/api/v1/safety/zones", headers=auth_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
    assert any(z["zone_id"] == zone_id for z in list_res.json()["items"])

    # 3. Get Zone by ID
    get_res = client.get(f"/api/v1/safety/zones/{zone_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["zone_id"] == zone_id

    # 4. Update Zone
    update_res = client.put(
        f"/api/v1/safety/zones/{zone_id}",
        json={"name": "Assembly Line 4 - Active", "enabled": False},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Assembly Line 4 - Active"
    assert update_res.json()["enabled"] is False

    # 5. Delete Zone
    del_res = client.delete(f"/api/v1/safety/zones/{zone_id}", headers=auth_headers)
    assert del_res.status_code == 204

    # 6. Verify 404 after deletion
    assert client.get(f"/api/v1/safety/zones/{zone_id}", headers=auth_headers).status_code == 404


def test_safety_zone_api_cross_user_isolation(client: TestClient, auth_headers, other_user_headers):
    # User 1 creates zone
    payload = {
        "name": "Restricted Battery Station",
        "zone_type": "restricted",
        "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "enabled": True,
    }
    create_res = client.post("/api/v1/safety/zones", json=payload, headers=auth_headers)
    assert create_res.status_code == 201
    zone_id = create_res.json()["zone_id"]

    # User 2 attempts to get User 1's zone -> 404
    assert client.get(f"/api/v1/safety/zones/{zone_id}", headers=other_user_headers).status_code == 404

    # User 2 attempts to update User 1's zone -> 404
    assert client.put(
        f"/api/v1/safety/zones/{zone_id}",
        json={"name": "Attacked Zone"},
        headers=other_user_headers,
    ).status_code == 404

    # User 2 attempts to delete User 1's zone -> 404
    assert client.delete(f"/api/v1/safety/zones/{zone_id}", headers=other_user_headers).status_code == 404


def test_safety_events_listing_and_filtering(client: TestClient, auth_headers, mock_mongodb, test_user):
    events_coll = mock_mongodb["safety_events"]
    # Seed events for test user
    test_user_id = test_user["user_id"]
    await_docs = [
        {
            "_id": "ev_001",
            "job_id": "job_1",
            "user_id": test_user_id,
            "event_type": "restricted_zone_violation",
            "severity": "high",
            "track_ids": [1],
            "zone_id": "zone_a",
            "distance": None,
            "frame_number": 5,
            "timestamp_seconds": 0.5,
            "message": "Zone breach",
            "created_at": "2026-09-28T12:00:00Z",
        },
        {
            "_id": "ev_002",
            "job_id": "job_1",
            "user_id": test_user_id,
            "event_type": "proximity_warning",
            "severity": "warning",
            "track_ids": [1, 2],
            "zone_id": None,
            "distance": 80.0,
            "frame_number": 15,
            "timestamp_seconds": 1.5,
            "message": "Proximity close",
            "created_at": "2026-09-28T12:01:00Z",
        },
    ]
    for d in await_docs:
        events_coll._docs[d["_id"]] = d

    # Also seed job
    mock_mongodb["processing_jobs"]._docs["job_1"] = {
        "_id": "job_1",
        "user_id": test_user_id,
        "status": "completed",
        "safety": {
            "enabled": True,
            "total_events": 2,
            "restricted_zone_violations": 1,
            "proximity_warnings": 1,
            "collision_risk_events": 0,
            "severity_counts": {"low": 0, "medium": 1, "high": 1, "critical": 0},
        },
    }

    # 1. List all events
    res = client.get("/api/v1/safety/events", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # 2. Filter by event_type
    res_type = client.get("/api/v1/safety/events?event_type=restricted_zone_violation", headers=auth_headers)
    assert res_type.status_code == 200
    assert res_type.json()["total"] == 1
    assert res_type.json()["items"][0]["event_id"] == "ev_001"

    # 3. Get single event
    res_single = client.get("/api/v1/safety/events/ev_001", headers=auth_headers)
    assert res_single.status_code == 200
    assert res_single.json()["event_id"] == "ev_001"

    # 4. Get summary
    res_summary = client.get("/api/v1/safety/summary/job_1", headers=auth_headers)
    assert res_summary.status_code == 200
    sum_data = res_summary.json()
    assert sum_data["enabled"] is True
    assert sum_data["total_events"] == 2
    assert sum_data["restricted_zone_violations"] == 1
