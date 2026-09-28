import asyncio
import pytest
from datetime import datetime, timezone


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_job_with_ppe(db, job_id, user_id, ppe_data=None, ppe_workers=None):
    """Insert a processing job with PPE data."""
    doc = {
        "_id": job_id,
        "user_id": user_id,
        "status": "completed",
        "original_filename": "test.mp4",
        "processed_filename": "test_processed.mp4",
        "original_path": "uploads/videos/test.mp4",
        "created_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }
    if ppe_data is not None:
        doc["ppe"] = ppe_data
    if ppe_workers is not None:
        doc["ppe_workers"] = ppe_workers

    coll = db["processing_jobs"]
    await coll.insert_one(doc)


# ---------------------------------------------------------------------------
# GET /api/v1/safety/ppe/{job_id}
# ---------------------------------------------------------------------------

class TestGetPPESummary:

    def test_ppe_summary_success(self, client, auth_headers, mock_mongodb, test_user):
        import asyncio
        _run_async(
            _seed_job_with_ppe(
                mock_mongodb,
                "job_ppe_api_1",
                test_user["user_id"],
                ppe_data={
                    "enabled": True,
                    "available": True,
                    "workers_checked": 5,
                    "compliant_workers": 3,
                    "non_compliant_workers": 2,
                    "unknown_workers": 0,
                    "helmet_violations": 1,
                    "vest_violations": 1,
                },
            )
        )

        resp = client.get("/api/v1/safety/ppe/job_ppe_api_1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["available"] is True
        assert data["workers_checked"] == 5
        assert data["compliant_workers"] == 3
        assert data["non_compliant_workers"] == 2
        assert data["helmet_violations"] == 1

    def test_ppe_summary_no_auth(self, client):
        resp = client.get("/api/v1/safety/ppe/some_job")
        assert resp.status_code == 401

    def test_ppe_summary_wrong_user(self, client, other_user_headers, mock_mongodb, test_user):
        import asyncio
        _run_async(
            _seed_job_with_ppe(
                mock_mongodb,
                "job_other_ppe",
                test_user["user_id"],  # owned by test_user
                ppe_data={"enabled": True, "available": True},
            )
        )

        # Access with other_user
        resp = client.get("/api/v1/safety/ppe/job_other_ppe", headers=other_user_headers)
        assert resp.status_code == 404

    def test_ppe_summary_job_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/safety/ppe/nonexistent_job", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/safety/ppe/{job_id}/workers
# ---------------------------------------------------------------------------

class TestGetPPEWorkers:

    def test_worker_compliance_success(self, client, auth_headers, mock_mongodb, test_user):
        import asyncio
        _run_async(
            _seed_job_with_ppe(
                mock_mongodb,
                "job_workers_api",
                test_user["user_id"],
                ppe_workers=[
                    {
                        "track_id": 12,
                        "required_ppe": ["helmet", "vest"],
                        "detected_ppe": ["helmet", "vest"],
                        "missing_ppe": [],
                        "status": "compliant",
                    },
                    {
                        "track_id": 15,
                        "required_ppe": ["helmet", "vest"],
                        "detected_ppe": ["vest"],
                        "missing_ppe": ["helmet"],
                        "status": "non_compliant",
                    },
                ],
            )
        )

        resp = client.get("/api/v1/safety/ppe/job_workers_api/workers", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        items = data["items"]
        assert items[0]["track_id"] == 12
        assert items[0]["status"] == "compliant"
        assert items[1]["track_id"] == 15
        assert items[1]["status"] == "non_compliant"
        assert "helmet" in items[1]["missing_ppe"]

    def test_worker_compliance_no_auth(self, client):
        resp = client.get("/api/v1/safety/ppe/some_job/workers")
        assert resp.status_code == 401

    def test_worker_compliance_empty(self, client, auth_headers, mock_mongodb, test_user):
        import asyncio
        _run_async(
            _seed_job_with_ppe(
                mock_mongodb,
                "job_no_workers",
                test_user["user_id"],
            )
        )

        resp = client.get("/api/v1/safety/ppe/job_no_workers/workers", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []
