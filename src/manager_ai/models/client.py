from enum import Enum

from pydantic import BaseModel


class InstallationType(str, Enum):
    BALCONY = "balcony"
    ROOF = "roof"
    STAIRWELL = "stairwell"


class Address(BaseModel):
    street: str | None = None
    city: str | None = None
    floor_or_apartment: str | None = None


class Dimensions(BaseModel):
    width_meters: float | None = None
    height_meters: float | None = None


class ClientChart(BaseModel):
    name: str | None = None
    phone: str
    address: Address = Address()
    installation_type: InstallationType | None = None
    dimensions: Dimensions | None = None
    urgency: str | None = None
