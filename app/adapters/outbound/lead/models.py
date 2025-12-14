"""SQLAlchemy ORM models for leads."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

# Import Base from conversation_state_repository models to reuse the same declarative base
from app.adapters.outbound.conversation_state_repository.models import Base


class LeadModel(Base):
    """SQLAlchemy model for leads table."""

    __tablename__ = "leads"

    session_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    preferred_contact_time = Column(String, nullable=True)
    status = Column(String, nullable=True)  # e.g., "partial", "complete"
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
