import asyncio
from datetime import datetime, timezone
import pytest


def _run_async(coro):
    """Safely execute an async coroutine in sync test code."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _seed_job_with_inventory(db, job_id, user_id, inv_data=None):
    doc = {
        "_id": job_id,
        "user_id": user_id,
        "status": "completed",
        "original_filename": "inventory_test.mp4",
        "processed_filename": "inventory_test_processed.mp4",
        "original_path": "uploads/videos/inventory_test.mp4",
        "total_frames": 300,
        "processed_frames": 300,
        "detection_count": 50,
        "duration_seconds": 10.0,
        "created_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }
    if inv_data is not None:
        doc["inventory"] = inv_data

    await db["processing_jobs"].insert_one(doc)


class TestInventoryAPI:

    def test_auth_required_for_all_endpoints(self, client):
        assert client.get("/api/v1/inventory/job_123").status_code in [401, 403]
        assert client.get("/api/v1/inventory/job_123/snapshots").status_code in [401, 403]
        assert client.get("/api/v1/inventory/job_123/events").status_code in [401, 403]
        assert client.get("/api/v1/inventory/events").status_code in [401, 403]

    def test_get_inventory_summary_success(self, client, auth_headers, mock_mongodb, test_user):
        import asyncio
        _run_async(
            _seed_job_with_inventory(
                mock_mongodb,
                "job_inv_api_1",
                test_user["user_id"],
                inv_data={
                    "enabled": True,
                    "available_classes": ["box", "pallet"],
                    "unavailable_classes": ["crate"],
                    "counts": {
                        "box": {
                            "current_visible_count": 8,
                            "max_visible_count": 12,
                            "min_visible_count": 2,
                            "unique_track_count": 15,
                            "frames_with_inventory": 250,
                            "average_visible_count": 7.4,
                        }
                    },
                    "total_inventory_events": 3,
                },
            )
        )

        resp = client.get("/api/v1/inventory/job_inv_api_1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert "box" in data["available_classes"]
        assert "crate" in data["unavailable_classes"]
        assert data["counts"]["box"]["current_visible_count"] == 8
        assert data["counts"]["box"]["unique_track_count"] == 15
        assert data["total_inventory_events"] == 3

    def test_get_inventory_summary_forbidden_other_user(self, client, auth_headers, mock_mongodb):
        import asyncio
        _run_async(
            _seed_job_with_inventory(mock_mongodb, "job_other_user", "another_user_id", inv_data={"enabled": True})
        )

        resp = client.get("/api/v1/inventory/job_other_user", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_inventory_snapshots_endpoint(self, client, auth_headers, mock_mongodb, test_user):
        import asyncio
        _run_async(
            _seed_job_with_inventory(mock_mongodb, "job_snap_api", test_user["user_id"])
        )

        # Seed snapshots
        async def seed_snaps():
            coll = mock_mongodb["inventory_snapshots"]
            for i in range(5):
                await coll.insert_one({
                    "_id": f"snap_{i}",
                    "job_id": "job_snap_api",
                    "user_id": test_user["user_id"],
                    "timestamp_seconds": float(i * 10),
                    "frame_number": i * 300,
                    "counts": {"box": i + 2},
                    "created_at": datetime.now(timezone.utc),
                })
        _run_async(seed_snaps())

        resp = client.get("/api/v1/inventory/job_snap_api/snapshots?skip=0&limit=3", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "job_snap_api"
        assert data["total"] == 5
        assert len(data["snapshots"]) == 3
        assert data["snapshots"][0]["counts"]["box"] == 2

    def test_get_job_events_endpoint(self, client, auth_headers, mock_mongodb, test_user):
        import asyncio
        _run_async(
            _seed_job_with_inventory(mock_mongodb, "job_events_api", test_user["user_id"])
        )

        async def seed_events():
            coll = mock_mongodb["inventory_events"]
            await coll.insert_one({
                "_id": "ev_1",
                "job_id": "job_events_api",
                "user_id": test_user["user_id"],
                "event_type": "inventory_count_change",
                "class_name": "box",
                "previous_count": 2,
                "current_count": 5,
                "change": 3,
                "frame_number": 300,
                "timestamp_seconds": 10.0,
                "message": "Observed visible box count increased by 3.",
                "created_at": datetime.now(timezone.utc),
            })
            await coll.insert_one({
                "_id": "ev_2",
                "job_id": "job_events_api",
                "user_id": test_user["user_id"],
                "event_type": "inventory_low_stock",
                "class_name": "pallet",
                "current_count": 1,
                "threshold": 2,
                "frame_number": 600,
                "timestamp_seconds": 20.0,
                "message": "Observed visible pallet count is below threshold.",
                "created_at": datetime.now(timezone.utc),
            })
        _run_async(seed_events())

        # All events for job
        resp = client.get("/api/v1/inventory/job_events_api/events", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

        # Filter by class_name
        resp_filtered = client.get("/api/v1/inventory/job_events_api/events?class_name=pallet", headers=auth_headers)
        assert resp_filtered.status_code == 200
        assert resp_filtered.json()["total"] == 1
        assert resp_filtered.json()["events"][0]["class_name"] == "pallet"

    def test_get_user_events_endpoint(self, client, auth_headers, mock_mongodb, test_user):
        resp = client.get("/api/v1/inventory/events", headers=auth_headers)
        assert resp.status_code == 200
        assert "events" in resp.json()

    def test_processing_result_includes_inventory(self, client, auth_headers, mock_mongodb, test_user):
        import asyncio
        _run_async(
            _seed_job_with_inventory(
                mock_mongodb,
                "job_result_inv",
                test_user["user_id"],
                inv_data={
                    "enabled": True,
                    "available_classes": ["box"],
                    "unavailable_classes": ["pallet"],
                    "counts": {
                        "box": {
                            "current_visible_count": 5,
                            "max_visible_count": 5,
                            "min_visible_count": 5,
                            "unique_track_count": 5,
                            "frames_with_inventory": 100,
                            "average_visible_count": 5.0,
                        }
                    },
                    "total_inventory_events": 1,
                },
            )
        )

        resp = client.get("/api/v1/processing/job_result_inv/result", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "inventory" in data
        assert data["inventory"] is not None
        assert data["inventory"]["enabled"] is True
        assert data["inventory"]["available_classes"] == ["box"]
