"""Conversation state entity."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConversationState:
    """Conversation state entity."""

    session_id: str
    need: Optional[str] = None
    budget: Optional[str] = None
    preferences: Optional[str] = None
    financing_interest: Optional[bool] = None
    contact_intent: Optional[bool] = None
    current_step: str = "need"  # need -> budget -> options -> financing -> next_action

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
                self.contact_intent is not None,
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
        if self.contact_intent is None:
            return "contact_intent"
        return None

