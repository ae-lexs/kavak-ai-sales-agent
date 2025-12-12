"""Base DTO class."""

from pydantic import BaseModel, ConfigDict


class DTO(BaseModel):
    """Base class for application DTOs."""

    model_config = ConfigDict(frozen=True)
