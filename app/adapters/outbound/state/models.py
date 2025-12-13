"""SQLAlchemy ORM models for conversation state."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ConversationStateModel(Base):
    """SQLAlchemy model for conversation_states table."""

    __tablename__ = "conversation_states"

    session_id = Column(String, primary_key=True, index=True)
    state_json = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
