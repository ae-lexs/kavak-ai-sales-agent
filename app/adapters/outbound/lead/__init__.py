"""Lead repository adapters."""

from app.adapters.outbound.lead.lead_repository import InMemoryLeadRepository
from app.adapters.outbound.lead.postgres_lead_repository import PostgresLeadRepository

__all__ = [
    "InMemoryLeadRepository",
    "PostgresLeadRepository",
]
