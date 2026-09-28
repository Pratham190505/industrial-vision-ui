"""
Tests for InventoryService — MongoDB persistence and query methods.
"""

from datetime import datetime, timezone
import pytest
from app.core.exceptions import EntityNotFoundError
from app.services.inventory_service import InventoryService


@pytest.mark.asyncio
async def test_persist_snapshots(mock_mongodb):
    service = InventoryService(mock_mongodb)

    snapshots = [
        {"timestamp_seconds": 0.0, "frame_number": 0, "counts": {"box": 5}},
        {"timestamp_seconds": 10.0, "frame_number": 300, "counts": {"box": 8}},
    ]
    count = await service.persist_snapshots(snapshots, job_id="job-1", user_id="user-1")
    assert count == 2

    # Empty list
    assert await service.persist_snapshots([], job_id="job-1", user_id="user-1") == 0


@pytest.mark.asyncio
async def test_persist_events(mock_mongodb):
    service = InventoryService(mock_mongodb)

    events = [
        {
            "event_type": "inventory_count_change",
            "class_name": "box",
            "previous_count": 5,
            "current_count": 8,
            "change": 3,
            "frame_number": 300,
            "timestamp_seconds": 10.0,
            "message": "Observed visible box count increased by 3.",
        },
        {
            "event_type": "inventory_low_stock",
            "class_name": "box",
            "current_count": 1,
            "threshold": 5,
            "frame_number": 600,
            "timestamp_seconds": 20.0,
            "message": "Observed visible box count (1) is at or below threshold.",
        },
    ]
    count = await service.persist_events(events, job_id="job-1", user_id="user-1")
    assert count == 2
    assert await service.persist_events([], job_id="job-1", user_id="user-1") == 0


@pytest.mark.asyncio
async def test_get_inventory_summary_success(mock_mongodb):
    service = InventoryService(mock_mongodb)

    # Insert a job with inventory data
    await mock_mongodb["processing_jobs"].insert_one({
        "_id": "job-inv-1",
        "user_id": "user-1",
        "status": "completed",
        "inventory": {
            "enabled": True,
            "available_classes": ["box", "pallet"],
            "unavailable_classes": ["crate"],
            "counts": {
                "box": {
                    "current_visible_count": 12,
                    "max_visible_count": 15,
                    "min_visible_count": 3,
                    "unique_track_count": 24,
                    "frames_with_inventory": 950,
                    "average_visible_count": 9.7,
                }
            },
            "total_inventory_events": 2,
        }
    })

    summary = await service.get_inventory_summary("job-inv-1", "user-1")
    assert summary.enabled is True
    assert summary.available_classes == ["box", "pallet"]
    assert summary.unavailable_classes == ["crate"]
    assert summary.counts["box"].current_visible_count == 12
    assert summary.counts["box"].unique_track_count == 24
    assert summary.total_inventory_events == 2


@pytest.mark.asyncio
async def test_get_inventory_summary_unauthorized_or_missing(mock_mongodb):
    service = InventoryService(mock_mongodb)

    await mock_mongodb["processing_jobs"].insert_one({
        "_id": "job-other",
        "user_id": "user-other",
        "inventory": {"enabled": True},
    })

    # Access by different user raises EntityNotFoundError
    with pytest.raises(EntityNotFoundError):
        await service.get_inventory_summary("job-other", "user-1")

    # Non-existent job
    with pytest.raises(EntityNotFoundError):
        await service.get_inventory_summary("non-existent", "user-1")


@pytest.mark.asyncio
async def test_get_inventory_snapshots_pagination(mock_mongodb):
    service = InventoryService(mock_mongodb)

    await mock_mongodb["processing_jobs"].insert_one({
        "_id": "job-snap-1",
        "user_id": "user-1",
    })

    for i in range(10):
        await service.persist_snapshots(
            [{"timestamp_seconds": float(i * 10), "frame_number": i * 300, "counts": {"box": i + 1}}],
            job_id="job-snap-1",
            user_id="user-1",
        )

    # First page: limit 4
    page1 = await service.get_inventory_snapshots("job-snap-1", "user-1", skip=0, limit=4)
    assert page1.total == 10
    assert len(page1.snapshots) == 4
    assert page1.snapshots[0].frame_number == 0

    # Second page: skip 4, limit 4
    page2 = await service.get_inventory_snapshots("job-snap-1", "user-1", skip=4, limit=4)
    assert len(page2.snapshots) == 4
    assert page2.snapshots[0].frame_number == 1200


@pytest.mark.asyncio
async def test_get_inventory_events_filtering(mock_mongodb):
    service = InventoryService(mock_mongodb)

    await mock_mongodb["processing_jobs"].insert_one({
        "_id": "job-ev-1",
        "user_id": "user-1",
    })

    events = [
        {"event_type": "inventory_count_change", "class_name": "box", "current_count": 5, "timestamp_seconds": 1.0},
        {"event_type": "inventory_low_stock", "class_name": "box", "current_count": 1, "threshold": 3, "timestamp_seconds": 2.0},
        {"event_type": "inventory_low_stock", "class_name": "pallet", "current_count": 0, "threshold": 2, "timestamp_seconds": 3.0},
    ]
    await service.persist_events(events, job_id="job-ev-1", user_id="user-1")

    # Filter by event_type
    low_res = await service.get_job_inventory_events("job-ev-1", "user-1", event_type="inventory_low_stock")
    assert low_res.total == 2
    assert all(e.event_type == "inventory_low_stock" for e in low_res.events)

    # Filter by class_name
    pallet_res = await service.get_job_inventory_events("job-ev-1", "user-1", class_name="pallet")
    assert pallet_res.total == 1
    assert pallet_res.events[0].class_name == "pallet"


@pytest.mark.asyncio
async def test_get_user_inventory_events(mock_mongodb):
    service = InventoryService(mock_mongodb)

    # Events from two different jobs belonging to user-1
    await service.persist_events(
        [{"event_type": "inventory_count_change", "class_name": "box", "current_count": 10, "timestamp_seconds": 5.0}],
        job_id="job-a",
        user_id="user-1",
    )
    await service.persist_events(
        [{"event_type": "inventory_low_stock", "class_name": "pallet", "current_count": 1, "threshold": 3, "timestamp_seconds": 8.0}],
        job_id="job-b",
        user_id="user-1",
    )
    # Event from user-2
    await service.persist_events(
        [{"event_type": "inventory_low_stock", "class_name": "crate", "current_count": 0, "threshold": 2, "timestamp_seconds": 1.0}],
        job_id="job-c",
        user_id="user-2",
    )

    user1_events = await service.get_user_inventory_events("user-1")
    assert user1_events.total == 2
    assert {e.job_id for e in user1_events.events} == {"job-a", "job-b"}
