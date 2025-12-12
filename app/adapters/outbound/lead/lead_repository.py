"""In-memory lead repository adapter."""

from app.application.dtos.lead import Lead
from app.application.ports.lead_repository import LeadRepository


class InMemoryLeadRepository(LeadRepository):
    """In-memory implementation of lead repository."""

    def __init__(self) -> None:
        """Initialize in-memory repository."""
        self._storage: list[Lead] = []

    async def save(self, lead: Lead) -> None:
        """
        Save a lead.

        Args:
            lead: Lead DTO to save
        """
        # Remove existing lead for same session_id if present
        self._storage = [
            existing_lead
            for existing_lead in self._storage
            if existing_lead.session_id != lead.session_id
        ]
        self._storage.append(lead)

    async def list(self) -> list[Lead]:
        """
        List all leads.

        Returns:
            List of all leads
        """
        return self._storage.copy()
