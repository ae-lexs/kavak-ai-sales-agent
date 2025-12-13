"""Postgres-backed conversation state repository adapter."""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.domain.entities.conversation_state import ConversationState
from app.infrastructure.db import get_db_session
from app.infrastructure.logging.logger import logger

from .models import ConversationStateModel


class PostgresConversationStateRepository(ConversationStateRepository):
    """Postgres implementation of conversation state repository."""

    def __init__(self) -> None:
        """Initialize Postgres repository."""
        pass

    def _serialize_state(self, state: ConversationState) -> dict:
        """
        Serialize ConversationState to dictionary.

        Args:
            state: Conversation state entity

        Returns:
            Dictionary representation of the state
        """
        return {
            "session_id": state.session_id,
            "need": state.need,
            "budget": state.budget,
            "preferences": state.preferences,
            "financing_interest": state.financing_interest,
            "down_payment": state.down_payment,
            "loan_term": state.loan_term,
            "selected_car_price": state.selected_car_price,
            "last_question": state.last_question,
            "step": state.step,
            "lead_name": state.lead_name,
            "lead_phone": state.lead_phone,
            "lead_preferred_contact_time": state.lead_preferred_contact_time,
            "created_at": state.created_at.isoformat() if state.created_at else None,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }

    def _deserialize_state(self, data: dict) -> ConversationState:
        """
        Deserialize dictionary to ConversationState.

        Args:
            data: Dictionary representation of the state

        Returns:
            ConversationState entity
        """
        # Parse datetime strings back to datetime objects
        created_at = None
        updated_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

        return ConversationState(
            session_id=data["session_id"],
            need=data.get("need"),
            budget=data.get("budget"),
            preferences=data.get("preferences"),
            financing_interest=data.get("financing_interest"),
            down_payment=data.get("down_payment"),
            loan_term=data.get("loan_term"),
            selected_car_price=data.get("selected_car_price"),
            last_question=data.get("last_question"),
            step=data.get("step", "need"),
            lead_name=data.get("lead_name"),
            lead_phone=data.get("lead_phone"),
            lead_preferred_contact_time=data.get("lead_preferred_contact_time"),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
        )

    async def get(self, session_id: str) -> Optional[ConversationState]:
        """
        Get conversation state for a session.

        Args:
            session_id: Session identifier

        Returns:
            Conversation state entity, or None if not found
        """
        db: Session = get_db_session()
        try:
            model = (
                db.query(ConversationStateModel)
                .filter(ConversationStateModel.session_id == session_id)
                .first()
            )
            if model is None:
                return None

            # Deserialize JSON to ConversationState
            state_data = model.state_json
            if isinstance(state_data, str):
                state_data = json.loads(state_data)

            return self._deserialize_state(state_data)
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting state for session {session_id}: {str(e)}")
            return None
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error deserializing state for session {session_id}: {str(e)}")
            return None
        finally:
            db.close()

    async def save(self, session_id: str, state: ConversationState) -> None:
        """
        Save conversation state.

        Args:
            session_id: Session identifier
            state: Conversation state entity to save
        """
        db: Session = get_db_session()
        try:
            # Serialize state to JSON
            state_dict = self._serialize_state(state)
            state_json = json.dumps(state_dict, sort_keys=True)  # Deterministic serialization

            # Check if record exists
            model = (
                db.query(ConversationStateModel)
                .filter(ConversationStateModel.session_id == session_id)
                .first()
            )

            now = datetime.now(timezone.utc)

            if model:
                # Update existing record
                model.state_json = json.loads(state_json)  # Store as JSON object, not string
                model.updated_at = now
            else:
                # Insert new record
                model = ConversationStateModel(
                    session_id=session_id,
                    state_json=json.loads(state_json),
                    created_at=state.created_at if state.created_at else now,
                    updated_at=now,
                )
                db.add(model)

            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error while saving state for session {session_id}: {str(e)}")
            raise
        except (json.JSONEncodeError, ValueError) as e:
            db.rollback()
            logger.error(f"Error serializing state for session {session_id}: {str(e)}")
            raise
        finally:
            db.close()

    async def delete(self, session_id: str) -> None:
        """
        Delete conversation state for a session.

        Args:
            session_id: Session identifier
        """
        db: Session = get_db_session()
        try:
            db.query(ConversationStateModel).filter(
                ConversationStateModel.session_id == session_id
            ).delete()
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error while deleting state for session {session_id}: {str(e)}")
            raise
        finally:
            db.close()
