"""In-memory conversation state repository adapter."""

from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.domain.entities.conversation_state import ConversationState


class InMemoryConversationStateRepository(ConversationStateRepository):
    """In-memory implementation of conversation state repository."""

    def __init__(self) -> None:
        """Initialize in-memory repository."""
        self._storage: dict[str, ConversationState] = {}

    async def get(self, session_id: str) -> ConversationState:
        """
        Get conversation state for a session.

        Args:
            session_id: Session identifier

        Returns:
            Conversation state entity (creates new one if not found)
        """
        if session_id not in self._storage:
            self._storage[session_id] = ConversationState(session_id=session_id)
        return self._storage[session_id]

    async def save(self, state: ConversationState) -> None:
        """
        Save conversation state.

        Args:
            state: Conversation state entity to save
        """
        self._storage[state.session_id] = state

    async def delete(self, session_id: str) -> None:
        """
        Delete conversation state for a session.

        Args:
            session_id: Session identifier
        """
        if session_id in self._storage:
            del self._storage[session_id]
