"""HTTP routes."""

from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Request, Response, status

from app.adapters.inbound.http.twilio_utils import (
    generate_twiml_response,
    validate_twilio_signature,
)
from app.application.dtos.chat import ChatRequest, ChatResponse
from app.infrastructure.config.settings import settings
from app.infrastructure.logging.logger import log_turn, logger
from app.infrastructure.wiring.dependencies import (
    create_conversation_state_repository,
    create_handle_chat_turn_use_case,
    create_idempotency_store,
    create_lead_repository,
)

router = APIRouter()

# Create use case instance (wired with dependencies)
_handle_chat_turn_use_case = create_handle_chat_turn_use_case()
_state_repository = create_conversation_state_repository()
_lead_repository = create_lead_repository()
_idempotency_store = create_idempotency_store()


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


@router.post("/channels/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form(None),
    MessageSid: str = Form(None),
) -> Response:
    """
    Handle WhatsApp webhook requests from Twilio.

    Accepts form-encoded data from Twilio and returns TwiML XML response.
    Maps Twilio webhook payload to internal chat flow.

    Args:
        request: FastAPI request object (for signature validation)
        From: Phone number (used as session_id)
        Body: Message text
        ProfileName: Optional WhatsApp profile name
        MessageSid: Optional Twilio message SID

    Returns:
        TwiML XML response with Spanish reply
    """
    # Validate Twilio signature if enabled
    # Build full URL for signature validation
    url = str(request.url)
    form_data = {
        "From": From,
        "Body": Body,
    }
    if ProfileName:
        form_data["ProfileName"] = ProfileName
    if MessageSid:
        form_data["MessageSid"] = MessageSid

    try:
        if not validate_twilio_signature(request, url, form_data):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature",
            )
    except HTTPException:
        raise
    except Exception as err:
        # If signature validation fails for other reasons and it's enabled, fail
        if settings.twilio_validate_signature:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Twilio signature validation failed",
            ) from err

    # Idempotency check: if MessageSid exists and idempotency is enabled
    if MessageSid and settings.twilio_idempotency_enabled:
        if await _idempotency_store.is_processed(MessageSid):
            # Get stored response if available
            stored_response = await _idempotency_store.get_response(MessageSid)
            if stored_response:
                # Return stored TwiML response
                return Response(
                    content=stored_response,
                    media_type="application/xml",
                    status_code=status.HTTP_200_OK,
                )
            else:
                # Return safe no-op TwiML message in Spanish
                safe_message = (
                    "Mensaje recibido. Si necesitas ayuda adicional, dime en qué puedo apoyarte."
                )
                twiml = generate_twiml_response(safe_message)
                return Response(
                    content=twiml,
                    media_type="application/xml",
                    status_code=status.HTTP_200_OK,
                )
    elif MessageSid is None and settings.twilio_idempotency_enabled:
        # Log warning if MessageSid is missing but idempotency is enabled
        logger.warning("MessageSid missing in Twilio webhook request but idempotency is enabled")

    # Generate turn_id for request correlation
    turn_id = str(uuid4())

    # Map Twilio payload to ChatRequest
    metadata = {}
    if ProfileName:
        metadata["profile_name"] = ProfileName
    if MessageSid:
        metadata["message_sid"] = MessageSid

    chat_request = ChatRequest(
        session_id=From,
        message=Body,
        channel="whatsapp",
        metadata=metadata if metadata else None,
    )

    # Log incoming request
    log_turn(
        session_id=chat_request.session_id,
        turn_id=turn_id,
        component="whatsapp_webhook",
        message_length=len(chat_request.message),
        channel=chat_request.channel,
    )

    # Execute use case (same as /chat endpoint)
    chat_response = await _handle_chat_turn_use_case.execute(chat_request, turn_id=turn_id)

    # Log response
    log_turn(
        session_id=chat_request.session_id,
        turn_id=turn_id,
        component="whatsapp_webhook",
        next_action=chat_response.next_action,
        reply_length=len(chat_response.reply),
    )

    # Generate TwiML response
    twiml = generate_twiml_response(chat_response.reply)

    # Store idempotency marker and response if MessageSid exists and idempotency is enabled
    if MessageSid and settings.twilio_idempotency_enabled:
        await _idempotency_store.mark_processed(
            MessageSid,
            settings.twilio_idempotency_ttl_seconds,
        )
        await _idempotency_store.store_response(
            MessageSid,
            twiml,
            settings.twilio_idempotency_ttl_seconds,
        )

    # Return TwiML XML response
    return Response(
        content=twiml,
        media_type="application/xml",
        status_code=status.HTTP_200_OK,
    )


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
