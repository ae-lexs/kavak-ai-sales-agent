"""In-memory conversation state repository adapter."""

from datetime import datetime, timezone
from typing import Optional

from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.domain.entities.conversation_state import ConversationState
from app.infrastructure.config.settings import settings


class InMemoryConversationStateRepository(ConversationStateRepository):
    """In-memory implementation of conversation state repository with TTL cleanup."""

    def __init__(self, ttl_seconds: Optional[int] = None) -> None:
        """
        Initialize in-memory repository.

        Args:
            ttl_seconds: Time-to-live in seconds for session states
            (defaults to settings.state_ttl_seconds).
        """  # noqa: E501
        self._storage: dict[str, ConversationState] = {}
        self._ttl_seconds = ttl_seconds or settings.state_ttl_seconds

    def _purge_expired(self) -> None:
        """Remove expired sessions from storage."""
        now = datetime.now(timezone.utc)
        expired_sessions = [
            session_id
            for session_id, state in self._storage.items()
            if (now - state.updated_at).total_seconds() > self._ttl_seconds
        ]
        for session_id in expired_sessions:
            del self._storage[session_id]

    async def get(self, session_id: str) -> Optional[ConversationState]:
        """
        Get conversation state for a session.

        Args:
            session_id: Session identifier

        Returns:
            Conversation state entity, or None if not found or expired
        """
        self._purge_expired()
        state = self._storage.get(session_id)
        if state:
            # Check if this specific state is expired
            now = datetime.now(timezone.utc)
            if (now - state.updated_at).total_seconds() > self._ttl_seconds:
                del self._storage[session_id]
                return None
        return state

    async def save(self, session_id: str, state: ConversationState) -> None:
        """
        Save conversation state.

        Args:
            session_id: Session identifier
            state: Conversation state entity to save
        """
        self._purge_expired()
        # Only touch if state already exists (to preserve created_at)
        if session_id in self._storage:
            state.touch()  # Update timestamp
        self._storage[session_id] = state

    async def delete(self, session_id: str) -> None:
        """
        Delete conversation state for a session.

        Args:
            session_id: Session identifier
        """
        if session_id in self._storage:
            del self._storage[session_id]
