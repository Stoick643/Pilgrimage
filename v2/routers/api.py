"""API router — JSON endpoints + SSE streaming."""

import json
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from v2.config import settings
from v2.models import (
    GeoResponse,
    ImageResponse,
    ItineraryRequest,
    ItineraryResponse,
    PhotoCredit,
    WeatherResponse,
)
from v2.services.geocoding import geocode_cities
from v2.services.images import get_image_url
from v2.services.llm import build_prompt, llm_complete, llm_stream
from v2.services.weather import get_forecast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


def _get_clients(request: Request) -> list:
    """Get LLM clients from app state."""
    clients = getattr(request.app.state, "llm_clients", [])
    if not clients:
        raise HTTPException(status_code=500, detail="No LLM provider configured.")
    return clients


def _get_http_client(request: Request) -> httpx.AsyncClient:
    """Get shared HTTP client from app state."""
    return getattr(request.app.state, "http_client", None)


@router.post("/generate", response_model=ItineraryResponse)
async def generate_itinerary(req: ItineraryRequest, request: Request):
    """Generate a complete itinerary. Returns structured JSON."""
    clients = _get_clients(request)

    activities_text = ", ".join(req.activities) if req.activities else "general sightseeing"

    system_prompt, user_prompt, max_tokens = build_prompt(
        active_prompt=settings.active_prompt,
        duration=req.duration,
        country=req.country,
        activities=activities_text,
        language=req.language,
    )

    logger.info(
        f"Generating itinerary: {req.country}, {req.duration} days, "
        f"lang={req.language}, activities={activities_text}"
    )

    try:
        result = await llm_complete(
            clients=clients,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Check for error response from LLM
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Inject country so frontend can pass it to city-image for disambiguation
    result["country"] = req.country
    return result


@router.post("/stream")
async def stream_itinerary(req: ItineraryRequest, request: Request):
    """Stream itinerary generation via Server-Sent Events."""
    clients = _get_clients(request)

    activities_text = ", ".join(req.activities) if req.activities else "general sightseeing"

    system_prompt, user_prompt, max_tokens = build_prompt(
        active_prompt=settings.active_prompt,
        duration=req.duration,
        country=req.country,
        activities=activities_text,
        language=req.language,
    )

    logger.info(
        f"Streaming itinerary: {req.country}, {req.duration} days, "
        f"lang={req.language}, activities={activities_text}"
    )

    async def generate():
        try:
            async for chunk in llm_stream(
                clients=clients,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            ):
                data = json.dumps({"text": chunk})
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/city-image", response_model=ImageResponse)
async def city_image(request: Request, city: str, country: str | None = None):
    """Fetch image for a city. Pass country for disambiguation (e.g. Syracuse + Sicily)."""
    if not city.strip():
        raise HTTPException(status_code=400, detail="city parameter required")

    http_client = _get_http_client(request)
    image_url, credit = await get_image_url(
        city=city.strip(),
        country=country,
        unsplash_key=settings.unsplash_access_key,
        http_client=http_client,
    )
    return ImageResponse(
        image_url=image_url,
        credit=PhotoCredit(**credit),
    )


@router.get("/city-weather", response_model=WeatherResponse)
async def city_weather(request: Request, city: str):
    """Fetch 5-day weather for a city."""
    if not city.strip():
        raise HTTPException(status_code=400, detail="city parameter required")

    http_client = _get_http_client(request)
    forecast = await get_forecast(city.strip(), settings.openweathermap_api_key, http_client)
    return WeatherResponse(forecast=forecast)


@router.get("/geocode", response_model=GeoResponse)
async def geocode(request: Request, cities: str):
    """Geocode a comma-separated list of cities."""
    if not cities.strip():
        raise HTTPException(status_code=400, detail="cities parameter required")

    http_client = _get_http_client(request)
    city_list = [c.strip() for c in cities.split(",") if c.strip()]
    locations = await geocode_cities(city_list, settings.google_directions_api_key, http_client)
    return GeoResponse(locations=locations)
