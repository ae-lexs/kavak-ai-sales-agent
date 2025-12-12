"""Chat adapter implementation."""

from app.application.dtos.chat import ChatRequest, ChatResponse
from app.application.ports.chat_port import ChatPort
from app.application.use_cases.handle_chat_turn_use_case import HandleChatTurnUseCase
from app.adapters.outbound.persistence.conversation_state_repository import (
    InMemoryConversationStateRepository,
)


class LLMRAGChatAdapter(ChatPort):
    """LLM/RAG-based chat adapter implementation."""

    def __init__(self) -> None:
        """Initialize chat adapter with use case and dependencies."""
        state_repository = InMemoryConversationStateRepository()
        self._use_case = HandleChatTurnUseCase(state_repository)

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Handle a chat conversation turn.

        Args:
            request: Chat request DTO

        Returns:
            Chat response DTO
        """
        return await self._use_case.execute(request)

