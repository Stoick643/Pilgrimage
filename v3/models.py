"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field


class ItineraryRequest(BaseModel):
    """Input for itinerary generation."""
    country: str = Field(..., min_length=1, description="Country or region to visit")
    duration: int = Field(..., ge=1, le=30, description="Number of days (1-30)")
    activities: list[str] = Field(default_factory=list, description="Preferred activities")
    language: str = Field(default="en", description="Output language code")


class DayEntry(BaseModel):
    """A single day parsed from &&& markers."""
    city: str
    content: str


class ItineraryResponse(BaseModel):
    """Itinerary response — parsed from &&& marker text."""
    days: list[DayEntry]
    country: str | None = None


class PhotoCredit(BaseModel):
    """Photo attribution."""
    name: str
    link: str
    company: str


class ImageResponse(BaseModel):
    """City image response."""
    image_url: str
    credit: PhotoCredit


class WeatherEntry(BaseModel):
    """Single weather forecast entry."""
    date: str
    temperature: int
    description: str
    icon: str
    icon_url: str


class WeatherResponse(BaseModel):
    """Weather forecast response."""
    forecast: list[WeatherEntry]


class GeoLocation(BaseModel):
    """Geocoded location."""
    name: str
    lat: float
    lng: float


class GeoResponse(BaseModel):
    """Geocoding response."""
    locations: list[GeoLocation]
