"""Unit tests for lead capture functionality."""

from datetime import datetime
from typing import Any, Optional

import pytest

from app.adapters.outbound.lead.lead_repository import InMemoryLeadRepository
from app.application.dtos.car import CarSummary
from app.application.dtos.chat import ChatRequest
from app.application.dtos.lead import Lead
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.lead_repository import LeadRepository
from app.application.use_cases.handle_chat_turn_use_case import HandleChatTurnUseCase
from app.domain.entities.conversation_state import ConversationState


class MockConversationStateRepository:
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
        """Return mocked cars."""
        return [
            CarSummary(
                id="car_001",
                make="Toyota",
                model="Corolla",
                year=2022,
                price_mxn=350000.0,
                mileage_km=15000,
            ),
        ]


class MockLeadRepository(LeadRepository):
    """Mock lead repository for testing."""

    def __init__(self) -> None:
        """Initialize mock repository."""
        self._storage: list[Lead] = []

    async def save(self, lead: Lead) -> None:
        """Save lead."""
        # Remove existing lead for same session_id if present
        self._storage = [
            existing_lead
            for existing_lead in self._storage
            if existing_lead.session_id != lead.session_id
        ]
        self._storage.append(lead)

    async def list(self) -> list[Lead]:
        """List all leads."""
        return self._storage.copy()


@pytest.mark.asyncio
async def test_lead_repository_save_and_list():
    """Test lead repository save and list operations."""
    repository = InMemoryLeadRepository()

    lead1 = Lead(
        session_id="session_1",
        name="Juan Pérez",
        phone="+521234567890",
        preferred_contact_time="morning",
        created_at=datetime.now(),
    )

    lead2 = Lead(
        session_id="session_2",
        name="María García",
        phone="+529876543210",
        preferred_contact_time="afternoon",
        created_at=datetime.now(),
    )

    await repository.save(lead1)
    await repository.save(lead2)

    leads = await repository.list()

    assert len(leads) == 2
    assert any(lead.session_id == "session_1" and lead.name == "Juan Pérez" for lead in leads)
    assert any(lead.session_id == "session_2" and lead.name == "María García" for lead in leads)


@pytest.mark.asyncio
async def test_lead_repository_update_existing():
    """Test that saving a lead with existing session_id updates it."""
    repository = InMemoryLeadRepository()

    lead1 = Lead(
        session_id="session_1",
        name="Juan Pérez",
        phone="+521234567890",
        preferred_contact_time="morning",
        created_at=datetime.now(),
    )

    lead2 = Lead(
        session_id="session_1",
        name="Juan Pérez Updated",
        phone="+521111111111",
        preferred_contact_time="evening",
        created_at=datetime.now(),
    )

    await repository.save(lead1)
    await repository.save(lead2)

    leads = await repository.list()

    assert len(leads) == 1
    assert leads[0].name == "Juan Pérez Updated"
    assert leads[0].phone == "+521111111111"
    assert leads[0].preferred_contact_time == "evening"


@pytest.mark.asyncio
async def test_lead_capture_progression():
    """Test lead capture progression from partial to complete."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = MockLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_lead_session_1"

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
        ChatRequest(
            session_id=session_id,
            message="Sí, me interesa financiamiento",
            channel="api",
        )
    )

    # Step 5: Down payment
    await use_case.execute(
        ChatRequest(session_id=session_id, message="10% de enganche", channel="api")
    )

    # Step 6: Loan term
    await use_case.execute(ChatRequest(session_id=session_id, message="36 meses", channel="api"))

    # Step 7: After financing plans are shown, user expresses interest in scheduling
    # This should trigger lead capture
    response1 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Sí, agendar cita", channel="api")
    )

    # Verify response1 asks for contact info (should immediately ask for name)
    assert response1.next_action == "collect_contact_info"
    assert (
        "nombre" in response1.reply.lower()
        or "llamas" in response1.reply.lower()
        or "contacto" in response1.reply.lower()
    )

    # Check that step was set for lead capture
    state = await state_repo.get(session_id)
    assert state is not None
    # Step should be collect_contact_info after processing scheduling intent
    assert state.step == "collect_contact_info"

    # Step 8: User responds - should ask for name
    response2 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Ok", channel="api")
    )

    assert response2.next_action == "collect_contact_info"
    assert "nombre" in response2.reply.lower() or "llamas" in response2.reply.lower()

    # Step 9: Provide name
    response3 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Me llamo Juan Pérez", channel="api")
    )

    assert response3.next_action == "collect_contact_info"
    assert "teléfono" in response3.reply.lower() or "whatsapp" in response3.reply.lower()
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_name == "Juan Pérez"

    # Step 10: Provide phone
    response4 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Mi teléfono es 1234567890", channel="api")
    )

    assert response4.next_action == "collect_contact_info"
    assert "horario" in response4.reply.lower() or "contact" in response4.reply.lower()
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_phone is not None

    # Step 11: Provide preferred contact time
    response5 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Mañana", channel="api")
    )

    assert response5.next_action == "handoff_to_human"
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.is_lead_complete()

    # Verify lead was saved
    leads = await lead_repo.list()
    assert len(leads) == 1
    assert leads[0].session_id == session_id
    assert leads[0].name == "Juan Pérez"
    assert leads[0].phone is not None
    assert leads[0].preferred_contact_time is not None


@pytest.mark.asyncio
async def test_lead_capture_next_action_transitions():
    """Test that next_action transitions correctly during lead capture."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = MockLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_next_action_1"

    # Create a complete state manually to test lead capture directly
    state = ConversationState(session_id=session_id)
    state.need = "family"
    state.budget = "300000"
    state.preferences = "automatic"
    state.financing_interest = True
    state.step = "collect_contact_info"
    await state_repo.save(session_id, state)

    # Test asking for name
    response1 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Hola", channel="api")
    )

    assert response1.next_action == "collect_contact_info"

    # Provide name
    state.lead_name = "María"
    await state_repo.save(session_id, state)
    response2 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Mi nombre es María", channel="api")
    )

    assert response2.next_action == "collect_contact_info"

    # Provide phone
    state.lead_phone = "+521234567890"
    await state_repo.save(session_id, state)
    response3 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Mi teléfono es 1234567890", channel="api")
    )

    assert response3.next_action == "collect_contact_info"

    # Provide preferred contact time
    state.lead_preferred_contact_time = "afternoon"
    await state_repo.save(session_id, state)
    response4 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Tarde", channel="api")
    )

    assert response4.next_action == "handoff_to_human"


@pytest.mark.asyncio
async def test_lead_extraction_patterns():
    """Test extraction of name, phone, and contact time from various formats."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = MockLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_extraction_1"

    # Create complete state
    state = ConversationState(session_id=session_id)
    state.need = "family"
    state.budget = "300000"
    state.preferences = "automatic"
    state.financing_interest = True
    state.step = "collect_contact_info"
    await state_repo.save(session_id, state)

    # Test name extraction - "me llamo"
    await use_case.execute(
        ChatRequest(session_id=session_id, message="Me llamo Carlos Rodríguez", channel="api")
    )
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_name == "Carlos Rodríguez"

    # Test phone extraction
    state.lead_name = "Carlos"
    await state_repo.save(session_id, state)
    await use_case.execute(ChatRequest(session_id=session_id, message="5551234567", channel="api"))
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_phone is not None

    # Test preferred contact time extraction
    state.lead_phone = "+525551234567"
    await state_repo.save(session_id, state)
    await use_case.execute(
        ChatRequest(session_id=session_id, message="Prefiero la noche", channel="api")
    )
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_preferred_contact_time is not None


@pytest.mark.asyncio
async def test_lead_capture_triggered_by_purchase_intent():
    """Test that purchase intent keywords trigger lead capture."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = MockLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_purchase_intent_1"

    # Complete commercial flow
    await use_case.execute(
        ChatRequest(session_id=session_id, message="Auto familiar", channel="api")
    )
    await use_case.execute(ChatRequest(session_id=session_id, message="$300,000", channel="api"))
    await use_case.execute(ChatRequest(session_id=session_id, message="Automática", channel="api"))
    await use_case.execute(
        ChatRequest(
            session_id=session_id,
            message="Sí, me interesa financiamiento",
            channel="api",
        )
    )
    await use_case.execute(
        ChatRequest(session_id=session_id, message="10% de enganche", channel="api")
    )
    await use_case.execute(ChatRequest(session_id=session_id, message="36 meses", channel="api"))

    # Express purchase intent - should trigger lead capture
    response = await use_case.execute(
        ChatRequest(session_id=session_id, message="Quiero comprar", channel="api")
    )

    state = await state_repo.get(session_id)
    assert state is not None
    # Should either be in collect_contact_info or next step should be ask_contact_info
    assert state.step in ["collect_contact_info", "next_action"] or response.next_action in [
        "collect_contact_info",
        "ask_contact_info",
    ]
