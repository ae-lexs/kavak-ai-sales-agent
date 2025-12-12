"""Lead repository port."""

from abc import ABC, abstractmethod

from app.application.dtos.lead import Lead


class LeadRepository(ABC):
    """Port interface for lead repository."""

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
