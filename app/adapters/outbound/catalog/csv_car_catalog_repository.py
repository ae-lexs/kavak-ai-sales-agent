"""CSV-backed car catalog repository adapter."""

import csv
import os
from pathlib import Path
from typing import Any, Optional

from app.application.dtos.car import CarSummary
from app.application.ports.car_catalog_repository import CarCatalogRepository


class CSVCarCatalogRepository(CarCatalogRepository):
    """CSV implementation of car catalog repository."""

    def __init__(self, csv_path: str = None) -> None:
        """
        Initialize CSV car catalog repository.

        Args:
            csv_path: Path to CSV file. Defaults to data/catalog.csv relative to project root.
        """
        if csv_path is None:
            # Default to data/catalog.csv relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            csv_path = str(project_root / "data" / "catalog.csv")
        self._csv_path = csv_path
        self._cars: list[CarSummary] = []
        self._load_catalog()

    def _load_catalog(self) -> None:
        """Load and parse the CSV catalog."""
        if not os.path.exists(self._csv_path):
            raise FileNotFoundError(f"Catalog CSV file not found: {self._csv_path}")

        self._cars = []
        with open(self._csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    car = self._map_row_to_car_summary(row)
                    if car:
                        self._cars.append(car)
                except (ValueError, KeyError) as e:
                    # Skip invalid rows, log error in production
                    continue

    def _map_row_to_car_summary(self, row: dict[str, str]) -> Optional[CarSummary]:
        """
        Map CSV row to CarSummary DTO.

        Args:
            row: CSV row as dictionary

        Returns:
            CarSummary DTO or None if row is invalid
        """
        try:
            # Map required fields
            car_id = str(row["stock_id"]).strip()
            make = str(row["make"]).strip()
            model = str(row["model"]).strip()
            year = int(row["year"])
            price_mxn = float(row["price"])
            mileage_km = int(row["km"])

            # Validate required fields
            if not car_id or not make or not model or year <= 0 or price_mxn <= 0:
                return None

            return CarSummary(
                id=car_id,
                make=make,
                model=model,
                year=year,
                price_mxn=price_mxn,
                mileage_km=mileage_km,
            )
        except (ValueError, KeyError):
            return None

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for matching (case-insensitive, trimmed).

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        return text.lower().strip()

    def _matches_make_model(self, car: CarSummary, make_filter: str = None, model_filter: str = None) -> bool:
        """
        Check if car matches make/model filters with normalization.

        Args:
            car: Car to check
            make_filter: Make filter (case-insensitive, token matching)
            model_filter: Model filter (case-insensitive, token matching)

        Returns:
            True if car matches filters
        """
        if make_filter:
            normalized_filter = self._normalize_text(make_filter)
            normalized_car_make = self._normalize_text(car.make)
            # Token matching: check if filter tokens are in car make
            filter_tokens = normalized_filter.split()
            car_tokens = normalized_car_make.split()
            if not any(token in normalized_car_make for token in filter_tokens):
                return False

        if model_filter:
            normalized_filter = self._normalize_text(model_filter)
            normalized_car_model = self._normalize_text(car.model)
            # Token matching: check if filter tokens are in car model
            filter_tokens = normalized_filter.split()
            if not any(token in normalized_car_model for token in filter_tokens):
                return False

        return True

    async def search(self, filters: dict[str, Any]) -> list[CarSummary]:
        """
        Search for cars matching the given filters.

        Args:
            filters: Dictionary of filter criteria:
                - max_price: Maximum price (float)
                - make: Make filter (case-insensitive, token matching)
                - model: Model filter (case-insensitive, token matching)
                - min_year: Minimum year (int, optional)
                - max_year: Maximum year (int, optional)

        Returns:
            List of car summaries matching the filters
        """
        results = self._cars.copy()

        # Filter by maximum budget
        if "max_price" in filters and filters["max_price"] is not None:
            max_price = float(filters["max_price"])
            results = [car for car in results if car.price_mxn <= max_price]

        # Filter by make
        if "make" in filters and filters["make"] is not None:
            make_filter = str(filters["make"])
            results = [car for car in results if self._matches_make_model(car, make_filter=make_filter)]

        # Filter by model
        if "model" in filters and filters["model"] is not None:
            model_filter = str(filters["model"])
            results = [car for car in results if self._matches_make_model(car, model_filter=model_filter)]

        # Filter by year range
        if "min_year" in filters and filters["min_year"] is not None:
            min_year = int(filters["min_year"])
            results = [car for car in results if car.year >= min_year]

        if "max_year" in filters and filters["max_year"] is not None:
            max_year = int(filters["max_year"])
            results = [car for car in results if car.year <= max_year]

        # Filter by need (if provided, map to make/model preferences)
        if "need" in filters and filters["need"] is not None:
            # For MVP, we can ignore this or map to common makes
            # This is a simple implementation - can be enhanced later
            pass

        return results

