"""Lead DTOs."""

from datetime import datetime
from typing import Optional

from app.application.dtos.base import DTO


class Lead(DTO):
    """Lead DTO for capturing customer contact information."""

    session_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    preferred_contact_time: Optional[str] = None
    created_at: datetime
