"""
Tests for LiveSessionService — session management, isolated state, and lifecycle.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

from app.schemas.live import LiveSessionCreateResponse, LiveSessionStopResponse
from app.services.live_session_service import LiveSessionService, LiveSessionState


@pytest.mark.asyncio
async def test_create_session(mock_mongodb):
    service = LiveSessionService(mock_mongodb)
    res = await service.create_session(user_id="user_123")

    assert isinstance(res, LiveSessionCreateResponse)
    assert res.session_id is not None
    assert res.status == "active"

    # Verify in-memory state exists
    session_state = await service.get_session(res.session_id, user_id="user_123")
    assert session_state.session_id == res.session_id
    assert session_state.user_id == "user_123"
    assert session_state.status == "active"

    # Verify document persisted in MongoDB
    doc = await mock_mongodb["live_sessions"].find_one({"_id": res.session_id})
    assert doc is not None
    assert doc["user_id"] == "user_123"
    assert doc["status"] == "active"


@pytest.mark.asyncio
async def test_get_session_ownership_enforcement(mock_mongodb):
    service = LiveSessionService(mock_mongodb)
    res = await service.create_session(user_id="user_owner")

    # Unauthorized access should raise 404 (EntityNotFoundError)
    from app.core.exceptions import EntityNotFoundError
    with pytest.raises(EntityNotFoundError):
        await service.get_session(res.session_id, user_id="user_intruder")


@pytest.mark.asyncio
async def test_session_inactivity_timeout(mock_mongodb):
    service = LiveSessionService(mock_mongodb)
    res = await service.create_session(user_id="user_timeout")

    # Artificially age the session beyond LIVE_SESSION_TIMEOUT_SECONDS (60s)
    session_state = service._active_sessions[res.session_id]
    session_state.last_activity_at = datetime.now(timezone.utc) - timedelta(seconds=75)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_session(res.session_id, user_id="user_timeout")

    assert exc_info.value.status_code == 410
    assert "expired" in exc_info.value.detail.lower()

    # Session should now be marked stopped/expired in DB and removed from active memory
    assert res.session_id not in service._active_sessions
    doc = await mock_mongodb["live_sessions"].find_one({"_id": res.session_id})
    assert doc["status"] == "expired"


@pytest.mark.asyncio
async def test_stop_session_and_summary(mock_mongodb):
    service = LiveSessionService(mock_mongodb)
    res = await service.create_session(user_id="user_stop")
    session_id = res.session_id

    # Simulate some processed frames and unique tracks
    session_state = service._active_sessions[session_id]
    session_state.frame_counter = 42
    session_state.unique_track_ids = {1, 2, 3, 4}
    session_state.processing_times = [50.0, 60.0, 70.0]
    session_state.total_safety_events = 2

    stop_res = await service.stop_session(session_id, user_id="user_stop")
    assert isinstance(stop_res, LiveSessionStopResponse)
    assert stop_res.status == "stopped"
    assert stop_res.summary.frames_processed == 42
    assert stop_res.summary.unique_tracks == 4
    assert stop_res.summary.average_processing_time_ms == 60.0
    assert stop_res.summary.safety_events == 2

    # Session removed from in-memory dictionary
    assert session_id not in service._active_sessions

    # Persisted summary in DB
    doc = await mock_mongodb["live_sessions"].find_one({"_id": session_id})
    assert doc["status"] == "stopped"
    assert doc["frame_count"] == 42
    assert doc["unique_tracks"] == 4


@pytest.mark.asyncio
async def test_stop_session_unauthorized(mock_mongodb):
    service = LiveSessionService(mock_mongodb)
    res = await service.create_session(user_id="user_legit")

    from app.core.exceptions import EntityNotFoundError
    with pytest.raises(EntityNotFoundError):
        await service.stop_session(res.session_id, user_id="user_imposter")

    # Legit session should still be active in memory
    assert res.session_id in service._active_sessions


@pytest.mark.asyncio
async def test_list_user_sessions(mock_mongodb):
    service = LiveSessionService(mock_mongodb)
    res1 = await service.create_session(user_id="user_multi")
    res2 = await service.create_session(user_id="user_multi")
    await service.create_session(user_id="user_other")

    listing = await service.list_user_sessions(user_id="user_multi")
    assert listing.total == 2
    session_ids = [item.session_id for item in listing.items]
    assert res1.session_id in session_ids
    assert res2.session_id in session_ids


@pytest.mark.asyncio
async def test_cleanup_expired_sessions(mock_mongodb):
    service = LiveSessionService(mock_mongodb)
    res1 = await service.create_session(user_id="user_clean_1")
    res2 = await service.create_session(user_id="user_clean_2")

    # Age res1 past timeout
    service._active_sessions[res1.session_id].last_activity_at = (
        datetime.now(timezone.utc) - timedelta(seconds=120)
    )

    cleaned = await service.cleanup_expired_sessions()
    assert cleaned == 1
    assert res1.session_id not in service._active_sessions
    assert res2.session_id in service._active_sessions
