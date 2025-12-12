"""Car catalog repository port."""

from abc import ABC, abstractmethod
from typing import Any

from app.application.dtos.car import CarSummary


class CarCatalogRepository(ABC):
    """Port interface for car catalog repository."""

    @abstractmethod
    async def search(self, filters: dict[str, Any]) -> list[CarSummary]:
        """
        Search for cars matching the given filters.

        Args:
            filters: Dictionary of filter criteria (e.g., {"make": "Toyota", "max_price": 500000})

        Returns:
            List of car summaries matching the filters
        """
        pass
