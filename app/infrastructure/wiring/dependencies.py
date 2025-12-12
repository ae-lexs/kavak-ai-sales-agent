"""Dependency injection factory functions."""

from app.adapters.outbound.catalog.csv_car_catalog_repository import (
    CSVCarCatalogRepository,
)
from app.adapters.outbound.knowledge_base.local_markdown_knowledge_base_repository import (
    LocalMarkdownKnowledgeBaseRepository,
)
from app.adapters.outbound.state.conversation_state_repository import (
    InMemoryConversationStateRepository,
)
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.ports.knowledge_base_repository import KnowledgeBaseRepository
from app.application.use_cases.answer_faq_with_rag import AnswerFaqWithRag
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
    return CSVCarCatalogRepository()


def create_knowledge_base_repository() -> KnowledgeBaseRepository:
    """
    Factory function to create knowledge base repository.

    Returns:
        KnowledgeBaseRepository instance
    """
    return LocalMarkdownKnowledgeBaseRepository()


def create_faq_rag_service() -> AnswerFaqWithRag:
    """
    Factory function to create FAQ RAG service.

    Returns:
        AnswerFaqWithRag instance
    """
    knowledge_base_repository = create_knowledge_base_repository()
    return AnswerFaqWithRag(knowledge_base_repository)


def create_handle_chat_turn_use_case() -> HandleChatTurnUseCase:
    """
    Factory function to create HandleChatTurnUseCase with dependencies.

    Returns:
        HandleChatTurnUseCase instance
    """
    state_repository = create_conversation_state_repository()
    car_catalog_repository = create_car_catalog_repository()
    faq_rag_service = create_faq_rag_service()
    return HandleChatTurnUseCase(state_repository, car_catalog_repository, faq_rag_service)
