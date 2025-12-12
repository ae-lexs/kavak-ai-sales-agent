"""Car DTOs."""

from app.application.dtos.base import DTO


class CarSummary(DTO):
    """Car summary DTO."""

    id: str
    make: str
    model: str
    year: int
    price_mxn: float
    mileage_km: int

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "car_001",
                "make": "Toyota",
                "model": "Corolla",
                "year": 2022,
                "price_mxn": 350000.0,
                "mileage_km": 15000,
            }
        }
