"""Unit tests for NoOp idempotency store adapter."""

import pytest

from app.adapters.outbound.idempotency.noop_idempotency_store import NoOpIdempotencyStore


@pytest.fixture
def noop_store():
    """Create NoOp idempotency store."""
    return NoOpIdempotencyStore()


@pytest.mark.asyncio
async def test_is_processed_always_returns_false(noop_store):
    """Test is_processed always returns False."""
    assert await noop_store.is_processed("SM123") is False
    assert await noop_store.is_processed("SM456") is False
    assert await noop_store.is_processed("") is False


@pytest.mark.asyncio
async def test_mark_processed_does_nothing(noop_store):
    """Test mark_processed does nothing (no-op)."""
    # Should not raise any exceptions
    await noop_store.mark_processed("SM123", ttl_seconds=3600)
    await noop_store.mark_processed("SM456", ttl_seconds=0)
    await noop_store.mark_processed("", ttl_seconds=-1)


@pytest.mark.asyncio
async def test_get_response_always_returns_none(noop_store):
    """Test get_response always returns None."""
    assert await noop_store.get_response("SM123") is None
    assert await noop_store.get_response("SM456") is None
    assert await noop_store.get_response("") is None


@pytest.mark.asyncio
async def test_store_response_does_nothing(noop_store):
    """Test store_response does nothing (no-op)."""
    # Should not raise any exceptions
    await noop_store.store_response("SM123", "response1", ttl_seconds=3600)
    await noop_store.store_response("SM456", "response2", ttl_seconds=0)
    await noop_store.store_response("", "", ttl_seconds=-1)


@pytest.mark.asyncio
async def test_noop_store_allows_idempotency_disabled(noop_store):
    """Test that NoOp store allows processing when idempotency is disabled."""
    # Even if we "mark" something as processed, is_processed still returns False
    await noop_store.mark_processed("SM123", 3600)
    assert await noop_store.is_processed("SM123") is False

    # get_response always returns None
    await noop_store.store_response("SM123", "test", 3600)
    assert await noop_store.get_response("SM123") is None
