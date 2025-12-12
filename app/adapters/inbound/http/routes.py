"""HTTP routes."""

from fastapi import APIRouter, status

from app.application.dtos.chat import ChatRequest, ChatResponse
from app.infrastructure.wiring.dependencies import create_handle_chat_turn_use_case

router = APIRouter()

# Create use case instance (wired with dependencies)
_handle_chat_turn_use_case = create_handle_chat_turn_use_case()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """
    Health check endpoint for liveness/readiness.

    Returns:
        Health status
    """
    return {"status": "ok"}


@router.post("/chat", status_code=status.HTTP_200_OK, response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Handle a conversation turn with the AI Commercial Agent.

    Args:
        request: Chat request containing session_id, message, channel, and optional metadata

    Returns:
        Chat response with reply, next_action, suggested_questions, and optional debug info
    """
    return await _handle_chat_turn_use_case.execute(request)

