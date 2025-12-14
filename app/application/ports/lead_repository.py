"""Lead repository port."""

from abc import ABC, abstractmethod
from typing import Optional

from app.application.dtos.lead import Lead


class LeadRepository(ABC):
    """Port interface for lead repository."""

    @abstractmethod
    async def get(self, session_id: str) -> Optional[Lead]:
        """
        Get a lead by session_id.

        Args:
            session_id: Session identifier

        Returns:
            Lead DTO, or None if not found
        """
        pass

    @abstractmethod
    async def save(self, lead: Lead) -> None:
        """
        Save a lead.

        Args:
            lead: Lead DTO to save
        """
        pass

    @abstractmethod
    async def list(self) -> list[Lead]:
        """
        List all leads.

        Returns:
            List of all leads (used for debug/demo purposes)
        """
        pass
