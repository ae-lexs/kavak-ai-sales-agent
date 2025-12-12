"""Mock car catalog repository adapter."""

from typing import Any

from app.application.dtos.car import CarSummary
from app.application.ports.car_catalog_repository import CarCatalogRepository


class MockCarCatalogRepository(CarCatalogRepository):
    """Mock implementation of car catalog repository for testing/development."""

    async def search(self, filters: dict[str, Any]) -> list[CarSummary]:
        """
        Search for cars matching the given filters.

        Args:
            filters: Dictionary of filter criteria

        Returns:
            List of 3 mocked car summaries
        """
        # Return 3 mocked cars for now
        return [
            CarSummary(
                id="car_001",
                make="Toyota",
                model="Corolla",
                year=2022,
                price_mxn=350000.0,
                mileage_km=15000,
            ),
            CarSummary(
                id="car_002",
                make="Honda",
                model="Civic",
                year=2021,
                price_mxn=320000.0,
                mileage_km=25000,
            ),
            CarSummary(
                id="car_003",
                make="Nissan",
                model="Sentra",
                year=2023,
                price_mxn=380000.0,
                mileage_km=8000,
            ),
        ]

