"""Unit tests for Redis idempotency store adapter."""

from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.outbound.idempotency.redis_idempotency_store import RedisIdempotencyStore


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.exists = AsyncMock(return_value=0)
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def redis_store():
    """Create Redis idempotency store with test URL."""
    return RedisIdempotencyStore("redis://localhost:6379/0")


@pytest.mark.asyncio
async def test_is_processed_returns_false_when_not_processed(redis_store, mock_redis_client):
    """Test is_processed returns False when key doesn't exist."""
    with patch(
        "app.adapters.outbound.idempotency.redis_idempotency_store.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_store._client = None  # Reset client to force recreation

        result = await redis_store.is_processed("SM1234567890")

        assert result is False
        mock_redis_client.exists.assert_called_once_with("twilio:processed:SM1234567890")


@pytest.mark.asyncio
async def test_is_processed_returns_true_when_processed(redis_store, mock_redis_client):
    """Test is_processed returns True when key exists."""
    mock_redis_client.exists.return_value = 1

    with patch(
        "app.adapters.outbound.idempotency.redis_idempotency_store.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_store._client = None

        result = await redis_store.is_processed("SM1234567890")

        assert result is True
        mock_redis_client.exists.assert_called_once_with("twilio:processed:SM1234567890")


@pytest.mark.asyncio
async def test_mark_processed_stores_key_with_ttl(redis_store, mock_redis_client):
    """Test mark_processed stores key with TTL."""
    with patch(
        "app.adapters.outbound.idempotency.redis_idempotency_store.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_store._client = None

        await redis_store.mark_processed("SM1234567890", ttl_seconds=3600)

        mock_redis_client.setex.assert_called_once_with("twilio:processed:SM1234567890", 3600, "1")


@pytest.mark.asyncio
async def test_get_response_returns_none_when_not_found(redis_store, mock_redis_client):
    """Test get_response returns None when response not stored."""
    mock_redis_client.get.return_value = None

    with patch(
        "app.adapters.outbound.idempotency.redis_idempotency_store.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_store._client = None

        result = await redis_store.get_response("SM1234567890")

        assert result is None
        mock_redis_client.get.assert_called_once_with("twilio:response:SM1234567890")


@pytest.mark.asyncio
async def test_get_response_returns_stored_response(redis_store, mock_redis_client):
    """Test get_response returns stored TwiML response."""
    twiml_response = (
        '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Hola</Message></Response>'
    )
    mock_redis_client.get.return_value = twiml_response

    with patch(
        "app.adapters.outbound.idempotency.redis_idempotency_store.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_store._client = None

        result = await redis_store.get_response("SM1234567890")

        assert result == twiml_response
        mock_redis_client.get.assert_called_once_with("twilio:response:SM1234567890")


@pytest.mark.asyncio
async def test_store_response_stores_twiml_with_ttl(redis_store, mock_redis_client):
    """Test store_response stores TwiML with TTL."""
    twiml_response = (
        '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Hola</Message></Response>'
    )

    with patch(
        "app.adapters.outbound.idempotency.redis_idempotency_store.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_store._client = None

        await redis_store.store_response("SM1234567890", twiml_response, ttl_seconds=3600)

        mock_redis_client.setex.assert_called_once_with(
            "twilio:response:SM1234567890", 3600, twiml_response
        )


@pytest.mark.asyncio
async def test_close_closes_redis_connection(redis_store, mock_redis_client):
    """Test close closes Redis connection."""
    redis_store._client = mock_redis_client

    await redis_store.close()

    mock_redis_client.close.assert_called_once()
    assert redis_store._client is None


@pytest.mark.asyncio
async def test_client_reuse(redis_store, mock_redis_client):
    """Test that client is reused across multiple calls."""
    with patch(
        "app.adapters.outbound.idempotency.redis_idempotency_store.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_store._client = None

        # First call should create client
        await redis_store.is_processed("SM1")
        assert mock_from_url.call_count == 1

        # Second call should reuse client
        await redis_store.is_processed("SM2")
        assert mock_from_url.call_count == 1


@pytest.mark.asyncio
async def test_key_namespace_correct(redis_store, mock_redis_client):
    """Test that keys use correct namespace."""
    with patch(
        "app.adapters.outbound.idempotency.redis_idempotency_store.aioredis.from_url",
        new_callable=AsyncMock,
    ) as mock_from_url:
        mock_from_url.return_value = mock_redis_client
        redis_store._client = None

        message_sid = "SM9876543210"
        await redis_store.mark_processed(message_sid, 3600)
        await redis_store.store_response(message_sid, "test_response", 3600)

        # Verify correct key prefixes
        assert mock_redis_client.setex.call_args_list[0][0][0] == f"twilio:processed:{message_sid}"
        assert mock_redis_client.setex.call_args_list[1][0][0] == f"twilio:response:{message_sid}"
