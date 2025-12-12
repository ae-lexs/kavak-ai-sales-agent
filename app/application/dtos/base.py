"""Base DTO class."""

from pydantic import BaseModel


class DTO(BaseModel):
    """Base class for application DTOs."""

    class Config:
        """Pydantic configuration."""

        frozen = True
