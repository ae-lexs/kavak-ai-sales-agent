"""Postgres-backed lead repository adapter."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.dtos.lead import Lead
from app.application.ports.lead_repository import LeadRepository
from app.infrastructure.db import get_db_session
from app.infrastructure.logging.logger import logger

from .models import LeadModel


class PostgresLeadRepository(LeadRepository):
    """Postgres implementation of lead repository."""

    def __init__(self) -> None:
        """Initialize Postgres repository."""
        pass

    def _model_to_dto(self, model: LeadModel) -> Lead:
        """
        Convert LeadModel to Lead DTO.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Lead DTO
        """
        # Ensure created_at is timezone-aware (SQLite returns naive datetimes)
        created_at = model.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        return Lead(
            session_id=model.session_id,
            name=model.name,
            phone=model.phone,
            preferred_contact_time=model.preferred_contact_time,
            created_at=created_at,
        )

    def _dto_to_model(self, lead: Lead, model: Optional[LeadModel] = None) -> LeadModel:
        """
        Convert Lead DTO to LeadModel (for upsert).

        Args:
            lead: Lead DTO
            model: Existing model instance (for update) or None (for insert)

        Returns:
            LeadModel instance
        """
        now = datetime.now(timezone.utc)

        # Determine status based on completeness
        status = None
        if lead.name and lead.phone and lead.preferred_contact_time:
            status = "complete"
        elif lead.name or lead.phone or lead.preferred_contact_time:
            status = "partial"

        if model:
            # Update existing model
            model.name = lead.name
            model.phone = lead.phone
            model.preferred_contact_time = lead.preferred_contact_time
            model.status = status
            model.updated_at = now
            return model
        else:
            # Create new model
            return LeadModel(
                session_id=lead.session_id,
                name=lead.name,
                phone=lead.phone,
                preferred_contact_time=lead.preferred_contact_time,
                status=status,
                created_at=lead.created_at if lead.created_at else now,
                updated_at=now,
            )

    async def save(self, lead: Lead) -> None:
        """
        Save a lead (upsert by session_id).

        Args:
            lead: Lead DTO to save
        """
        db: Session = get_db_session()
        try:
            # Check if record exists
            model = db.query(LeadModel).filter(LeadModel.session_id == lead.session_id).first()

            if model:
                # Update existing record
                self._dto_to_model(lead, model)
            else:
                # Insert new record
                model = self._dto_to_model(lead)
                db.add(model)

            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                f"Database error while saving lead for session {lead.session_id}: {str(e)}"
            )
            raise
        finally:
            db.close()

    async def get(self, session_id: str) -> Optional[Lead]:
        """
        Get a lead by session_id.

        Args:
            session_id: Session identifier

        Returns:
            Lead DTO, or None if not found
        """
        db: Session = get_db_session()
        try:
            model = db.query(LeadModel).filter(LeadModel.session_id == session_id).first()
            if model is None:
                return None
            return self._model_to_dto(model)
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting lead for session {session_id}: {str(e)}")
            return None
        finally:
            db.close()

    async def list(self) -> list[Lead]:
        """
        List all leads.

        Returns:
            List of all leads
        """
        db: Session = get_db_session()
        try:
            models = db.query(LeadModel).all()
            return [self._model_to_dto(model) for model in models]
        except SQLAlchemyError as e:
            logger.error(f"Database error while listing leads: {str(e)}")
            return []
        finally:
            db.close()
