"""HTTP adapter schemas for external integrations."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class TwilioWebhookRequest(BaseModel):
    """Twilio webhook payload schema."""

    From: str  # Phone number (used as session_id)
    Body: str  # Message text
    ProfileName: Optional[str] = None  # Optional WhatsApp profile name

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "From": "+521234567890",
                "Body": "Estoy buscando un auto familiar",
                "ProfileName": "Juan Pérez",
            }
        }
    )


class WhatsAppWebhookResponse(BaseModel):
    """Simplified WhatsApp webhook response."""

    session_id: str
    reply: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "+521234567890",
                "reply": "¡Hola! ¿En qué puedo ayudarte hoy?",
            }
        }
    )
