"""Golden tests for commercial flow to prevent regressions."""

from typing import Any, Optional

import pytest

from app.application.dtos.car import CarSummary
from app.application.dtos.chat import ChatRequest
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.use_cases.handle_chat_turn_use_case import HandleChatTurnUseCase
from app.domain.entities.conversation_state import ConversationState


class MockCarCatalogRepository(CarCatalogRepository):
    """Mock car catalog repository for golden tests."""

    async def search(self, filters: dict[str, Any]) -> list[CarSummary]:
        """Return mock cars matching filters."""
        # Return consistent mock data for golden tests
        return [
            CarSummary(
                id="car_001",
                make="Toyota",
                model="Corolla",
                year=2022,
                price_mxn=350000.0,
                mileage_km=15000,
            ),
            CarSummary(
                id="car_002",
                make="Honda",
                model="Civic",
                year=2021,
                price_mxn=320000.0,
                mileage_km=25000,
            ),
        ]


class InMemoryStateRepository(ConversationStateRepository):
    """In-memory state repository for golden tests."""

    def __init__(self) -> None:
        """Initialize in-memory storage."""
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


@pytest.fixture
def use_case():
    """Create use case with mock dependencies."""
    state_repo = InMemoryStateRepository()
    car_repo = MockCarCatalogRepository()
    return HandleChatTurnUseCase(
        state_repo, car_repo, lead_repository=None, faq_rag_service=None, logger=None
    )


@pytest.mark.asyncio
async def test_golden_commercial_flow_happy_path(use_case):
    """Golden test: Happy path commercial flow in Spanish."""
    session_id = "golden_test_session"

    # Step 1: User expresses need
    request1 = ChatRequest(
        session_id=session_id,
        message="Estoy buscando un auto familiar",
        channel="api",
    )
    response1 = await use_case.execute(request1)

    # Assert: Should ask for budget
    assert response1.next_action == "ask_budget"
    assert "presupuesto" in response1.reply.lower() or "presupuest" in response1.reply.lower()
    assert all(isinstance(q, str) and len(q) > 0 for q in response1.suggested_questions)
    # Assert Spanish-only (no obvious English)
    assert "what" not in response1.reply.lower()
    assert "choose" not in response1.reply.lower()
    assert "select" not in response1.reply.lower()

    # Step 2: User provides budget
    request2 = ChatRequest(
        session_id=session_id,
        message="Mi presupuesto es $300,000",
        channel="api",
    )
    response2 = await use_case.execute(request2)

    # Assert: Should show options and ask about financing (after budget, it shows cars)
    assert response2.next_action == "ask_financing"
    assert all(isinstance(q, str) and len(q) > 0 for q in response2.suggested_questions)
    # Assert Spanish-only
    assert "what" not in response2.reply.lower()
    assert "choose" not in response2.reply.lower()

    # Step 3: User asks about financing
    request3 = ChatRequest(
        session_id=session_id,
        message="Sí, me interesa el financiamiento",
        channel="api",
    )
    response3 = await use_case.execute(request3)

    # Assert: May ask for preferences first (if missing) or down payment
    # The flow checks missing fields, so preferences might be asked first
    assert response3.next_action in ["ask_down_payment", "ask_preferences"]
    assert all(isinstance(q, str) and len(q) > 0 for q in response3.suggested_questions)
    # Assert Spanish-only
    assert "what" not in response3.reply.lower()
    assert "down payment" not in response3.reply.lower()

    # If preferences are asked, provide them and continue
    if response3.next_action == "ask_preferences":
        request4 = ChatRequest(
            session_id=session_id,
            message="Automático",
            channel="api",
        )
        response4 = await use_case.execute(request4)
        # Now should ask for down payment
        assert response4.next_action == "ask_down_payment"
        assert "enganche" in response4.reply.lower() or "pago inicial" in response4.reply.lower()
    else:
        # Already asking for down payment
        assert "enganche" in response3.reply.lower() or "pago inicial" in response3.reply.lower()


@pytest.mark.asyncio
async def test_golden_faq_intent_routing_without_rag(use_case):
    """Golden test: FAQ intent without RAG service continues commercial flow."""
    session_id = "golden_faq_test_session"

    # FAQ keyword question
    request = ChatRequest(
        session_id=session_id,
        message="¿Qué garantías ofrecen?",
        channel="api",
    )
    response = await use_case.execute(request)

    # Without RAG service, should continue in commercial flow
    assert response.next_action in [
        "ask_need",
        "ask_budget",
        "ask_preferences",
        "ask_financing",
        "continue_conversation",
        "complete",
    ]
    assert all(isinstance(q, str) and len(q) > 0 for q in response.suggested_questions)
    # Assert Spanish-only
    assert "what" not in response.reply.lower()
    assert (
        "guarantee" not in response.reply.lower()
        or "garantía" in response.reply.lower()
        or "garantia" in response.reply.lower()
    )


@pytest.mark.asyncio
async def test_golden_faq_intent_routing_with_rag():
    """Golden test: FAQ intent routing to RAG service."""
    from app.adapters.outbound.knowledge_base.local_markdown_knowledge_base_repository import (
        LocalMarkdownKnowledgeBaseRepository,
    )
    from app.application.use_cases.answer_faq_with_rag import AnswerFaqWithRag

    # Create use case with RAG service
    state_repo = InMemoryStateRepository()
    car_repo = MockCarCatalogRepository()
    knowledge_repo = LocalMarkdownKnowledgeBaseRepository()
    faq_service = AnswerFaqWithRag(knowledge_repo)
    use_case = HandleChatTurnUseCase(
        state_repo, car_repo, lead_repository=None, faq_rag_service=faq_service, logger=None
    )

    session_id = "golden_faq_rag_test_session"

    # FAQ keyword question
    request = ChatRequest(
        session_id=session_id,
        message="¿Qué garantías ofrecen?",
        channel="api",
    )
    response = await use_case.execute(request)

    # With RAG service, should route to FAQ
    assert response.next_action == "continue_conversation"
    assert response.debug is not None
    assert response.debug.get("intent") == "faq" or response.debug.get("step") == "faq_rag"
    assert all(isinstance(q, str) and len(q) > 0 for q in response.suggested_questions)
    # Assert Spanish-only
    assert "what" not in response.reply.lower()
    # RAG may return fallback if no relevant chunks found, or warranty content if found
    # Both are valid - just ensure it's in Spanish and grounded in KB content
    reply_lower = response.reply.lower()
    # Should contain warranty-related terms or fallback message (both are valid)
    assert (
        "garantía" in reply_lower
        or "garantia" in reply_lower
        or "garantiza" in reply_lower
        or "información" in reply_lower
        or "kavak" in reply_lower
    )


@pytest.mark.asyncio
async def test_golden_spanish_only_outputs(use_case):
    """Golden test: All outputs are Spanish-only."""
    session_id = "golden_spanish_test_session"

    test_messages = [
        "Quiero un auto",
        "Mi presupuesto es $200,000",
        "Automático",
        "Sí, quiero financiamiento",
    ]

    for message in test_messages:
        request = ChatRequest(
            session_id=session_id,
            message=message,
            channel="api",
        )
        response = await use_case.execute(request)

        # Assert reply is in Spanish (no obvious English words)
        english_indicators = ["what", "choose", "select", "please", "thank you", "hello", "hi"]
        reply_lower = response.reply.lower()
        for indicator in english_indicators:
            assert indicator not in reply_lower, (
                f"Found English indicator '{indicator}' in reply: {response.reply}"
            )

        # Assert suggested questions are in Spanish
        for question in response.suggested_questions:
            question_lower = question.lower()
            for indicator in english_indicators:
                assert indicator not in question_lower, (
                    f"Found English indicator '{indicator}' in question: {question}"
                )
