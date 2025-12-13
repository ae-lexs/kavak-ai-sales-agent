"""Dependency injection factory functions."""

from typing import Optional

from app.adapters.outbound.catalog.csv_car_catalog_repository import (
    CSVCarCatalogRepository,
)
from app.adapters.outbound.knowledge_base.local_markdown_knowledge_base_repository import (
    LocalMarkdownKnowledgeBaseRepository,
)
from app.adapters.outbound.lead.lead_repository import InMemoryLeadRepository
from app.adapters.outbound.llm.openai_llm_client import OpenAILLMClient
from app.adapters.outbound.state.conversation_state_repository import (
    InMemoryConversationStateRepository,
)
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.ports.knowledge_base_repository import KnowledgeBaseRepository
from app.application.ports.lead_repository import LeadRepository
from app.application.ports.llm_client import LLMClient
from app.application.use_cases.answer_faq_with_rag import AnswerFaqWithRag
from app.application.use_cases.handle_chat_turn_use_case import HandleChatTurnUseCase
from app.infrastructure.config.settings import settings
from app.infrastructure.logging.logger import log_turn


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


def create_llm_client() -> Optional[LLMClient]:
    """
    Factory function to create LLM client if enabled.

    Returns:
        LLMClient instance if enabled, None otherwise
    """
    if not settings.llm_enabled:
        return None

    try:
        return OpenAILLMClient()
    except (ValueError, Exception):
        # If API key is missing or client creation fails, return None
        # This allows the use case to fall back to deterministic responses
        return None


def create_faq_rag_service() -> AnswerFaqWithRag:
    """
    Factory function to create FAQ RAG service.

    Returns:
        AnswerFaqWithRag instance
    """
    knowledge_base_repository = create_knowledge_base_repository()
    llm_client = create_llm_client()
    return AnswerFaqWithRag(knowledge_base_repository, llm_client=llm_client)


def create_lead_repository() -> LeadRepository:
    """
    Factory function to create lead repository.

    Returns:
        LeadRepository instance
    """
    return InMemoryLeadRepository()


def create_handle_chat_turn_use_case() -> HandleChatTurnUseCase:
    """
    Factory function to create HandleChatTurnUseCase with dependencies.

    Returns:
        HandleChatTurnUseCase instance
    """
    state_repository = create_conversation_state_repository()
    car_catalog_repository = create_car_catalog_repository()
    lead_repository = create_lead_repository()
    faq_rag_service = create_faq_rag_service()

    # Wire logger function
    def _logger_func(session_id, turn_id, component, **kwargs):
        log_turn(session_id, turn_id, component, **kwargs)

    return HandleChatTurnUseCase(
        state_repository,
        car_catalog_repository,
        lead_repository,
        faq_rag_service,
        logger=_logger_func,
    )
