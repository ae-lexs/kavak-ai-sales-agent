"""Money in Mexican Pesos value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MoneyMXN:
    """Money value object in Mexican Pesos."""

    amount: float

    def __post_init__(self) -> None:
        """Validate money amount."""
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")

    def __add__(self, other: "MoneyMXN") -> "MoneyMXN":
        """Add two money amounts."""
        return MoneyMXN(self.amount + other.amount)

    def __sub__(self, other: "MoneyMXN") -> "MoneyMXN":
        """Subtract two money amounts."""
        return MoneyMXN(self.amount - other.amount)

    def __mul__(self, multiplier: float) -> "MoneyMXN":
        """Multiply money by a scalar."""
        return MoneyMXN(self.amount * multiplier)

    def __truediv__(self, divisor: float) -> "MoneyMXN":
        """Divide money by a scalar."""
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return MoneyMXN(self.amount / divisor)

    def __lt__(self, other: "MoneyMXN") -> bool:
        """Compare less than."""
        return self.amount < other.amount

    def __le__(self, other: "MoneyMXN") -> bool:
        """Compare less than or equal."""
        return self.amount <= other.amount

    def __gt__(self, other: "MoneyMXN") -> bool:
        """Compare greater than."""
        return self.amount > other.amount

    def __ge__(self, other: "MoneyMXN") -> bool:
        """Compare greater than or equal."""
        return self.amount >= other.amount

