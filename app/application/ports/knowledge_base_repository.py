"""Knowledge base repository port."""

from abc import ABC, abstractmethod

from app.application.dtos.knowledge import KnowledgeChunk


class KnowledgeBaseRepository(ABC):
    """Port interface for knowledge base repository."""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        """
        Retrieve relevant knowledge chunks for a query.

        Args:
            query: Search query
            top_k: Maximum number of chunks to return

        Returns:
            List of knowledge chunks sorted by relevance score (highest first)
        """
        pass
