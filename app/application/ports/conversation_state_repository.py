"""Conversation state repository port."""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.conversation_state import ConversationState


class ConversationStateRepository(ABC):
    """Port interface for conversation state repository."""

    @abstractmethod
    async def get(self, session_id: str) -> Optional[ConversationState]:
        """
        Get conversation state for a session.

        Args:
            session_id: Session identifier

        Returns:
            Conversation state entity, or None if not found
        """
        pass

    @abstractmethod
    async def save(self, session_id: str, state: ConversationState) -> None:
        """
        Save conversation state.

        Args:
            session_id: Session identifier
            state: Conversation state entity to save
        """
        pass
