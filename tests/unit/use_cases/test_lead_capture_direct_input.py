"""Unit tests for lead capture with direct input (no "me llamo" prefix)."""

from typing import Any, Optional

import pytest

from app.adapters.outbound.lead.lead_repository import InMemoryLeadRepository
from app.application.dtos.car import CarSummary
from app.application.dtos.chat import ChatRequest
from app.application.ports.car_catalog_repository import CarCatalogRepository
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


@pytest.mark.asyncio
async def test_lead_capture_extracts_direct_name_input():
    """Test that direct name input (e.g., 'Juan Pérez') is extracted correctly."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = InMemoryLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_direct_name_1"

    # Create a complete commercial flow state with step set to collect_contact_info
    state = ConversationState(session_id=session_id)
    state.need = "family"
    state.budget = "300000"
    state.preferences = "automatic"
    state.financing_interest = True
    state.step = "collect_contact_info"
    await state_repo.save(session_id, state)

    # Turn 1: User provides name directly (no "me llamo" prefix)
    response1 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Juan Pérez", channel="api")
    )

    # Verify name was extracted
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_name == "Juan Pérez", f"Expected 'Juan Pérez', got '{state.lead_name}'"

    # Verify lead was saved to repository
    saved_lead = await lead_repo.get(session_id)
    assert saved_lead is not None
    assert saved_lead.name == "Juan Pérez"
    assert saved_lead.phone is None
    assert saved_lead.preferred_contact_time is None

    # Verify response asks for phone (not name again)
    assert response1.next_action == "collect_contact_info"
    assert "teléfono" in response1.reply.lower() or "whatsapp" in response1.reply.lower()
    assert "cómo te llamas" not in response1.reply.lower(), "Should not ask for name again"


@pytest.mark.asyncio
async def test_lead_capture_progression_name_phone_time():
    """Test complete lead capture progression: name -> phone -> contact time."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = InMemoryLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_progression_1"

    # Create a complete commercial flow state
    state = ConversationState(session_id=session_id)
    state.need = "family"
    state.budget = "300000"
    state.preferences = "automatic"
    state.financing_interest = True
    state.step = "collect_contact_info"
    await state_repo.save(session_id, state)

    # Turn 1: User provides name
    response1 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Juan Pérez", channel="api")
    )
    assert (
        state.lead_name == "Juan Pérez"
        or (await state_repo.get(session_id)).lead_name == "Juan Pérez"
    )
    assert "teléfono" in response1.reply.lower() or "whatsapp" in response1.reply.lower()

    # Turn 2: User provides phone
    response2 = await use_case.execute(
        ChatRequest(session_id=session_id, message="+525512345678", channel="api")
    )
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_name == "Juan Pérez"
    assert state.lead_phone == "+525512345678"
    assert "horario" in response2.reply.lower() or "contact" in response2.reply.lower()

    # Turn 3: User provides contact time
    response3 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Mañana en la tarde", channel="api")
    )
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_name == "Juan Pérez"
    assert state.lead_phone == "+525512345678"
    assert state.lead_preferred_contact_time is not None
    assert response3.next_action == "handoff_to_human"
    assert "registrado" in response3.reply.lower() or "contacto" in response3.reply.lower()


@pytest.mark.asyncio
async def test_lead_capture_does_not_repeat_questions():
    """Test that lead capture does not ask for the same field twice."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = InMemoryLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_no_repeat_1"

    # Create a complete commercial flow state
    state = ConversationState(session_id=session_id)
    state.need = "family"
    state.budget = "300000"
    state.preferences = "automatic"
    state.financing_interest = True
    state.step = "collect_contact_info"
    await state_repo.save(session_id, state)

    # Turn 1: User provides name
    response1 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Juan Pérez", channel="api")
    )

    # Verify we're asking for phone, not name
    assert "cómo te llamas" not in response1.reply.lower(), (
        "Should not ask for name after it's provided"
    )
    assert "teléfono" in response1.reply.lower() or "whatsapp" in response1.reply.lower()

    # Turn 2: User provides phone
    response2 = await use_case.execute(
        ChatRequest(session_id=session_id, message="+525512345678", channel="api")
    )

    # Verify we're asking for contact time, not phone or name
    assert "teléfono" not in response2.reply.lower(), "Should not ask for phone after it's provided"
    assert "cómo te llamas" not in response2.reply.lower(), "Should not ask for name again"
    assert "horario" in response2.reply.lower() or "contact" in response2.reply.lower()
