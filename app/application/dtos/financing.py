"""Financing DTOs."""

from app.application.dtos.base import DTO


class FinancingPlan(DTO):
    """Financing plan DTO."""

    term_months: int
    financed_amount: float
    monthly_payment: float
    total_paid: float
    total_interest: float

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "term_months": 48,
                "financed_amount": 315000.0,
                "monthly_payment": 7985.50,
                "total_paid": 383304.0,
                "total_interest": 68304.0,
            }
        }
