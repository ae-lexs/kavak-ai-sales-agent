"""Knowledge base DTOs."""

from app.application.dtos.base import DTO


class KnowledgeChunk(DTO):
    """Knowledge chunk DTO."""

    id: str
    text: str
    score: float
    source: str
