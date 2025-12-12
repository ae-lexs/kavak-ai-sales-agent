"""HTTP routes."""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.application.dtos.chat import ChatRequest, ChatResponse
from app.infrastructure.config.settings import settings
from app.infrastructure.logging.logger import log_turn
from app.infrastructure.wiring.dependencies import (
    create_conversation_state_repository,
    create_handle_chat_turn_use_case,
    create_lead_repository,
)

router = APIRouter()

# Create use case instance (wired with dependencies)
_handle_chat_turn_use_case = create_handle_chat_turn_use_case()
_state_repository = create_conversation_state_repository()
_lead_repository = create_lead_repository()


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
    # Generate turn_id for request correlation
    turn_id = str(uuid4())

    # Log incoming request
    log_turn(
        session_id=request.session_id,
        turn_id=turn_id,
        component="http",
        message_length=len(request.message),
        channel=request.channel,
    )

    # Execute use case
    response = await _handle_chat_turn_use_case.execute(request, turn_id=turn_id)

    # Add turn_id to debug if DEBUG_MODE is enabled
    if settings.debug_mode and response.debug is not None:
        response.debug["turn_id"] = turn_id

    # Log response
    log_turn(
        session_id=request.session_id,
        turn_id=turn_id,
        component="http",
        next_action=response.next_action,
        reply_length=len(response.reply),
    )

    return response


@router.get("/debug/session/{session_id}", status_code=status.HTTP_200_OK)
async def get_session_debug(session_id: str) -> dict:
    """
    Get debug information for a session (only enabled if DEBUG_MODE=true).

    Args:
        session_id: Session identifier

    Returns:
        Conversation state debug information

    Raises:
        HTTPException: 404 if DEBUG_MODE is disabled
    """
    if not settings.debug_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug endpoint is disabled",
        )

    # Fetch state from repository
    state = await _state_repository.get(session_id)

    if state is None:
        return {"session_id": session_id, "state": None}

    # Return state as dictionary with English keys
    return {
        "session_id": session_id,
        "state": {
            "step": state.step,
            "need": state.need,
            "budget": state.budget,
            "preferences": state.preferences,
            "financing_interest": state.financing_interest,
            "down_payment": state.down_payment,
            "loan_term": state.loan_term,
            "selected_car_price": state.selected_car_price,
            "last_question": state.last_question,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        },
    }


@router.post("/debug/session/{session_id}/reset", status_code=status.HTTP_200_OK)
async def reset_session(session_id: str) -> dict:
    """
    Reset conversation state for a session (only enabled if DEBUG_MODE=true).

    Args:
        session_id: Session identifier

    Returns:
        Confirmation message

    Raises:
        HTTPException: 404 if DEBUG_MODE is disabled
    """
    if not settings.debug_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug endpoint is disabled",
        )

    # Delete state from repository
    await _state_repository.delete(session_id)

    return {
        "session_id": session_id,
        "message": "Session reset successfully",
        "status": "reset",
    }


@router.get("/debug/leads", status_code=status.HTTP_200_OK)
async def get_leads_debug() -> dict:
    """
    Get all captured leads (only enabled if DEBUG_MODE=true).

    Returns:
        List of captured leads with English keys

    Raises:
        HTTPException: 404 if DEBUG_MODE is disabled
    """
    if not settings.debug_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug endpoint is disabled",
        )

    leads = await _lead_repository.list()

    return {
        "leads": [
            {
                "session_id": lead.session_id,
                "name": lead.name,
                "phone": lead.phone,
                "preferred_contact_time": lead.preferred_contact_time,
                "created_at": lead.created_at.isoformat(),
            }
            for lead in leads
        ],
        "count": len(leads),
    }
