"""Dependency injection container."""

from app.adapters.outbound.catalog_csv.mock_car_catalog_repository import (
    MockCarCatalogRepository,
)
from app.adapters.outbound.conversation_state_repository.conversation_state_repository import (
    InMemoryConversationStateRepository,
)
from app.adapters.outbound.llm_rag.chat_adapter import LLMRAGChatAdapter
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.use_cases.chat_use_case import ChatUseCase


class Container:
    """Dependency injection container."""

    def __init__(self) -> None:
        """Initialize container with dependencies."""
        # State repository
        self._state_repository: ConversationStateRepository = InMemoryConversationStateRepository()

        # Car catalog repository
        self._car_catalog_repository: CarCatalogRepository = MockCarCatalogRepository()

        # Chat adapter (uses state repository and car catalog repository)
        self._chat_adapter = LLMRAGChatAdapter(self._state_repository, self._car_catalog_repository)

        # Use cases
        self._chat_use_case = ChatUseCase(self._chat_adapter)

    @property
    def chat_use_case(self) -> ChatUseCase:
        """Get chat use case."""
        return self._chat_use_case

    @property
    def state_repository(self) -> ConversationStateRepository:
        """Get state repository."""
        return self._state_repository


# Global container instance
container = Container()
