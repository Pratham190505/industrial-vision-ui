"""
Tests for PPE service — persistence and query logic.
"""

import pytest
from datetime import datetime, timezone
from app.services.ppe_service import PPEService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_job(db, job_id, user_id, ppe_data=None, ppe_workers=None):
    """Insert a processing job document with optional PPE data."""
    import asyncio

    doc = {
        "_id": job_id,
        "user_id": user_id,
        "status": "completed",
        "original_filename": "test.mp4",
        "processed_filename": "test_processed.mp4",
        "created_at": datetime.now(timezone.utc),
    }
    if ppe_data is not None:
        doc["ppe"] = ppe_data
    if ppe_workers is not None:
        doc["ppe_workers"] = ppe_workers

    coll = db["processing_jobs"]
    asyncio.get_event_loop().run_until_complete(coll.insert_one(doc))
    return doc


# ---------------------------------------------------------------------------
# PPE Event Persistence
# ---------------------------------------------------------------------------

class TestPPEEventPersistence:

    @pytest.mark.asyncio
    async def test_persist_ppe_events(self, mock_mongodb):
        service = PPEService(mock_mongodb)
        events = [
            {
                "event_type": "helmet_missing",
                "severity": "high",
                "track_ids": [12],
                "missing_ppe": ["helmet"],
                "frame_number": 100,
                "timestamp_seconds": 3.3,
                "message": "Worker #12 missing helmet.",
            },
            {
                "event_type": "vest_missing",
                "severity": "high",
                "track_ids": [15],
                "missing_ppe": ["vest"],
                "frame_number": 200,
                "timestamp_seconds": 6.6,
                "message": "Worker #15 missing vest.",
            },
        ]
        count = await service.persist_ppe_events(events, "job_123", "usr_test")
        assert count == 2

        # Verify documents in DB
        total = await service.events_coll.count_documents({"job_id": "job_123"})
        assert total == 2

    @pytest.mark.asyncio
    async def test_persist_empty_events(self, mock_mongodb):
        service = PPEService(mock_mongodb)
        count = await service.persist_ppe_events([], "job_123", "usr_test")
        assert count == 0


# ---------------------------------------------------------------------------
# PPE Summary Retrieval
# ---------------------------------------------------------------------------

class TestPPESummaryRetrieval:

    @pytest.mark.asyncio
    async def test_get_ppe_summary_with_data(self, mock_mongodb):
        jobs_coll = mock_mongodb["processing_jobs"]
        await jobs_coll.insert_one({
            "_id": "job_ppe_1",
            "user_id": "usr_1",
            "status": "completed",
            "ppe": {
                "enabled": True,
                "available": True,
                "workers_checked": 10,
                "compliant_workers": 7,
                "non_compliant_workers": 3,
                "unknown_workers": 0,
                "helmet_violations": 2,
                "vest_violations": 1,
            },
            "created_at": datetime.now(timezone.utc),
        })

        service = PPEService(mock_mongodb)
        summary = await service.get_ppe_summary("job_ppe_1", "usr_1")

        assert summary.enabled is True
        assert summary.available is True
        assert summary.workers_checked == 10
        assert summary.compliant_workers == 7
        assert summary.non_compliant_workers == 3
        assert summary.helmet_violations == 2
        assert summary.vest_violations == 1

    @pytest.mark.asyncio
    async def test_get_ppe_summary_no_ppe_data(self, mock_mongodb):
        jobs_coll = mock_mongodb["processing_jobs"]
        await jobs_coll.insert_one({
            "_id": "job_no_ppe",
            "user_id": "usr_1",
            "status": "completed",
            "created_at": datetime.now(timezone.utc),
        })

        service = PPEService(mock_mongodb)
        summary = await service.get_ppe_summary("job_no_ppe", "usr_1")
        assert summary.enabled is False
        assert summary.available is False

    @pytest.mark.asyncio
    async def test_get_ppe_summary_not_found(self, mock_mongodb):
        from app.core.exceptions import EntityNotFoundError
        service = PPEService(mock_mongodb)
        with pytest.raises(EntityNotFoundError):
            await service.get_ppe_summary("nonexistent_job", "usr_1")

    @pytest.mark.asyncio
    async def test_get_ppe_summary_wrong_user(self, mock_mongodb):
        from app.core.exceptions import EntityNotFoundError
        jobs_coll = mock_mongodb["processing_jobs"]
        await jobs_coll.insert_one({
            "_id": "job_other_user",
            "user_id": "usr_owner",
            "status": "completed",
            "created_at": datetime.now(timezone.utc),
        })

        service = PPEService(mock_mongodb)
        with pytest.raises(EntityNotFoundError):
            await service.get_ppe_summary("job_other_user", "usr_hacker")


# ---------------------------------------------------------------------------
# PPE Worker Compliance Retrieval
# ---------------------------------------------------------------------------

class TestPPEWorkerCompliance:

    @pytest.mark.asyncio
    async def test_get_worker_compliance(self, mock_mongodb):
        jobs_coll = mock_mongodb["processing_jobs"]
        await jobs_coll.insert_one({
            "_id": "job_workers",
            "user_id": "usr_1",
            "status": "completed",
            "ppe_workers": [
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
            "created_at": datetime.now(timezone.utc),
        })

        service = PPEService(mock_mongodb)
        result = await service.get_worker_compliance("job_workers", "usr_1")

        assert result.total == 2
        assert result.items[0].track_id == 12
        assert result.items[0].status == "compliant"
        assert result.items[1].track_id == 15
        assert result.items[1].status == "non_compliant"
        assert "helmet" in result.items[1].missing_ppe

    @pytest.mark.asyncio
    async def test_get_worker_compliance_empty(self, mock_mongodb):
        jobs_coll = mock_mongodb["processing_jobs"]
        await jobs_coll.insert_one({
            "_id": "job_empty_workers",
            "user_id": "usr_1",
            "status": "completed",
            "created_at": datetime.now(timezone.utc),
        })

        service = PPEService(mock_mongodb)
        result = await service.get_worker_compliance("job_empty_workers", "usr_1")
        assert result.total == 0
        assert result.items == []
