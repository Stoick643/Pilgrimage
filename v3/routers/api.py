"""API router — JSON endpoints + SSE streaming."""

import json
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from v3.config import settings
from v3.models import (
    GeoResponse,
    ImageResponse,
    ItineraryRequest,
    ItineraryResponse,
    PhotoCredit,
    ShareRequest,
    ShareResponse,
    WeatherResponse,
)
from v3.services.cache import Cache, make_cache_key
from v3.services.geocoding import geocode_cities
from v3.services.images import get_image_url
from v3.services.llm import build_prompt, llm_complete, llm_stream, parse_marker_text
from v3.services.weather import get_forecast

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


def _get_cache(request: Request) -> Cache | None:
    """Get cache from app state."""
    return getattr(request.app.state, "cache", None)


@router.post("/generate", response_model=ItineraryResponse)
async def generate_itinerary(req: ItineraryRequest, request: Request):
    """Generate a complete itinerary. Returns parsed &&& marker text as JSON."""
    clients = _get_clients(request)
    cache = _get_cache(request)

    activities_text = ", ".join(sorted(req.activities)) if req.activities else "general sightseeing"

    # Check cache first
    cache_key = make_cache_key("itinerary", req.country, str(req.duration), activities_text, req.language, settings.active_prompt)
    if cache:
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for itinerary: {req.country}")
            return cached

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
        raw_text = await llm_complete(
            clients=clients,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Check for error response from LLM
    if raw_text.strip().startswith("Error"):
        raise HTTPException(status_code=400, detail=raw_text.strip())

    # Parse &&& markers into structured response
    days = parse_marker_text(raw_text)
    if not days:
        raise HTTPException(status_code=502, detail="Failed to parse itinerary — no day markers found.")

    result = {"days": days, "country": req.country}

    # Cache the result (24 hours)
    if cache:
        cache.set(cache_key, result, ttl=86400)

    return result


@router.post("/stream")
async def stream_itinerary(req: ItineraryRequest, request: Request):
    """Stream itinerary generation via Server-Sent Events.

    Cache-aware: if a cached result exists, streams it back instantly.
    On cache miss, streams from LLM and saves the full text to cache.
    """
    clients = _get_clients(request)
    cache = _get_cache(request)

    activities_text = ", ".join(sorted(req.activities)) if req.activities else "general sightseeing"

    # Same cache key as /api/generate — they share the cache
    cache_key = make_cache_key("stream", req.country, str(req.duration), activities_text, req.language, settings.active_prompt)

    system_prompt, user_prompt, max_tokens = build_prompt(
        active_prompt=settings.active_prompt,
        duration=req.duration,
        country=req.country,
        activities=activities_text,
        language=req.language,
    )

    # Check cache first
    cached_text = None
    if cache:
        cached_text = cache.get(cache_key)

    if cached_text:
        logger.info(f"Cache hit for stream: {req.country}")

        async def generate_cached():
            # Stream cached text in line-sized chunks for natural rendering
            for line in cached_text.split("\n"):
                data = json.dumps({"text": line + "\n"})
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(generate_cached(), media_type="text/event-stream")

    logger.info(
        f"Streaming itinerary: {req.country}, {req.duration} days, "
        f"lang={req.language}, activities={activities_text}"
    )

    async def generate():
        full_text = ""
        try:
            async for chunk in llm_stream(
                clients=clients,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            ):
                full_text += chunk
                data = json.dumps({"text": chunk})
                yield f"data: {data}\n\n"

            # Cache the full text after successful stream (24 hours)
            if cache and full_text.strip():
                cache.set(cache_key, full_text, ttl=86400)
                logger.info(f"Cached stream result for: {req.country}")

            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/share", response_model=ShareResponse)
async def share_itinerary(req: ShareRequest, request: Request):
    """Save an itinerary for sharing. Returns a shareable trip ID."""
    cache = _get_cache(request)
    if not cache:
        raise HTTPException(status_code=500, detail="Storage unavailable")

    trip_id = cache.save_shared_trip(
        country=req.country,
        duration=req.duration,
        language=req.language,
        activities=req.activities,
        content=req.content,
    )

    return ShareResponse(id=trip_id, url=f"/trip/{trip_id}")


@router.get("/city-image", response_model=ImageResponse)
async def city_image(request: Request, city: str, country: str | None = None, page: int = 1):
    """Fetch image for a city. Pass country for disambiguation, page for variety."""
    if not city.strip():
        raise HTTPException(status_code=400, detail="city parameter required")

    cache = _get_cache(request)
    cache_key = make_cache_key("image", city, country or "", str(page))
    if cache:
        cached = cache.get(cache_key)
        if cached:
            return ImageResponse(**cached)

    http_client = _get_http_client(request)
    image_url, credit = await get_image_url(
        city=city.strip(),
        country=country,
        page=page,
        unsplash_key=settings.unsplash_access_key,
        http_client=http_client,
    )
    result = ImageResponse(image_url=image_url, credit=PhotoCredit(**credit))

    if cache:
        cache.set(cache_key, result.model_dump(), ttl=604800)  # 7 days

    return result


@router.get("/city-weather", response_model=WeatherResponse)
async def city_weather(request: Request, city: str):
    """Fetch 5-day weather for a city."""
    if not city.strip():
        raise HTTPException(status_code=400, detail="city parameter required")

    cache = _get_cache(request)
    cache_key = make_cache_key("weather", city)
    if cache:
        cached = cache.get(cache_key)
        if cached:
            return WeatherResponse(**cached)

    http_client = _get_http_client(request)
    forecast = await get_forecast(city.strip(), settings.openweathermap_api_key, http_client)
    result = WeatherResponse(forecast=forecast)

    if cache:
        cache.set(cache_key, result.model_dump(), ttl=10800)  # 3 hours

    return result


@router.get("/geocode", response_model=GeoResponse)
async def geocode(request: Request, cities: str):
    """Geocode a comma-separated list of cities."""
    if not cities.strip():
        raise HTTPException(status_code=400, detail="cities parameter required")

    cache = _get_cache(request)
    cache_key = make_cache_key("geo", cities)
    if cache:
        cached = cache.get(cache_key)
        if cached:
            return GeoResponse(**cached)

    http_client = _get_http_client(request)
    city_list = [c.strip() for c in cities.split(",") if c.strip()]
    locations = await geocode_cities(city_list, settings.google_directions_api_key, http_client)
    result = GeoResponse(locations=locations)

    if cache:
        cache.set(cache_key, result.model_dump(), ttl=0)  # Never expires

    return result
