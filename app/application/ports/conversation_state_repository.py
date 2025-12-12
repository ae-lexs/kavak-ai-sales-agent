"""Conversation state repository port."""

from abc import ABC, abstractmethod

from app.domain.entities.conversation_state import ConversationState


class ConversationStateRepository(ABC):
    """Port interface for conversation state repository."""

    @abstractmethod
    async def get(self, session_id: str) -> ConversationState:
        """
        Get conversation state for a session.

        Args:
            session_id: Session identifier

        Returns:
            Conversation state entity
        """
        pass

    @abstractmethod
    async def save(self, state: ConversationState) -> None:
        """
        Save conversation state.

        Args:
            state: Conversation state entity to save
        """
        pass

