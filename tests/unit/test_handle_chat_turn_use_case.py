"""Unit tests for HandleChatTurnUseCase."""

from typing import Any, Optional

import pytest

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
            CarSummary(
                id="car_002",
                make="Honda",
                model="Civic",
                year=2021,
                price_mxn=320000.0,
                mileage_km=25000,
            ),
        ]


@pytest.mark.asyncio
async def test_handle_chat_turn_initial_greeting():
    """Test initial greeting when no state exists."""
    repository = MockConversationStateRepository()
    catalog_repository = MockCarCatalogRepository()
    use_case = HandleChatTurnUseCase(repository, catalog_repository)

    request = ChatRequest(
        session_id="test_session_1",
        message="Hola",
        channel="api",
    )

    response = await use_case.execute(request)

    assert response.session_id == "test_session_1"
    assert "Hola" in response.reply or "auto" in response.reply.lower()
    assert response.next_action == "ask_need"
    assert len(response.suggested_questions) > 0
    assert response.debug is not None


@pytest.mark.asyncio
async def test_handle_chat_turn_extract_need():
    """Test extracting need from message."""
    repository = MockConversationStateRepository()
    catalog_repository = MockCarCatalogRepository()
    use_case = HandleChatTurnUseCase(repository, catalog_repository)

    request = ChatRequest(
        session_id="test_session_2",
        message="Necesito un auto familiar",
        channel="api",
    )

    response = await use_case.execute(request)

    assert response.session_id == "test_session_2"
    assert response.next_action == "ask_budget"
    assert response.debug.get("need") == "family"


@pytest.mark.asyncio
async def test_handle_chat_turn_extract_budget():
    """Test extracting budget from message."""
    repository = MockConversationStateRepository()
    catalog_repository = MockCarCatalogRepository()
    use_case = HandleChatTurnUseCase(repository, catalog_repository)

    # First message: set need
    request1 = ChatRequest(
        session_id="test_session_3",
        message="Auto familiar",
        channel="api",
    )
    await use_case.execute(request1)

    # Second message: set budget
    request2 = ChatRequest(
        session_id="test_session_3",
        message="Mi presupuesto es $200,000",
        channel="api",
    )
    response = await use_case.execute(request2)

    # When budget is set, step becomes "options" and cars are searched
    # If cars are found, next_action is "ask_financing", otherwise "ask_preferences"
    assert response.next_action in ["ask_preferences", "ask_financing"]
    assert response.debug.get("budget") is not None


@pytest.mark.asyncio
async def test_handle_chat_turn_state_persistence():
    """Test that state persists across multiple messages."""
    repository = MockConversationStateRepository()
    catalog_repository = MockCarCatalogRepository()
    use_case = HandleChatTurnUseCase(repository, catalog_repository)

    session_id = "test_session_4"

    # First message
    request1 = ChatRequest(
        session_id=session_id,
        message="Auto familiar",
        channel="api",
    )
    response1 = await use_case.execute(request1)
    assert response1.debug.get("need") == "family"

    # Second message - should remember need
    request2 = ChatRequest(
        session_id=session_id,
        message="Mi presupuesto es $150,000",
        channel="api",
    )
    response2 = await use_case.execute(request2)
    assert response2.debug.get("need") == "family"
    assert response2.debug.get("budget") is not None


@pytest.mark.asyncio
async def test_handle_chat_turn_all_steps():
    """Test complete flow through all steps."""
    repository = MockConversationStateRepository()
    catalog_repository = MockCarCatalogRepository()
    use_case = HandleChatTurnUseCase(repository, catalog_repository)

    session_id = "test_session_5"

    # Step 1: Need
    response1 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Auto familiar", channel="api")
    )
    assert response1.next_action == "ask_budget"

    # Step 2: Budget - when set, cars are searched and shown
    response2 = await use_case.execute(
        ChatRequest(session_id=session_id, message="$200,000", channel="api")
    )
    # Cars are found, so it goes directly to financing
    assert response2.next_action == "ask_financing"

    # Step 3: Set preferences first (since it's still missing)
    response3 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Automática", channel="api")
    )
    assert response3.next_action == "ask_financing"

    # Step 4: Financing interest
    response4 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Sí, me interesa financiamiento", channel="api")
    )
    # After showing financing interest, it should ask for down payment
    assert response4.next_action == "ask_down_payment"

    # Step 5: Down payment
    response5 = await use_case.execute(
        ChatRequest(session_id=session_id, message="10% de enganche", channel="api")
    )
    assert response5.next_action == "ask_loan_term"

    # Step 6: Loan term
    response6 = await use_case.execute(
        ChatRequest(session_id=session_id, message="48 meses", channel="api")
    )
    # After providing term, should show financing plans and complete
    assert response6.next_action == "complete"


@pytest.mark.asyncio
async def test_handle_chat_turn_spanish_keywords():
    """Test that Spanish keywords are recognized."""
    repository = MockConversationStateRepository()
    catalog_repository = MockCarCatalogRepository()
    use_case = HandleChatTurnUseCase(repository, catalog_repository)

    session_id = "test_session_6"

    # Test Spanish need keywords
    response = await use_case.execute(
        ChatRequest(session_id=session_id, message="Necesito un SUV", channel="api")
    )
    assert response.debug.get("need") == "suv"

    # Test Spanish financing keywords
    response2 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Sí, quiero crédito", channel="api")
    )
    assert response2.debug.get("financing_interest") is True


@pytest.mark.asyncio
async def test_handle_chat_turn_car_search_on_options_step():
    """Test that cars are searched when step is 'options'."""
    repository = MockConversationStateRepository()
    catalog_repository = MockCarCatalogRepository()
    use_case = HandleChatTurnUseCase(repository, catalog_repository)

    session_id = "test_session_7"

    # Set need and budget to reach options step
    await use_case.execute(
        ChatRequest(session_id=session_id, message="Auto familiar", channel="api")
    )
    response = await use_case.execute(
        ChatRequest(session_id=session_id, message="$200,000", channel="api")
    )

    # Step should be "options" and we should get car recommendations
    assert response.debug.get("step") == "options"
    # The response should either show cars or ask for preferences
    assert "opciones" in response.reply.lower() or "preferencias" in response.reply.lower()
