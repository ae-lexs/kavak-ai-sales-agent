"""Idempotency store port."""

from abc import ABC, abstractmethod
from typing import Optional


class IdempotencyStore(ABC):
    """Port interface for idempotency store."""

    @abstractmethod
    async def is_processed(self, key: str) -> bool:
        """
        Check if a key has been processed.

        Args:
            key: Unique identifier for the processed item

        Returns:
            True if the key has been processed, False otherwise
        """
        pass

    @abstractmethod
    async def mark_processed(self, key: str, ttl_seconds: int) -> None:
        """
        Mark a key as processed with a TTL.

        Args:
            key: Unique identifier for the processed item
            ttl_seconds: Time-to-live in seconds
        """
        pass

    @abstractmethod
    async def get_response(self, key: str) -> Optional[str]:
        """
        Get stored response for a key.

        Args:
            key: Unique identifier for the processed item

        Returns:
            Stored response string, or None if not found
        """
        pass

    @abstractmethod
    async def store_response(self, key: str, response: str, ttl_seconds: int) -> None:
        """
        Store response for a key with a TTL.

        Args:
            key: Unique identifier for the processed item
            response: Response string to store
            ttl_seconds: Time-to-live in seconds
        """
        pass
