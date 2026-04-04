from typing import Literal

from pydantic import BaseModel, Field


class ExtractedNetArea(BaseModel):
    label: str | None = Field(
        default=None,
        description="Optional label for the covered area, e.g. 'Balcon frente'.",
    )
    width_meters: float | None = Field(
        default=None,
        description="Width of this covered area in meters.",
    )
    height_meters: float | None = Field(
        default=None,
        description="Height of this covered area in meters.",
    )


class ExtractedClientData(BaseModel):
    """Structured client data extracted from a collection conversation turn."""

    name: str | None = Field(
        default=None,
        description="Full name of the client, or null if not yet provided.",
    )
    street: str | None = Field(
        default=None,
        description="Street address including number, e.g. 'Corrientes 1234'.",
    )
    city: str | None = Field(
        default=None,
        description="City name, e.g. 'Rosario'.",
    )
    floor_or_apartment: str | None = Field(
        default=None,
        description="Floor or apartment identifier, e.g. '3B' or 'Piso 2'.",
    )
    installation_type: Literal["balcony", "roof", "stairwell"] | None = Field(
        default=None,
        description="Type of net installation location.",
    )
    net_areas: list[ExtractedNetArea] = Field(
        default_factory=list,
        description="One or more net areas to cover, each with width and height.",
    )
    urgency: str | None = Field(
        default=None,
        description="Urgency or preferred installation date expressed by the client.",
    )
