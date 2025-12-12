"""Annual Percentage Rate value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class APR:
    """Annual Percentage Rate value object."""

    rate: float  # As decimal (e.g., 0.10 for 10%)

    def __post_init__(self) -> None:
        """Validate APR rate."""
        if not 0 <= self.rate <= 1:
            raise ValueError("APR rate must be between 0 and 1 (0% to 100%)")

    @property
    def monthly_rate(self) -> float:
        """Get monthly interest rate."""
        return self.rate / 12

    @property
    def as_percentage(self) -> float:
        """Get APR as percentage (e.g., 10.0 for 10%)."""
        return self.rate * 100

