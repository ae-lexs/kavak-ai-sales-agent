"""Chat use case."""

from app.application.dtos.chat import ChatRequest, ChatResponse
from app.application.ports.chat_port import ChatPort


class ChatUseCase:
    """Use case for handling chat conversations."""

    def __init__(self, chat_port: ChatPort) -> None:
        """
        Initialize chat use case.

        Args:
            chat_port: Port implementation for chat handling
        """
        self._chat_port = chat_port

    async def execute(self, request: ChatRequest) -> ChatResponse:
        """
        Execute chat use case.

        Args:
            request: Chat request DTO

        Returns:
            Chat response DTO
        """
        return await self._chat_port.handle_chat(request)
