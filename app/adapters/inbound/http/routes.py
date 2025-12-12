"""HTTP routes."""

from fastapi import APIRouter, status

from app.application.dtos.chat import ChatRequest, ChatResponse
from app.application.use_cases.chat_use_case import ChatUseCase
from app.adapters.outbound.llm_rag.chat_adapter import LLMRAGChatAdapter

router = APIRouter()

# Initialize dependencies (TODO: Replace with proper DI container)
_chat_adapter = LLMRAGChatAdapter()
_chat_use_case = ChatUseCase(_chat_adapter)


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
    return await _chat_use_case.execute(request)

