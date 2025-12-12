"""Conversation state entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ConversationState:
    """Conversation state entity."""

    session_id: str
    need: Optional[str] = None
    budget: Optional[str] = None
    preferences: Optional[str] = None  # make/model
    financing_interest: Optional[bool] = None
    down_payment: Optional[str] = None  # Can be amount or percentage
    loan_term: Optional[int] = None  # Term in months (36, 48, 60, 72)
    selected_car_price: Optional[float] = None  # Price of selected car for financing
    last_question: Optional[str] = None
    step: str = "need"  # need -> budget -> options -> financing -> next_action
    # Lead capture fields
    lead_name: Optional[str] = None
    lead_phone: Optional[str] = None
    lead_preferred_contact_time: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def is_complete(self) -> bool:
        """
        Check if all required fields are collected.

        Returns:
            True if all required fields are present
        """
        return all(
            [
                self.need is not None,
                self.budget is not None,
                self.preferences is not None,
                self.financing_interest is not None,
            ]
        )

    def get_next_missing_field(self) -> Optional[str]:
        """
        Get the next missing field to collect.

        Returns:
            Name of the next missing field, or None if all are collected
        """
        if self.need is None:
            return "need"
        if self.budget is None:
            return "budget"
        if self.preferences is None:
            return "preferences"
        if self.financing_interest is None:
            return "financing_interest"
        return None

    def is_lead_complete(self) -> bool:
        """
        Check if all lead information is collected.

        Returns:
            True if name, phone, and preferred_contact_time are all present
        """
        return all(
            [
                self.lead_name is not None,
                self.lead_phone is not None,
                self.lead_preferred_contact_time is not None,
            ]
        )

    def get_next_missing_lead_field(self) -> Optional[str]:
        """
        Get the next missing lead field to collect.

        Returns:
            Name of the next missing lead field, or None if all are collected
        """
        if self.lead_name is None:
            return "lead_name"
        if self.lead_phone is None:
            return "lead_phone"
        if self.lead_preferred_contact_time is None:
            return "lead_preferred_contact_time"
        return None
