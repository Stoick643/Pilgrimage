"""Pages router — HTML page routes."""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from v3.config import settings
from v3.services.cache import Cache

logger = logging.getLogger(__name__)

V3_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(V3_DIR / "templates"))

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/plan", response_class=HTMLResponse)
async def plan(
    request: Request,
    country: str = "",
    duration: int = 5,
    language: str = "en",
    activities: list[str] | None = None,
):
    """Show itinerary page and start streaming."""
    if not country.strip():
        return templates.TemplateResponse(request, "index.html", {
            "error": "Please enter a country or region.",
        }, status_code=400)
    if duration < 1 or duration > 30:
        return templates.TemplateResponse(request, "index.html", {
            "error": "Duration must be between 1 and 30 days.",
        }, status_code=400)

    activities = activities or []

    # Build the stream URL and body for the frontend JS to call
    stream_body = {
        "country": country.strip(),
        "duration": duration,
        "activities": activities,
        "language": language,
    }

    return templates.TemplateResponse(request, "itinerary.html", {
        "country": country.strip(),
        "duration": duration,
        "google_api_key": settings.google_directions_api_key or "",
        "stream_url": "/api/stream",
        "stream_body": stream_body,
        "shared_trip": None,
    })


@router.get("/trip/{trip_id}", response_class=HTMLResponse)
async def shared_trip(request: Request, trip_id: str):
    """View a shared trip."""
    cache: Cache | None = getattr(request.app.state, "cache", None)
    if not cache:
        return RedirectResponse("/")

    trip = cache.get_shared_trip(trip_id)
    if not trip:
        return templates.TemplateResponse(request, "error.html", {
            "error_title": "Trip Not Found",
            "error_message": "This shared trip link is invalid or has been removed.",
        }, status_code=404)

    return templates.TemplateResponse(request, "shared_trip.html", {
        "trip": trip,
        "trip_id": trip_id,
        "google_api_key": settings.google_directions_api_key or "",
    })
