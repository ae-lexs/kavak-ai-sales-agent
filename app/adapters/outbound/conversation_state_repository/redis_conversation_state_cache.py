"""Redis cache adapter for conversation state."""

import json
from datetime import datetime, timezone
from typing import Optional

from redis import asyncio as aioredis

from app.domain.entities.conversation_state import ConversationState


class RedisConversationStateCache:
    """Redis cache for conversation state using cache-aside pattern."""

    KEY_PREFIX = "conversation:state:"

    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        """
        Initialize Redis conversation state cache.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Time-to-live in seconds for cached states
        """
        self._redis_url = redis_url
        self._ttl_seconds = ttl_seconds
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

    def _make_key(self, session_id: str) -> str:
        """
        Make Redis key for session state.

        Args:
            session_id: Session identifier

        Returns:
            Redis key string
        """
        return f"{self.KEY_PREFIX}{session_id}"

    def _serialize_state(self, state: ConversationState) -> dict:
        """
        Serialize ConversationState to dictionary.

        Args:
            state: Conversation state entity

        Returns:
            Dictionary representation of the state
        """
        return {
            "session_id": state.session_id,
            "need": state.need,
            "budget": state.budget,
            "preferences": state.preferences,
            "financing_interest": state.financing_interest,
            "down_payment": state.down_payment,
            "loan_term": state.loan_term,
            "selected_car_price": state.selected_car_price,
            "last_question": state.last_question,
            "step": state.step,
            "lead_name": state.lead_name,
            "lead_phone": state.lead_phone,
            "lead_preferred_contact_time": state.lead_preferred_contact_time,
            "created_at": state.created_at.isoformat() if state.created_at else None,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }

    def _deserialize_state(self, data: dict) -> ConversationState:
        """
        Deserialize dictionary to ConversationState.

        Args:
            data: Dictionary representation of the state

        Returns:
            ConversationState entity
        """
        # Parse datetime strings back to datetime objects
        created_at = None
        updated_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

        return ConversationState(
            session_id=data["session_id"],
            need=data.get("need"),
            budget=data.get("budget"),
            preferences=data.get("preferences"),
            financing_interest=data.get("financing_interest"),
            down_payment=data.get("down_payment"),
            loan_term=data.get("loan_term"),
            selected_car_price=data.get("selected_car_price"),
            last_question=data.get("last_question"),
            step=data.get("step", "need"),
            lead_name=data.get("lead_name"),
            lead_phone=data.get("lead_phone"),
            lead_preferred_contact_time=data.get("lead_preferred_contact_time"),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
        )

    async def get(self, session_id: str) -> Optional[ConversationState]:
        """
        Get conversation state from cache.

        Args:
            session_id: Session identifier

        Returns:
            Conversation state entity, or None if not found in cache
        """
        try:
            client = await self._get_client()
            redis_key = self._make_key(session_id)
            cached_data = await client.get(redis_key)

            if cached_data is None:
                return None

            # Deserialize JSON to ConversationState
            state_dict = json.loads(cached_data)
            return self._deserialize_state(state_dict)
        except (json.JSONDecodeError, KeyError, ValueError, Exception) as e:
            # Log error but don't fail - treat as cache miss
            from app.infrastructure.logging.logger import logger

            logger.warning(f"Error reading from cache for session {session_id}: {str(e)}")
            return None

    async def set(self, session_id: str, state: ConversationState) -> None:
        """
        Store conversation state in cache with TTL.

        Args:
            session_id: Session identifier
            state: Conversation state entity to cache
        """
        try:
            client = await self._get_client()
            redis_key = self._make_key(session_id)
            state_dict = self._serialize_state(state)
            state_json = json.dumps(state_dict, sort_keys=True)

            await client.setex(redis_key, self._ttl_seconds, state_json)
        except Exception as e:
            # Log error but don't fail - cache write failure is non-critical
            from app.infrastructure.logging.logger import logger

            logger.warning(f"Error writing to cache for session {session_id}: {str(e)}")

    async def delete(self, session_id: str) -> None:
        """
        Delete conversation state from cache.

        Args:
            session_id: Session identifier
        """
        try:
            client = await self._get_client()
            redis_key = self._make_key(session_id)
            await client.delete(redis_key)
        except Exception as e:
            # Log error but don't fail - cache delete failure is non-critical
            from app.infrastructure.logging.logger import logger

            logger.warning(f"Error deleting from cache for session {session_id}: {str(e)}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
