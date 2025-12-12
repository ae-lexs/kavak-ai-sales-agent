"""Chat DTOs."""

from typing import Any, Optional

from app.application.dtos.base import DTO


class ChatRequest(DTO):
    """Chat request DTO."""

    session_id: str
    message: str
    channel: str = "api"
    metadata: Optional[dict[str, Any]] = None

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "session_id": "session_123",
                "message": "Estoy buscando un auto familiar",
                "channel": "api",
                "metadata": {"user_id": "user_456", "timestamp": "2024-01-15T10:30:00Z"},
            }
        }


class ChatResponse(DTO):
    """Chat response DTO."""

    session_id: str
    reply: str
    next_action: str
    suggested_questions: list[str]
    debug: Optional[dict[str, Any]] = None

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "session_id": "session_123",
                "reply": "¡Excelente! Entiendo que buscas un auto family. ¿Cuál es tu rango de presupuesto? Puedes decirme un monto específico o un rango.",
                "next_action": "ask_budget",
                "suggested_questions": [
                    "Mi presupuesto es alrededor de $200,000",
                    "Estoy buscando algo menor a $150,000",
                    "Puedo gastar hasta $300,000",
                ],
                "debug": {"current_step": "budget", "need": "family", "budget": None},
            }
        }

