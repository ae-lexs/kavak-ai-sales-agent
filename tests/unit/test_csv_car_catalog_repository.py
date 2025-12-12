"""Unit tests for CSVCarCatalogRepository."""

import os
import tempfile

import pytest

from app.adapters.outbound.catalog.csv_car_catalog_repository import CSVCarCatalogRepository
from app.application.dtos.car import CarSummary


@pytest.fixture
def sample_csv_content() -> str:
    """Sample CSV content for testing."""
    return """stock_id,km,price,make,model,year,version,bluetooth,largo,ancho,altura,car_play
243587,77400,461999.0,Volkswagen,Touareg,2018,3.0 V6 TDI WOLFSBURG EDITION AUTO 4WD,Sí,4801.0,1940.0,1709.0,
229702,102184,660999.0,Land Rover,Discovery Sport,2018,2.0 HSE LUXURY AUTO 4WD,Sí,4599.0,2069.0,1724.0,
160422,56419,866999.0,BMW,Serie 2,2018,3.0 M2 DCT,Sí,4468.0,1854.0,1410.0,Sí
308634,76000,238999.0,Toyota,Avanza,2018,1.5 XLE AT,Sí,4140.0,1660.0,1695.0,
123456,50000,350000.0,Toyota,Corolla,2020,1.8 LE AT,,4140.0,1660.0,1695.0,
789012,30000,450000.0,Honda,Civic,2021,2.0 EX AT,Sí,4500.0,1800.0,1400.0,Sí"""  # noqa: E501


@pytest.fixture
def temp_csv_file(sample_csv_content: str) -> str:
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(sample_csv_content)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


@pytest.mark.asyncio
async def test_csv_loading(temp_csv_file: str) -> None:
    """Test that CSV is loaded correctly."""
    repository = CSVCarCatalogRepository(csv_path=temp_csv_file)

    cars = await repository.search({})

    assert len(cars) == 6
    assert all(isinstance(car, CarSummary) for car in cars)


@pytest.mark.asyncio
async def test_column_mapping(temp_csv_file: str) -> None:
    """Test that CSV columns are mapped correctly to DTO."""
    repository = CSVCarCatalogRepository(csv_path=temp_csv_file)

    cars = await repository.search({})

    # Check first car (Volkswagen Touareg)
    touareg = next((car for car in cars if car.id == "243587"), None)
    assert touareg is not None
    assert touareg.id == "243587"
    assert touareg.make == "Volkswagen"
    assert touareg.model == "Touareg"
    assert touareg.year == 2018
    assert touareg.price_mxn == 461999.0
    assert touareg.mileage_km == 77400

    # Check Toyota Avanza
    avanza = next((car for car in cars if car.id == "308634"), None)
    assert avanza is not None
    assert avanza.make == "Toyota"
    assert avanza.model == "Avanza"
    assert avanza.price_mxn == 238999.0


@pytest.mark.asyncio
async def test_budget_filtering(temp_csv_file: str) -> None:
    """Test filtering by maximum budget."""
    repository = CSVCarCatalogRepository(csv_path=temp_csv_file)

    # Filter by max price
    cars = await repository.search({"max_price": 500000.0})

    assert len(cars) == 4  # Volkswagen, Toyota Avanza, Toyota Corolla, Honda Civic
    assert all(car.price_mxn <= 500000.0 for car in cars)

    # Test with lower budget
    cars_low = await repository.search({"max_price": 300000.0})
    assert len(cars_low) == 1  # Only Toyota Avanza
    assert cars_low[0].id == "308634"


@pytest.mark.asyncio
async def test_make_filtering(temp_csv_file: str) -> None:
    """Test filtering by make with normalization."""
    repository = CSVCarCatalogRepository(csv_path=temp_csv_file)

    # Case-insensitive make filter
    cars = await repository.search({"make": "toyota"})
    assert len(cars) == 2
    assert all(car.make.lower() == "toyota" for car in cars)

    # With whitespace
    cars2 = await repository.search({"make": "  Toyota  "})
    assert len(cars2) == 2

    # Token matching
    cars3 = await repository.search({"make": "land"})
    assert len(cars3) == 1
    assert cars3[0].make == "Land Rover"


@pytest.mark.asyncio
async def test_model_filtering(temp_csv_file: str) -> None:
    """Test filtering by model with normalization."""
    repository = CSVCarCatalogRepository(csv_path=temp_csv_file)

    # Case-insensitive model filter
    cars = await repository.search({"model": "corolla"})
    assert len(cars) == 1
    assert cars[0].model == "Corolla"

    # Token matching
    cars2 = await repository.search({"model": "discovery"})
    assert len(cars2) == 1
    assert cars2[0].model == "Discovery Sport"


@pytest.mark.asyncio
async def test_year_range_filtering(temp_csv_file: str) -> None:
    """Test filtering by year range."""
    repository = CSVCarCatalogRepository(csv_path=temp_csv_file)

    # Filter by min year
    cars = await repository.search({"min_year": 2020})
    assert len(cars) == 2  # Toyota Corolla 2020, Honda Civic 2021
    assert all(car.year >= 2020 for car in cars)

    # Filter by max year
    cars2 = await repository.search({"max_year": 2018})
    assert len(cars2) == 4  # All 2018 cars

    # Filter by both
    cars3 = await repository.search({"min_year": 2020, "max_year": 2021})
    assert len(cars3) == 2


@pytest.mark.asyncio
async def test_combined_filters(temp_csv_file: str) -> None:
    """Test combining multiple filters."""
    repository = CSVCarCatalogRepository(csv_path=temp_csv_file)

    # Make + budget
    cars = await repository.search({"make": "Toyota", "max_price": 400000.0})
    assert len(cars) == 2
    assert all(car.make == "Toyota" for car in cars)
    assert all(car.price_mxn <= 400000.0 for car in cars)

    # Make + model + budget
    cars2 = await repository.search({"make": "Toyota", "model": "Corolla", "max_price": 400000.0})
    assert len(cars2) == 1
    assert cars2[0].model == "Corolla"


@pytest.mark.asyncio
async def test_empty_results(temp_csv_file: str) -> None:
    """Test that filters return empty list when no matches."""
    repository = CSVCarCatalogRepository(csv_path=temp_csv_file)

    # Non-existent make
    cars = await repository.search({"make": "Ferrari"})
    assert len(cars) == 0

    # Budget too low
    cars2 = await repository.search({"max_price": 100000.0})
    assert len(cars2) == 0


@pytest.mark.asyncio
async def test_invalid_csv_file() -> None:
    """Test that invalid CSV file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        CSVCarCatalogRepository(csv_path="/nonexistent/file.csv")


@pytest.mark.asyncio
async def test_invalid_rows_skipped() -> None:
    """Test that invalid CSV rows are skipped."""
    invalid_csv = """stock_id,km,price,make,model,year,version,bluetooth,largo,ancho,altura,car_play
123,50000,350000.0,Toyota,Corolla,2020,1.8 LE AT,,4140.0,1660.0,1695.0,
invalid,,,Missing,Fields,0,,,,
456,30000,450000.0,Honda,Civic,2021,2.0 EX AT,Sí,4500.0,1800.0,1400.0,Sí"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(invalid_csv)
        temp_path = f.name

    try:
        repository = CSVCarCatalogRepository(csv_path=temp_path)
        cars = await repository.search({})
        # Should only have 2 valid cars
        assert len(cars) == 2
        assert all(car.id in ["123", "456"] for car in cars)
    finally:
        os.unlink(temp_path)
