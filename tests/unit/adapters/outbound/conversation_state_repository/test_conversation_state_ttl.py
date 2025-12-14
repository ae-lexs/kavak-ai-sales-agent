"""Unit tests for conversation state TTL and reset functionality."""

from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.outbound.conversation_state_repository.conversation_state_repository import (
    InMemoryConversationStateRepository,
)
from app.domain.entities.conversation_state import ConversationState


@pytest.fixture
def repository():
    """Create repository with short TTL for testing."""
    return InMemoryConversationStateRepository(ttl_seconds=60)  # 1 minute for tests


@pytest.mark.asyncio
async def test_ttl_purge_expired_sessions(repository):
    """Test that expired sessions are purged automatically."""
    # Create a session
    session_id = "test_session"
    state = ConversationState(session_id=session_id)

    await repository.save(session_id, state)

    # Manually set updated_at to be expired (2 minutes ago) after saving
    repository._storage[session_id].updated_at = datetime.now(timezone.utc) - timedelta(seconds=120)

    # Try to get it - should return None because it's expired
    result = await repository.get(session_id)
    assert result is None

    # Storage should be empty
    assert len(repository._storage) == 0


@pytest.mark.asyncio
async def test_ttl_keep_active_sessions(repository):
    """Test that active sessions are not purged."""
    # Create a session
    session_id = "test_session"
    state = ConversationState(session_id=session_id)

    await repository.save(session_id, state)

    # Get it immediately - should still be there
    result = await repository.get(session_id)
    assert result is not None
    assert result.session_id == session_id


@pytest.mark.asyncio
async def test_ttl_purge_on_save(repository):
    """Test that expired sessions are purged when saving new ones."""
    # Create expired session
    expired_session = "expired_session"
    expired_state = ConversationState(session_id=expired_session)
    await repository.save(expired_session, expired_state)
    # Manually set to expired after saving
    repository._storage[expired_session].updated_at = datetime.now(timezone.utc) - timedelta(
        seconds=120
    )

    # Create new session
    new_session = "new_session"
    new_state = ConversationState(session_id=new_session)
    await repository.save(new_session, new_state)

    # Expired session should be gone
    assert await repository.get(expired_session) is None
    # New session should still be there
    assert await repository.get(new_session) is not None


@pytest.mark.asyncio
async def test_reset_deletes_session(repository):
    """Test that reset deletes session state."""
    session_id = "test_session"
    state = ConversationState(session_id=session_id)
    await repository.save(session_id, state)

    # Verify it exists
    assert await repository.get(session_id) is not None

    # Reset it
    await repository.delete(session_id)

    # Verify it's gone
    assert await repository.get(session_id) is None


@pytest.mark.asyncio
async def test_touch_updates_timestamp():
    """Test that touch() updates the updated_at timestamp."""
    state = ConversationState(session_id="test")
    original_time = state.updated_at

    # Wait a tiny bit and touch
    import time

    time.sleep(0.01)
    state.touch()

    assert state.updated_at > original_time


@pytest.mark.asyncio
async def test_state_has_timestamps():
    """Test that new state has created_at and updated_at timestamps."""
    state = ConversationState(session_id="test")

    assert state.created_at is not None
    assert state.updated_at is not None
    assert isinstance(state.created_at, datetime)
    assert isinstance(state.updated_at, datetime)
    assert state.created_at.tzinfo == timezone.utc
    assert state.updated_at.tzinfo == timezone.utc
