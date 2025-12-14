"""Unit tests for Redis conversation state cache."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.outbound.conversation_state_repository.redis_conversation_state_cache import (
    RedisConversationStateCache,
)
from app.domain.entities.conversation_state import ConversationState


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock()
    client.delete = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def redis_cache():
    """Create Redis conversation state cache with test config."""
    return RedisConversationStateCache("redis://localhost:6379/0", ttl_seconds=3600)


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


@pytest.mark.asyncio
async def test_get_returns_none_when_not_cached(redis_cache, mock_redis_client):
    """Test get returns None when state is not in cache."""
    with patch(
        "app.adapters.outbound.conversation_state_repository.redis_conversation_state_cache.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_cache._client = None

        result = await redis_cache.get("test_session")

        assert result is None
        mock_redis_client.get.assert_called_once_with("conversation:state:test_session")


@pytest.mark.asyncio
async def test_get_returns_state_when_cached(redis_cache, mock_redis_client, sample_state):
    """Test get returns ConversationState when found in cache."""
    # Serialize state to JSON
    state_dict = {
        "session_id": sample_state.session_id,
        "need": sample_state.need,
        "budget": sample_state.budget,
        "preferences": sample_state.preferences,
        "financing_interest": sample_state.financing_interest,
        "down_payment": sample_state.down_payment,
        "loan_term": sample_state.loan_term,
        "selected_car_price": sample_state.selected_car_price,
        "last_question": sample_state.last_question,
        "step": sample_state.step,
        "lead_name": sample_state.lead_name,
        "lead_phone": sample_state.lead_phone,
        "lead_preferred_contact_time": sample_state.lead_preferred_contact_time,
        "created_at": sample_state.created_at.isoformat() if sample_state.created_at else None,
        "updated_at": sample_state.updated_at.isoformat() if sample_state.updated_at else None,
    }
    import json

    cached_json = json.dumps(state_dict)

    mock_redis_client.get.return_value = cached_json

    with patch(
        "app.adapters.outbound.conversation_state_repository.redis_conversation_state_cache.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_cache._client = None

        result = await redis_cache.get("test_session")

        assert result is not None
        assert result.session_id == sample_state.session_id
        assert result.need == sample_state.need
        assert result.budget == sample_state.budget
        assert result.step == sample_state.step


@pytest.mark.asyncio
async def test_get_returns_none_on_json_decode_error(redis_cache, mock_redis_client):
    """Test get returns None when cached data is invalid JSON."""
    mock_redis_client.get.return_value = "invalid json"

    with patch(
        "app.adapters.outbound.conversation_state_repository.redis_conversation_state_cache.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_cache._client = None

        result = await redis_cache.get("test_session")

        assert result is None


@pytest.mark.asyncio
async def test_set_stores_state_with_ttl(redis_cache, mock_redis_client, sample_state):
    """Test set stores state in cache with TTL."""
    with patch(
        "app.adapters.outbound.conversation_state_repository.redis_conversation_state_cache.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_cache._client = None

        await redis_cache.set("test_session", sample_state)

        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][0] == "conversation:state:test_session"
        assert call_args[0][1] == 3600  # TTL
        # Verify JSON contains expected fields
        stored_json = call_args[0][2]
        import json

        stored_dict = json.loads(stored_json)
        assert stored_dict["session_id"] == sample_state.session_id
        assert stored_dict["need"] == sample_state.need


@pytest.mark.asyncio
async def test_delete_removes_state_from_cache(redis_cache, mock_redis_client):
    """Test delete removes state from cache."""
    with patch(
        "app.adapters.outbound.conversation_state_repository.redis_conversation_state_cache.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_cache._client = None

        await redis_cache.delete("test_session")

        mock_redis_client.delete.assert_called_once_with("conversation:state:test_session")


@pytest.mark.asyncio
async def test_key_namespace_correct(redis_cache):
    """Test that cache uses correct key namespace."""
    key = redis_cache._make_key("test_session")
    assert key == "conversation:state:test_session"


@pytest.mark.asyncio
async def test_close_closes_redis_connection(redis_cache, mock_redis_client):
    """Test close closes Redis connection."""
    redis_cache._client = mock_redis_client

    await redis_cache.close()

    mock_redis_client.close.assert_called_once()
    assert redis_cache._client is None
