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
                "message": "I'm looking for a family car",
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
                "reply": "Great! I'd be happy to help you find the perfect family car. What's your budget range?",
                "next_action": "ask_budget",
                "suggested_questions": [
                    "What's your budget?",
                    "Do you prefer SUVs or sedans?",
                    "How many seats do you need?",
                ],
                "debug": {"step": "need", "confidence": 0.95},
            }
        }

