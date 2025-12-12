"""Unit tests for HandleChatTurnUseCase."""

import pytest

from app.application.dtos.chat import ChatRequest
from app.application.use_cases.handle_chat_turn_use_case import HandleChatTurnUseCase
from app.domain.entities.conversation_state import ConversationState


class MockConversationStateRepository:
    """Mock repository for testing."""

    def __init__(self) -> None:
        """Initialize mock repository."""
        self._storage: dict[str, ConversationState] = {}

    async def get(self, session_id: str) -> ConversationState:
        """Get or create conversation state."""
        if session_id not in self._storage:
            self._storage[session_id] = ConversationState(session_id=session_id)
        return self._storage[session_id]

    async def save(self, state: ConversationState) -> None:
        """Save conversation state."""
        self._storage[state.session_id] = state


@pytest.mark.asyncio
async def test_handle_chat_turn_initial_greeting():
    """Test initial greeting when no state exists."""
    repository = MockConversationStateRepository()
    use_case = HandleChatTurnUseCase(repository)

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
    use_case = HandleChatTurnUseCase(repository)

    request = ChatRequest(
        session_id="test_session_2",
        message="Necesito un auto familiar",
        channel="api",
    )

    response = await use_case.execute(request)

    assert response.session_id == "test_session_2"
    assert response.next_action == "ask_budget"
    assert response.debug["need"] == "family"


@pytest.mark.asyncio
async def test_handle_chat_turn_extract_budget():
    """Test extracting budget from message."""
    repository = MockConversationStateRepository()
    use_case = HandleChatTurnUseCase(repository)

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

    assert response.next_action == "ask_preferences"
    assert response.debug["budget"] is not None


@pytest.mark.asyncio
async def test_handle_chat_turn_state_persistence():
    """Test that state persists across multiple messages."""
    repository = MockConversationStateRepository()
    use_case = HandleChatTurnUseCase(repository)

    session_id = "test_session_4"

    # First message
    request1 = ChatRequest(
        session_id=session_id,
        message="Auto familiar",
        channel="api",
    )
    response1 = await use_case.execute(request1)
    assert response1.debug["need"] == "family"

    # Second message - should remember need
    request2 = ChatRequest(
        session_id=session_id,
        message="Mi presupuesto es $150,000",
        channel="api",
    )
    response2 = await use_case.execute(request2)
    assert response2.debug["need"] == "family"
    assert response2.debug["budget"] is not None


@pytest.mark.asyncio
async def test_handle_chat_turn_all_steps():
    """Test complete flow through all steps."""
    repository = MockConversationStateRepository()
    use_case = HandleChatTurnUseCase(repository)

    session_id = "test_session_5"

    # Step 1: Need
    response1 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Auto familiar", channel="api")
    )
    assert response1.next_action == "ask_budget"

    # Step 2: Budget
    response2 = await use_case.execute(
        ChatRequest(session_id=session_id, message="$200,000", channel="api")
    )
    assert response2.next_action == "ask_preferences"

    # Step 3: Preferences
    response3 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Automática", channel="api")
    )
    assert response3.next_action == "ask_financing"

    # Step 4: Financing
    response4 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Sí, me interesa financiamiento", channel="api")
    )
    assert response4.next_action == "ask_contact"

    # Step 5: Contact intent
    response5 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Sí, agendar cita", channel="api")
    )
    assert response5.next_action == "complete" or response5.next_action == "ask_contact"


@pytest.mark.asyncio
async def test_handle_chat_turn_spanish_keywords():
    """Test that Spanish keywords are recognized."""
    repository = MockConversationStateRepository()
    use_case = HandleChatTurnUseCase(repository)

    session_id = "test_session_6"

    # Test Spanish need keywords
    response = await use_case.execute(
        ChatRequest(session_id=session_id, message="Necesito un SUV", channel="api")
    )
    assert response.debug["need"] == "suv"

    # Test Spanish financing keywords
    response2 = await use_case.execute(
        ChatRequest(session_id=session_id, message="Sí, quiero crédito", channel="api")
    )
    assert response2.debug["financing_interest"] is True

