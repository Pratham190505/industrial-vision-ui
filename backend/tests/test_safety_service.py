"""
Tests for SafetyService persistence and user isolation (tests/test_safety_service.py).
"""

from datetime import datetime, timezone
import pytest
from app.core.exceptions import EntityNotFoundError
from app.schemas.safety import SafetyZoneCreate, SafetyZoneUpdate
from app.services.safety_service import SafetyService


@pytest.mark.anyio
async def test_safety_zone_crud_lifecycle(mock_mongodb):
    service = SafetyService(mock_mongodb)
    user_id = "usr_safety_test_1"

    # 1. Create Zone
    zone_data = SafetyZoneCreate(
        name="Forklift Charging Zone",
        zone_type="restricted",
        polygon=[[10, 10], [100, 10], [100, 100], [10, 100]],
        enabled=True,
    )
    created = await service.create_zone(user_id=user_id, data=zone_data)
    assert created.zone_id is not None
    assert created.name == "Forklift Charging Zone"
    assert created.user_id == user_id

    # 2. Get Zone
    fetched = await service.get_zone(zone_id=created.zone_id, user_id=user_id)
    assert fetched.zone_id == created.zone_id
    assert fetched.name == "Forklift Charging Zone"

    # 3. List Zones
    zones_list = await service.get_zones(user_id=user_id)
    assert zones_list.total == 1
    assert zones_list.items[0].zone_id == created.zone_id

    # 4. Update Zone
    updated = await service.update_zone(
        zone_id=created.zone_id,
        user_id=user_id,
        data=SafetyZoneUpdate(name="Renamed Charging Zone", enabled=False),
    )
    assert updated.name == "Renamed Charging Zone"
    assert updated.enabled is False

    # 5. Delete Zone
    success = await service.delete_zone(zone_id=created.zone_id, user_id=user_id)
    assert success is True

    # 6. Verify Deletion
    with pytest.raises(EntityNotFoundError):
        await service.get_zone(zone_id=created.zone_id, user_id=user_id)


@pytest.mark.anyio
async def test_safety_zone_user_isolation(mock_mongodb):
    service = SafetyService(mock_mongodb)
    user_1 = "usr_zone_owner"
    user_2 = "usr_zone_attacker"

    created = await service.create_zone(
        user_id=user_1,
        data=SafetyZoneCreate(
            name="Confidential Vault",
            zone_type="restricted",
            polygon=[[0, 0], [50, 0], [50, 50], [0, 50]],
        ),
    )

    # User 2 cannot access User 1's zone
    with pytest.raises(EntityNotFoundError):
        await service.get_zone(zone_id=created.zone_id, user_id=user_2)

    # User 2 cannot update User 1's zone
    with pytest.raises(EntityNotFoundError):
        await service.update_zone(
            zone_id=created.zone_id,
            user_id=user_2,
            data=SafetyZoneUpdate(name="Hacked Name"),
        )

    # User 2 cannot delete User 1's zone
    with pytest.raises(EntityNotFoundError):
        await service.delete_zone(zone_id=created.zone_id, user_id=user_2)


@pytest.mark.anyio
async def test_safety_events_persistence_and_filtering(mock_mongodb):
    service = SafetyService(mock_mongodb)
    user_id = "usr_event_test"
    job_id = "job_video_123"

    # Insert dummy job into processing_jobs
    jobs_coll = mock_mongodb["processing_jobs"]
    await jobs_coll.insert_one({
        "_id": job_id,
        "user_id": user_id,
        "status": "completed",
        "safety": {
            "enabled": True,
            "total_events": 2,
            "restricted_zone_violations": 1,
            "proximity_warnings": 1,
            "collision_risk_events": 0,
            "severity_counts": {"low": 0, "medium": 1, "high": 1, "critical": 0},
        },
    })

    events = [
        {
            "event_type": "restricted_zone_violation",
            "severity": "high",
            "track_ids": [1],
            "zone_id": "zone_1",
            "distance": None,
            "frame_number": 10,
            "timestamp_seconds": 1.0,
            "message": "Person 1 in zone 1",
        },
        {
            "event_type": "proximity_warning",
            "severity": "warning",
            "track_ids": [1, 2],
            "zone_id": None,
            "distance": 45.0,
            "frame_number": 25,
            "timestamp_seconds": 2.5,
            "message": "Person 1 near forklift 2",
        },
    ]

    saved_count = await service.persist_events(events=events, job_id=job_id, user_id=user_id)
    assert saved_count == 2

    # Query all events for user
    res_all = await service.get_events(user_id=user_id)
    assert res_all.total == 2
    assert len(res_all.items) == 2

    # Filter by event_type
    res_filtered = await service.get_events(user_id=user_id, event_type="restricted_zone_violation")
    assert res_filtered.total == 1
    assert res_filtered.items[0].event_type == "restricted_zone_violation"

    # Retrieve specific event by ID
    event_id = res_all.items[0].event_id
    single_event = await service.get_event(event_id=event_id, user_id=user_id)
    assert single_event.event_id == event_id

    # Retrieve summary for job
    summary = await service.get_job_summary(job_id=job_id, user_id=user_id)
    assert summary.enabled is True
    assert summary.total_events == 2
    assert summary.restricted_zone_violations == 1
