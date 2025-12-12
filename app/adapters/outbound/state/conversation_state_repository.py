"""In-memory conversation state repository adapter."""

from typing import Optional

from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.domain.entities.conversation_state import ConversationState


class InMemoryConversationStateRepository(ConversationStateRepository):
    """In-memory implementation of conversation state repository."""

    def __init__(self) -> None:
        """Initialize in-memory repository."""
        self._storage: dict[str, ConversationState] = {}

    async def get(self, session_id: str) -> Optional[ConversationState]:
        """
        Get conversation state for a session.

        Args:
            session_id: Session identifier

        Returns:
            Conversation state entity, or None if not found
        """
        return self._storage.get(session_id)

    async def save(self, session_id: str, state: ConversationState) -> None:
        """
        Save conversation state.

        Args:
            session_id: Session identifier
            state: Conversation state entity to save
        """
        self._storage[session_id] = state

