"""Chat port interface."""

from abc import ABC, abstractmethod

from app.application.dtos.chat import ChatRequest, ChatResponse


class ChatPort(ABC):
    """Port interface for chat use case."""

    @abstractmethod
    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Handle a chat conversation turn.

        Args:
            request: Chat request DTO

        Returns:
            Chat response DTO
        """
        pass
