"""Redis idempotency store adapter."""

from typing import Optional

from redis import asyncio as aioredis

from app.application.ports.idempotency_store import IdempotencyStore


class RedisIdempotencyStore(IdempotencyStore):
    """Redis adapter for idempotency store."""

    KEY_PREFIX = "twilio:processed:"
    RESPONSE_KEY_PREFIX = "twilio:response:"

    def __init__(self, redis_url: str) -> None:
        """
        Initialize Redis idempotency store.

        Args:
            redis_url: Redis connection URL
        """
        self._redis_url = redis_url
        self._client: Optional[aioredis.Redis] = None

    async def _get_client(self) -> aioredis.Redis:
        """
        Get or create Redis client.

        Returns:
            Redis client instance
        """
        if self._client is None:
            self._client = await aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    def _make_key(self, message_sid: str) -> str:
        """
        Make Redis key for message processing status.

        Args:
            message_sid: Twilio message SID

        Returns:
            Redis key string
        """
        return f"{self.KEY_PREFIX}{message_sid}"

    def _make_response_key(self, message_sid: str) -> str:
        """
        Make Redis key for stored response.

        Args:
            message_sid: Twilio message SID

        Returns:
            Redis key string
        """
        return f"{self.RESPONSE_KEY_PREFIX}{message_sid}"

    async def is_processed(self, key: str) -> bool:
        """
        Check if a key has been processed.

        Args:
            key: Message SID (Twilio message identifier)

        Returns:
            True if the key has been processed, False otherwise
        """
        client = await self._get_client()
        redis_key = self._make_key(key)
        exists = await client.exists(redis_key)
        return exists > 0

    async def mark_processed(self, key: str, ttl_seconds: int) -> None:
        """
        Mark a key as processed with a TTL.

        Args:
            key: Message SID (Twilio message identifier)
            ttl_seconds: Time-to-live in seconds
        """
        client = await self._get_client()
        redis_key = self._make_key(key)
        await client.setex(redis_key, ttl_seconds, "1")

    async def get_response(self, key: str) -> Optional[str]:
        """
        Get stored response for a key.

        Args:
            key: Message SID (Twilio message identifier)

        Returns:
            Stored response string (TwiML XML), or None if not found
        """
        client = await self._get_client()
        response_key = self._make_response_key(key)
        response = await client.get(response_key)
        return response

    async def store_response(self, key: str, response: str, ttl_seconds: int) -> None:
        """
        Store response for a key with a TTL.

        Args:
            key: Message SID (Twilio message identifier)
            response: Response string to store (TwiML XML)
            ttl_seconds: Time-to-live in seconds
        """
        client = await self._get_client()
        response_key = self._make_response_key(key)
        await client.setex(response_key, ttl_seconds, response)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
