"""Unit tests for cached conversation state repository."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.outbound.conversation_state_repository.cached_conversation_state_repository import (  # noqa: E501
    CachedConversationStateRepository,
)
from app.adapters.outbound.conversation_state_repository.redis_conversation_state_cache import (
    RedisConversationStateCache,
)
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.domain.entities.conversation_state import ConversationState


@pytest.fixture
def mock_primary_repository():
    """Create a mock primary repository."""
    repo = AsyncMock(spec=ConversationStateRepository)
    repo.get = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_cache():
    """Create a mock cache."""
    cache = AsyncMock(spec=RedisConversationStateCache)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    return cache


@pytest.fixture
def sample_state():
    """Create a sample conversation state."""
    return ConversationState(
        session_id="test_session",
        need="auto familiar",
        budget="$300000",
        step="options",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def cached_repository(mock_primary_repository, mock_cache):
    """Create cached repository with mocked dependencies."""
    return CachedConversationStateRepository(mock_primary_repository, mock_cache)


@pytest.mark.asyncio
async def test_get_cache_hit_returns_cached_state(
    cached_repository, mock_primary_repository, mock_cache, sample_state
):
    """Test get returns cached state on cache hit without querying primary."""
    mock_cache.get.return_value = sample_state

    result = await cached_repository.get("test_session")

    assert result == sample_state
    mock_cache.get.assert_called_once_with("test_session")
    mock_primary_repository.get.assert_not_called()


@pytest.mark.asyncio
async def test_get_cache_miss_loads_from_primary_and_populates_cache(
    cached_repository, mock_primary_repository, mock_cache, sample_state
):
    """Test get loads from primary on cache miss and populates cache."""
    mock_cache.get.return_value = None
    mock_primary_repository.get.return_value = sample_state

    result = await cached_repository.get("test_session")

    assert result == sample_state
    mock_cache.get.assert_called_once_with("test_session")
    mock_primary_repository.get.assert_called_once_with("test_session")
    mock_cache.set.assert_called_once_with("test_session", sample_state)


@pytest.mark.asyncio
async def test_get_cache_miss_primary_not_found_returns_none(
    cached_repository, mock_primary_repository, mock_cache
):
    """Test get returns None when both cache and primary miss."""
    mock_cache.get.return_value = None
    mock_primary_repository.get.return_value = None

    result = await cached_repository.get("test_session")

    assert result is None
    mock_cache.get.assert_called_once_with("test_session")
    mock_primary_repository.get.assert_called_once_with("test_session")
    mock_cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_save_writes_to_primary_then_cache(
    cached_repository, mock_primary_repository, mock_cache, sample_state
):
    """Test save writes to primary repository first, then updates cache."""
    await cached_repository.save("test_session", sample_state)

    # Verify primary save was called first
    mock_primary_repository.save.assert_called_once_with("test_session", sample_state)
    # Verify cache set was called after
    mock_cache.set.assert_called_once_with("test_session", sample_state)


@pytest.mark.asyncio
async def test_delete_removes_from_primary_then_cache(
    cached_repository, mock_primary_repository, mock_cache
):
    """Test delete removes from primary repository first, then cache."""
    await cached_repository.delete("test_session")

    mock_primary_repository.delete.assert_called_once_with("test_session")
    mock_cache.delete.assert_called_once_with("test_session")


@pytest.mark.asyncio
async def test_get_logs_cache_hit(cached_repository, mock_cache, sample_state):
    """Test get logs cache hit."""
    mock_cache.get.return_value = sample_state

    with patch(
        "app.adapters.outbound.conversation_state_repository.cached_conversation_state_repository.log_turn"
    ) as mock_log:
        await cached_repository.get("test_session")

        # Verify log was called with cache hit
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["component"] == "state_cache"
        assert call_kwargs["state_cache_hit"] is True
        assert call_kwargs["state_cache_miss"] is False


@pytest.mark.asyncio
async def test_get_logs_cache_miss(
    cached_repository, mock_cache, mock_primary_repository, sample_state
):
    """Test get logs cache miss."""
    mock_cache.get.return_value = None
    mock_primary_repository.get.return_value = sample_state

    with patch(
        "app.adapters.outbound.conversation_state_repository.cached_conversation_state_repository.log_turn"
    ) as mock_log:
        await cached_repository.get("test_session")

        # Verify log was called with cache miss
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["component"] == "state_cache"
        assert call_kwargs["state_cache_hit"] is False
        assert call_kwargs["state_cache_miss"] is True
