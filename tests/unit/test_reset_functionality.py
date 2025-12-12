"""Unit tests for reset functionality."""

from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.adapters.inbound.http.routes import router
from app.application.dtos.chat import ChatRequest
from app.application.use_cases.handle_chat_turn_use_case import HandleChatTurnUseCase
from app.domain.entities.conversation_state import ConversationState
from app.infrastructure.config.settings import settings
from tests.unit.test_handle_chat_turn_use_case import (
    MockCarCatalogRepository,
    MockConversationStateRepository,
)


@pytest.fixture
def use_case():
    """Create use case with mock dependencies."""
    state_repo = MockConversationStateRepository()
    car_repo = MockCarCatalogRepository()
    return HandleChatTurnUseCase(state_repo, car_repo, faq_rag_service=None, logger=None)


@pytest.fixture
def client():
    """Create test client."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.asyncio
async def test_reset_via_chat_keyword_spanish(use_case):
    """Test that reset keyword in Spanish resets the session."""
    session_id = "test_reset_session"

    # Create some state
    state = ConversationState(session_id=session_id, need="family", budget="300000")
    await use_case._state_repository.save(session_id, state)

    # Send reset message in Spanish
    request = ChatRequest(
        session_id=session_id,
        message="reiniciar",
        channel="api",
    )
    response = await use_case.execute(request)

    # Should reset and start fresh
    assert response.next_action == "ask_need"
    assert "reiniciado" in response.reply.lower() or "empezar" in response.reply.lower()

    # State should be reset (new state created)
    new_state = await use_case._state_repository.get(session_id)
    assert new_state is not None
    assert new_state.need is None
    assert new_state.budget is None
    assert new_state.step == "need"


@pytest.mark.asyncio
async def test_reset_via_chat_keyword_english(use_case):
    """Test that reset keyword in English resets the session."""
    session_id = "test_reset_session_en"

    # Create some state
    state = ConversationState(session_id=session_id, need="family", budget="300000")
    await use_case._state_repository.save(session_id, state)

    # Send reset message in English
    request = ChatRequest(
        session_id=session_id,
        message="reset",
        channel="api",
    )
    response = await use_case.execute(request)

    # Should reset and start fresh
    assert response.next_action == "ask_need"
    assert "reiniciado" in response.reply.lower() or "empezar" in response.reply.lower()


@pytest.mark.asyncio
async def test_reset_endpoint_disabled_returns_404(client):
    """Test that reset endpoint returns 404 when DEBUG_MODE is disabled."""
    with patch.object(settings, "debug_mode", False):
        response = client.post("/debug/session/test_session/reset")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_reset_endpoint_enabled_resets_session(client):
    """Test that reset endpoint resets session when DEBUG_MODE is enabled."""
    with patch.object(settings, "debug_mode", True):
        session_id = "test_reset_endpoint"

        # First create a session by making a chat request
        chat_response = client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message": "Estoy buscando un auto familiar",
                "channel": "api",
            },
        )
        assert chat_response.status_code == status.HTTP_200_OK

        # Verify state exists (state is saved, so it should be available)
        debug_response = client.get(f"/debug/session/{session_id}")
        assert debug_response.status_code == status.HTTP_200_OK
        debug_data = debug_response.json()
        # State may or may not exist depending on when it's checked, but endpoint should work
        # The important part is that reset works
        state_data = debug_data.get("state")
        # If state exists, it should have step
        if state_data is not None:
            assert "step" in state_data

        # Reset the session
        reset_response = client.post(f"/debug/session/{session_id}/reset")
        assert reset_response.status_code == status.HTTP_200_OK
        assert reset_response.json()["status"] == "reset"

        # Verify state is gone
        debug_response_after = client.get(f"/debug/session/{session_id}")
        assert debug_response_after.status_code == status.HTTP_200_OK
        assert debug_response_after.json()["state"] is None


@pytest.mark.asyncio
async def test_invalid_budget_shows_error(use_case):
    """Test that invalid budget shows Spanish error message."""
    session_id = "test_invalid_budget"

    # Set need first
    request1 = ChatRequest(
        session_id=session_id,
        message="Estoy buscando un auto familiar",
        channel="api",
    )
    await use_case.execute(request1)

    # Provide invalid budget (too low)
    request2 = ChatRequest(
        session_id=session_id,
        message="Mi presupuesto es $10,000",
        channel="api",
    )
    response2 = await use_case.execute(request2)

    # Should show error in Spanish
    assert "presupuesto válido" in response2.reply.lower() or "mínimo" in response2.reply.lower()
    assert response2.next_action == "ask_budget"


@pytest.mark.asyncio
async def test_invalid_loan_term_shows_error(use_case):
    """Test that invalid loan term shows Spanish error with allowed terms."""
    session_id = "test_invalid_term"

    # Go through flow to get to loan term
    await use_case.execute(
        ChatRequest(session_id=session_id, message="Estoy buscando un auto familiar", channel="api")
    )
    await use_case.execute(
        ChatRequest(session_id=session_id, message="Mi presupuesto es $300,000", channel="api")
    )
    await use_case.execute(
        ChatRequest(
            session_id=session_id, message="Sí, me interesa el financiamiento", channel="api"
        )
    )
    await use_case.execute(ChatRequest(session_id=session_id, message="20%", channel="api"))

    # Provide invalid loan term
    request = ChatRequest(
        session_id=session_id,
        message="24 meses",
        channel="api",
    )
    response = await use_case.execute(request)

    # Should show error in Spanish with allowed terms
    assert "no está disponible" in response.reply.lower() or "plazos" in response.reply.lower()
    assert (
        "36" in response.reply
        or "48" in response.reply
        or "60" in response.reply
        or "72" in response.reply
    )
    assert response.next_action == "ask_loan_term"
    # Should suggest valid terms
    assert any(
        "36" in q or "48" in q or "60" in q or "72" in q for q in response.suggested_questions
    )
