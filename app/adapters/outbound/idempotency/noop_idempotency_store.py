"""No-op idempotency store adapter for when idempotency is disabled."""

from typing import Optional

from app.application.ports.idempotency_store import IdempotencyStore


class NoOpIdempotencyStore(IdempotencyStore):
    """No-op adapter that always returns False for idempotency checks."""

    async def is_processed(self, key: str) -> bool:
        """
        Always return False (not processed).

        Args:
            key: Unique identifier (ignored)

        Returns:
            Always False
        """
        return False

    async def mark_processed(self, key: str, ttl_seconds: int) -> None:
        """
        No-op (does nothing).

        Args:
            key: Unique identifier (ignored)
            ttl_seconds: TTL (ignored)
        """
        pass

    async def get_response(self, key: str) -> Optional[str]:
        """
        Always return None (no stored response).

        Args:
            key: Unique identifier (ignored)

        Returns:
            Always None
        """
        return None

    async def store_response(self, key: str, response: str, ttl_seconds: int) -> None:
        """
        No-op (does nothing).

        Args:
            key: Unique identifier (ignored)
            response: Response string (ignored)
            ttl_seconds: TTL (ignored)
        """
        pass
