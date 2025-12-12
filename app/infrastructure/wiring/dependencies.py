"""Dependency injection factory functions."""

from app.adapters.outbound.catalog_csv.mock_car_catalog_repository import (
    MockCarCatalogRepository,
)
from app.adapters.outbound.state.conversation_state_repository import (
    InMemoryConversationStateRepository,
)
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.use_cases.handle_chat_turn_use_case import HandleChatTurnUseCase


def create_conversation_state_repository() -> ConversationStateRepository:
    """
    Factory function to create conversation state repository.

    Returns:
        ConversationStateRepository instance
    """
    return InMemoryConversationStateRepository()


def create_car_catalog_repository() -> CarCatalogRepository:
    """
    Factory function to create car catalog repository.

    Returns:
        CarCatalogRepository instance
    """
    return MockCarCatalogRepository()


def create_handle_chat_turn_use_case() -> HandleChatTurnUseCase:
    """
    Factory function to create HandleChatTurnUseCase with dependencies.

    Returns:
        HandleChatTurnUseCase instance
    """
    state_repository = create_conversation_state_repository()
    car_catalog_repository = create_car_catalog_repository()
    return HandleChatTurnUseCase(state_repository, car_catalog_repository)
