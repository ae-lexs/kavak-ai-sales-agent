"""Golden tests for commercial flow to prevent regressions."""

from typing import Any, Optional

import pytest

from app.application.dtos.car import CarSummary
from app.application.dtos.chat import ChatRequest
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.ports.lead_repository import LeadRepository
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


class InMemoryLeadRepositoryForGolden(LeadRepository):
    """In-memory lead repository for golden tests."""

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        from app.application.dtos.lead import Lead

        self._storage: list[Lead] = []

    async def get(self, session_id: str) -> Optional[Any]:
        """Get lead by session_id."""

        for lead in self._storage:
            if lead.session_id == session_id:
                return lead
        return None

    async def save(self, lead: Any) -> None:
        """Save lead."""
        # Remove existing lead for same session_id if present
        self._storage = [
            existing_lead
            for existing_lead in self._storage
            if existing_lead.session_id != lead.session_id
        ]
        self._storage.append(lead)

    async def list(self) -> list[Any]:
        """List all leads."""
        return self._storage.copy()


@pytest.fixture
def use_case():
    """Create use case with mock dependencies."""
    state_repo = InMemoryStateRepository()
    car_repo = MockCarCatalogRepository()
    return HandleChatTurnUseCase(
        state_repo, car_repo, lead_repository=None, faq_rag_service=None, logger=None
    )


@pytest.fixture
def use_case_with_lead_repo():
    """Create use case with lead repository for lead capture tests."""
    state_repo = InMemoryStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = InMemoryLeadRepositoryForGolden()
    return HandleChatTurnUseCase(
        state_repo, car_repo, lead_repository=lead_repo, faq_rag_service=None, logger=None
    ), lead_repo


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
    # Verify improved formatting: no raw numbering or section headers
    assert "8. " not in response.reply and "2. " not in response.reply
    assert "Periodo de Prueba y Garantía" not in response.reply
    assert "Presencia Nacional" not in response.reply


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


@pytest.mark.asyncio
async def test_golden_lead_capture_complete_flow(use_case_with_lead_repo):
    """Golden test: Complete lead capture flow from start to finish."""
    use_case, lead_repo = use_case_with_lead_repo
    session_id = "golden_lead_capture_session"

    # Complete commercial flow first
    # Step 1: Need
    await use_case.execute(
        ChatRequest(session_id=session_id, message="Auto familiar", channel="api")
    )

    # Step 2: Budget
    await use_case.execute(ChatRequest(session_id=session_id, message="$300,000", channel="api"))

    # Step 3: Preferences
    await use_case.execute(ChatRequest(session_id=session_id, message="Automática", channel="api"))

    # Step 4: Financing interest
    await use_case.execute(
        ChatRequest(session_id=session_id, message="Sí, me interesa financiamiento", channel="api")
    )

    # Step 5: Down payment
    await use_case.execute(
        ChatRequest(session_id=session_id, message="10% de enganche", channel="api")
    )

    # Step 6: Loan term
    await use_case.execute(ChatRequest(session_id=session_id, message="36 meses", channel="api"))

    # Step 7: Trigger lead capture
    response1 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Sí, agendar cita", channel="api")
    )

    # Assert: Should ask for name (first field)
    assert response1.next_action == "collect_contact_info"
    assert "nombre" in response1.reply.lower() or "llamas" in response1.reply.lower()
    assert all(isinstance(q, str) for q in response1.suggested_questions)

    # Step 8: Provide name (test direct input without "me llamo" prefix)
    response2 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Juan Pérez", channel="api")
    )

    # Assert: Should ask for phone (not name again)
    assert response2.next_action == "collect_contact_info"
    assert "teléfono" in response2.reply.lower() or "whatsapp" in response2.reply.lower()
    assert "cómo te llamas" not in response2.reply.lower(), (
        "Should not ask for name again after it's provided"
    )

    # Verify name was saved (partial lead)
    saved_lead = await lead_repo.get(session_id)
    assert saved_lead is not None
    assert saved_lead.name == "Juan Pérez"
    assert saved_lead.phone is None
    assert saved_lead.preferred_contact_time is None

    # Step 9: Provide phone (test direct input)
    response3 = await use_case.execute(
        ChatRequest(session_id=session_id, message="+525512345678", channel="api")
    )

    # Assert: Should ask for preferred contact time (not phone or name again)
    assert response3.next_action == "collect_contact_info"
    assert "horario" in response3.reply.lower() or "contact" in response3.reply.lower()
    assert "teléfono" not in response3.reply.lower(), "Should not ask for phone after it's provided"
    assert "cómo te llamas" not in response3.reply.lower(), "Should not ask for name again"

    # Verify phone was saved (name preserved)
    saved_lead = await lead_repo.get(session_id)
    assert saved_lead is not None
    assert saved_lead.name == "Juan Pérez"  # Name preserved
    assert saved_lead.phone is not None  # Phone added
    assert "+52" in saved_lead.phone or "1234567890" in saved_lead.phone

    # Step 10: Provide preferred contact time (test with "Mañana en la tarde"
    # to verify "tarde" is extracted)
    response4 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Mañana en la tarde", channel="api")
    )

    # Assert: Should complete and set handoff_to_human
    assert response4.next_action == "handoff_to_human"
    assert "asesor" in response4.reply.lower() or "contacto" in response4.reply.lower()

    # Verify complete lead was saved
    saved_lead = await lead_repo.get(session_id)
    assert saved_lead is not None
    assert saved_lead.name == "Juan Pérez"
    assert saved_lead.phone is not None
    assert "+525512345678" in saved_lead.phone or saved_lead.phone == "+521234567890"
    assert saved_lead.preferred_contact_time is not None
    # "Mañana en la tarde" should extract "afternoon" (tarde), not "morning" (mañana)
    assert saved_lead.preferred_contact_time.lower() in ["afternoon", "tarde"]

    # Assert all responses are in Spanish
    import re

    for response in [response1, response2, response3, response4]:
        english_indicators = ["what", "choose", "select", "please", "thank you"]
        reply_lower = response.reply.lower()
        for indicator in english_indicators:
            # Use word boundaries to avoid false positives (e.g., "whatsapp" contains "what")
            pattern = r"\b" + re.escape(indicator) + r"\b"
            if re.search(pattern, reply_lower):
                raise AssertionError(
                    f"Found English indicator '{indicator}' in reply: {response.reply}"
                )
