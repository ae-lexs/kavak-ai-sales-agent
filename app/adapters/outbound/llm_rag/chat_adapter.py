"""Chat adapter implementation."""

from app.application.dtos.chat import ChatRequest, ChatResponse
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.chat_port import ChatPort
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.use_cases.handle_chat_turn_use_case import HandleChatTurnUseCase


class LLMRAGChatAdapter(ChatPort):
    """LLM/RAG-based chat adapter implementation."""

    def __init__(
        self,
        state_repository: ConversationStateRepository,
        car_catalog_repository: CarCatalogRepository,
    ) -> None:
        """
        Initialize chat adapter with use case and dependencies.

        Args:
            state_repository: Conversation state repository
            car_catalog_repository: Car catalog repository
        """
        self._use_case = HandleChatTurnUseCase(state_repository, car_catalog_repository)

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Handle a chat conversation turn.

        Args:
            request: Chat request DTO

        Returns:
            Chat response DTO
        """
        return await self._use_case.execute(request)
