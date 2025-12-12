"""Unit tests for ChatUseCase."""

import pytest

from app.application.dtos.chat import ChatRequest, ChatResponse
from app.application.ports.chat_port import ChatPort
from app.application.use_cases.chat_use_case import ChatUseCase


class MockChatPort(ChatPort):
    """Mock chat port for testing."""

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """Mock chat handling."""
        return ChatResponse(
            session_id=request.session_id,
            reply="Mock response",
            next_action="mock_action",
            suggested_questions=["Question 1", "Question 2"],
        )


@pytest.mark.asyncio
async def test_chat_use_case_execute():
    """Test ChatUseCase execute method."""
    mock_port = MockChatPort()
    use_case = ChatUseCase(mock_port)

    request = ChatRequest(
        session_id="test_session",
        message="Test message",
        channel="api",
    )

    response = await use_case.execute(request)

    assert response.session_id == "test_session"
    assert response.reply == "Mock response"
    assert response.next_action == "mock_action"
    assert len(response.suggested_questions) == 2

