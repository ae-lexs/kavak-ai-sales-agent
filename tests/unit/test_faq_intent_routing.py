"""Unit tests for FAQ intent routing in HandleChatTurnUseCase."""

from typing import Any, Optional

import pytest

from app.application.dtos.car import CarSummary
from app.application.dtos.chat import ChatRequest
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.use_cases.answer_faq_with_rag import AnswerFaqWithRag
from app.application.use_cases.handle_chat_turn_use_case import HandleChatTurnUseCase
from app.domain.entities.conversation_state import ConversationState


class MockConversationStateRepository(ConversationStateRepository):
    """Mock repository for testing."""

    def __init__(self) -> None:
        """Initialize mock repository."""
        self._storage: dict[str, ConversationState] = {}

    async def get(self, session_id: str) -> Optional[ConversationState]:
        """Get conversation state."""
        return self._storage.get(session_id)

    async def save(self, session_id: str, state: ConversationState) -> None:
        """Save conversation state."""
        self._storage[session_id] = state

    async def delete(self, session_id: str) -> None:
        """Delete conversation state."""
        if session_id in self._storage:
            del self._storage[session_id]


class MockCarCatalogRepository(CarCatalogRepository):
    """Mock car catalog repository for testing."""

    async def search(self, filters: dict[str, Any]) -> list[CarSummary]:
        """Return empty list."""
        return []


class MockFaqRagService(AnswerFaqWithRag):
    """Mock FAQ RAG service for testing."""

    def __init__(self) -> None:
        """Initialize mock service."""
        # Don't call super().__init__ to avoid needing a real repository
        pass

    def execute(self, query: str) -> tuple[str, list[str]]:
        """Return mock FAQ response."""
        return (
            "Esta es una respuesta de prueba sobre garantías. Kavak ofrece garantía en todos los vehículos certificados.",  # noqa: E501
            ["¿Cómo funciona la entrega?", "¿Puedo financiar mi compra?"],
        )


@pytest.mark.asyncio
async def test_faq_intent_routes_to_rag():
    """Test that FAQ intent routes to RAG service."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    faq_service = MockFaqRagService()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, faq_service)

    request = ChatRequest(
        session_id="test_session",
        message="¿Qué garantías ofrecen?",
        channel="api",
    )

    response = await use_case.execute(request)

    # Should route to RAG
    assert response.next_action == "continue_conversation"
    assert "garantía" in response.reply.lower() or "garantia" in response.reply.lower()
    assert len(response.suggested_questions) > 0
    # Debug should indicate FAQ
    assert response.debug is not None
    assert response.debug.get("intent") == "faq" or response.debug.get("step") == "faq_rag"


@pytest.mark.asyncio
async def test_faq_intent_with_garantia_keyword():
    """Test that 'garantía' keyword triggers FAQ routing."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    faq_service = MockFaqRagService()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, faq_service)

    request = ChatRequest(
        session_id="test_session",
        message="Quiero saber sobre la garantía",
        channel="api",
    )

    response = await use_case.execute(request)

    assert response.next_action == "continue_conversation"
    assert response.debug is not None


@pytest.mark.asyncio
async def test_faq_intent_with_devolucion_keyword():
    """Test that 'devolución' keyword triggers FAQ routing."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    faq_service = MockFaqRagService()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, faq_service)

    request = ChatRequest(
        session_id="test_session",
        message="¿Cómo funciona la devolución?",
        channel="api",
    )

    response = await use_case.execute(request)

    assert response.next_action == "continue_conversation"
    assert response.debug is not None


@pytest.mark.asyncio
async def test_faq_intent_with_inspeccion_keyword():
    """Test that 'inspección' keyword triggers FAQ routing."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    faq_service = MockFaqRagService()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, faq_service)

    request = ChatRequest(
        session_id="test_session",
        message="¿Qué es la inspección?",
        channel="api",
    )

    response = await use_case.execute(request)

    assert response.next_action == "continue_conversation"
    assert response.debug is not None


@pytest.mark.asyncio
async def test_non_faq_stays_in_commercial_flow():
    """Test that non-FAQ messages stay in commercial flow."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    faq_service = MockFaqRagService()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, faq_service)

    request = ChatRequest(
        session_id="test_session",
        message="Estoy buscando un auto familiar",
        channel="api",
    )

    response = await use_case.execute(request)

    # Should NOT route to RAG
    assert (
        response.next_action != "continue_conversation"
        or response.debug is None
        or response.debug.get("intent") != "faq"
    )
    # Should be in commercial flow (ask_need, ask_budget, etc.)
    assert response.next_action in [
        "ask_need",
        "ask_budget",
        "ask_preferences",
        "ask_financing",
        "complete",
    ]


@pytest.mark.asyncio
async def test_faq_intent_with_kavak_keyword():
    """Test that 'kavak' keyword triggers FAQ routing."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    faq_service = MockFaqRagService()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, faq_service)

    request = ChatRequest(
        session_id="test_session",
        message="¿Qué es Kavak?",
        channel="api",
    )

    response = await use_case.execute(request)

    assert response.next_action == "continue_conversation"
    assert response.debug is not None


@pytest.mark.asyncio
async def test_faq_intent_without_service_continues_normal_flow():
    """Test that FAQ intent without service continues normal flow."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    # No FAQ service provided
    use_case = HandleChatTurnUseCase(state_repo, car_repo, None)

    request = ChatRequest(
        session_id="test_session",
        message="¿Qué garantías ofrecen?",
        channel="api",
    )

    response = await use_case.execute(request)

    # Should continue in normal flow since no FAQ service
    assert response.next_action in [
        "ask_need",
        "ask_budget",
        "ask_preferences",
        "ask_financing",
        "complete",
    ]
