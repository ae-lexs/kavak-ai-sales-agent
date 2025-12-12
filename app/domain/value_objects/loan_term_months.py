"""Loan term in months value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoanTermMonths:
    """Loan term in months value object."""

    months: int

    def __post_init__(self) -> None:
        """Validate loan term."""
        if self.months <= 0:
            raise ValueError("Loan term must be positive")
        if self.months not in [36, 48, 60, 72]:
            raise ValueError("Loan term must be 36, 48, 60, or 72 months")

    @property
    def years(self) -> float:
        """Get loan term in years."""
        return self.months / 12
