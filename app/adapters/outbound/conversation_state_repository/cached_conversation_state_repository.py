"""Cached conversation state repository with cache-aside pattern."""

from typing import Optional

from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.domain.entities.conversation_state import ConversationState
from app.infrastructure.logging.logger import log_turn

from .redis_conversation_state_cache import RedisConversationStateCache


class CachedConversationStateRepository(ConversationStateRepository):
    """Conversation state repository with Redis cache (cache-aside pattern)."""

    def __init__(
        self,
        primary_repository: ConversationStateRepository,
        cache: RedisConversationStateCache,
    ) -> None:
        """
        Initialize cached repository.

        Args:
            primary_repository: Primary repository (Postgres) - source of truth
            cache: Redis cache for caching states
        """
        self._primary = primary_repository
        self._cache = cache

    async def get(self, session_id: str) -> Optional[ConversationState]:
        """
        Get conversation state (cache-aside pattern).

        Checks cache first, then loads from primary repository if cache miss.

        Args:
            session_id: Session identifier

        Returns:
            Conversation state entity, or None if not found
        """
        # Try cache first
        cached_state = await self._cache.get(session_id)
        if cached_state is not None:
            # Cache hit - log and return
            log_turn(
                session_id=session_id,
                turn_id="cache",
                component="state_cache",
                state_cache_hit=True,
                state_cache_miss=False,
            )
            return cached_state

        # Cache miss - load from primary repository
        log_turn(
            session_id=session_id,
            turn_id="cache",
            component="state_cache",
            state_cache_hit=False,
            state_cache_miss=True,
        )
        state = await self._primary.get(session_id)

        # Populate cache if found
        if state is not None:
            await self._cache.set(session_id, state)

        return state

    async def save(self, session_id: str, state: ConversationState) -> None:
        """
        Save conversation state (cache-aside pattern).

        Saves to primary repository first, then updates cache.

        Args:
            session_id: Session identifier
            state: Conversation state entity to save
        """
        # Save to primary repository first (source of truth)
        await self._primary.save(session_id, state)

        # Update cache
        await self._cache.set(session_id, state)

    async def delete(self, session_id: str) -> None:
        """
        Delete conversation state (cache-aside pattern).

        Deletes from both primary repository and cache.

        Args:
            session_id: Session identifier
        """
        # Delete from primary repository first
        await self._primary.delete(session_id)

        # Delete from cache
        await self._cache.delete(session_id)
