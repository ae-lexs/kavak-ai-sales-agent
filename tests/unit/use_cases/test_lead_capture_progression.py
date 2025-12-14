"""Unit tests for lead capture progression with partial saves."""

from datetime import datetime, timezone
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
async def test_partial_lead_capture_persists_name():
    """Test that partial lead capture (name only) persists correctly."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = InMemoryLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_partial_1"

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
        ChatRequest(session_id=session_id, message="Me llamo Juan Pérez", channel="api")
    )

    # Verify name was extracted
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_name == "Juan Pérez"

    # Verify lead was saved to repository (partial)
    saved_lead = await lead_repo.get(session_id)
    assert saved_lead is not None
    assert saved_lead.name == "Juan Pérez"
    assert saved_lead.phone is None
    assert saved_lead.preferred_contact_time is None

    # Verify response asks for phone
    assert response1.next_action == "collect_contact_info"
    assert "teléfono" in response1.reply.lower() or "whatsapp" in response1.reply.lower()


@pytest.mark.asyncio
async def test_lead_capture_progression_name_to_phone():
    """Test that providing phone after name preserves name and saves both."""
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
    state.lead_name = "María García"  # Name already collected
    await state_repo.save(session_id, state)

    # Save partial lead with name
    from app.application.dtos.lead import Lead

    partial_lead = Lead(
        session_id=session_id,
        name="María García",
        phone=None,
        preferred_contact_time=None,
        created_at=datetime.now(timezone.utc),
    )
    await lead_repo.save(partial_lead)

    # Turn: User provides phone
    response = await use_case.execute(
        ChatRequest(session_id=session_id, message="Mi teléfono es 1234567890", channel="api")
    )

    # Verify phone was extracted
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_phone is not None
    assert "+52" in state.lead_phone or "1234567890" in state.lead_phone

    # Verify lead was updated in repository (name preserved, phone added)
    saved_lead = await lead_repo.get(session_id)
    assert saved_lead is not None
    assert saved_lead.name == "María García"  # Name preserved
    assert saved_lead.phone is not None  # Phone added
    assert saved_lead.preferred_contact_time is None  # Still missing

    # Verify response asks for preferred contact time
    assert response.next_action == "collect_contact_info"
    assert "horario" in response.reply.lower() or "contact" in response.reply.lower()


@pytest.mark.asyncio
async def test_lead_capture_completion_sets_handoff():
    """Test that completing all fields sets next_action to handoff_to_human."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = InMemoryLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_completion_1"

    # Create a complete commercial flow state with name and phone
    state = ConversationState(session_id=session_id)
    state.need = "family"
    state.budget = "300000"
    state.preferences = "automatic"
    state.financing_interest = True
    state.step = "collect_contact_info"
    state.lead_name = "Carlos López"
    state.lead_phone = "+521234567890"
    await state_repo.save(session_id, state)

    # Turn: User provides preferred contact time
    response = await use_case.execute(
        ChatRequest(session_id=session_id, message="Mañana", channel="api")
    )

    # Verify all fields are complete
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.is_lead_complete()
    assert state.step == "handoff_to_human"

    # Verify lead was saved complete
    saved_lead = await lead_repo.get(session_id)
    assert saved_lead is not None
    assert saved_lead.name == "Carlos López"
    assert saved_lead.phone == "+521234567890"
    assert saved_lead.preferred_contact_time is not None

    # Verify response indicates handoff
    assert response.next_action == "handoff_to_human"
    assert "asesor" in response.reply.lower() or "contacto" in response.reply.lower()


@pytest.mark.asyncio
async def test_lead_capture_loads_existing_lead():
    """Test that existing lead is loaded and merged when starting lead capture."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    lead_repo = InMemoryLeadRepository()
    use_case = HandleChatTurnUseCase(state_repo, car_repo, lead_repo)

    session_id = "test_load_existing_1"

    # Create a complete commercial flow state
    state = ConversationState(session_id=session_id)
    state.need = "family"
    state.budget = "300000"
    state.preferences = "automatic"
    state.financing_interest = True
    state.step = "next_action"
    await state_repo.save(session_id, state)

    # Save a partial lead with name
    from app.application.dtos.lead import Lead

    existing_lead = Lead(
        session_id=session_id,
        name="Ana Martínez",
        phone=None,
        preferred_contact_time=None,
        created_at=datetime.now(timezone.utc),
    )
    await lead_repo.save(existing_lead)

    # Trigger lead capture
    response = await use_case.execute(
        ChatRequest(session_id=session_id, message="Sí, agendar cita", channel="api")
    )

    # Verify existing lead was loaded into state
    state = await state_repo.get(session_id)
    assert state is not None
    assert state.lead_name == "Ana Martínez"  # Loaded from repository
    assert state.step == "collect_contact_info"

    # Verify response asks for phone (not name, since name is already loaded)
    assert response.next_action == "collect_contact_info"
    assert "teléfono" in response.reply.lower() or "whatsapp" in response.reply.lower()


@pytest.mark.asyncio
async def test_lead_capture_upsert_behavior():
    """Test that saving partial lead then complete lead updates correctly."""
    lead_repo = InMemoryLeadRepository()

    from app.application.dtos.lead import Lead

    session_id = "test_upsert_1"
    created_at = datetime.now(timezone.utc)

    # Save partial lead with name
    partial_lead = Lead(
        session_id=session_id,
        name="Pedro Sánchez",
        phone=None,
        preferred_contact_time=None,
        created_at=created_at,
    )
    await lead_repo.save(partial_lead)

    # Verify partial lead
    saved = await lead_repo.get(session_id)
    assert saved is not None
    assert saved.name == "Pedro Sánchez"
    assert saved.phone is None

    # Save complete lead (upsert)
    complete_lead = Lead(
        session_id=session_id,
        name="Pedro Sánchez",
        phone="+529876543210",
        preferred_contact_time="afternoon",
        created_at=created_at,  # Preserve original created_at
    )
    await lead_repo.save(complete_lead)

    # Verify complete lead
    saved = await lead_repo.get(session_id)
    assert saved is not None
    assert saved.name == "Pedro Sánchez"
    assert saved.phone == "+529876543210"
    assert saved.preferred_contact_time == "afternoon"
    assert saved.created_at == created_at  # Preserved
