"""Geocoding service — Google Maps geocoding."""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


async def geocode_city(
    city: str,
    api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> dict | None:
    """Geocode a single city to {name, lat, lng}. Returns None on failure."""
    if not api_key:
        logger.warning("No Google API key — skipping geocoding")
        return None

    url = (
        f"https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={city}&key={api_key}"
    )

    try:
        client = http_client or httpx.AsyncClient()
        try:
            response = await client.get(url)
            data = response.json()
        finally:
            if not http_client:
                await client.aclose()

        if data["status"] == "OK":
            loc = data["results"][0]["geometry"]["location"]
            logger.info(f"Geocoded {city}: {loc['lat']}, {loc['lng']}")
            return {"name": city, "lat": loc["lat"], "lng": loc["lng"]}
        else:
            logger.warning(f"Geocoding failed for {city}: {data['status']}")
            return None

    except Exception as e:
        logger.error(f"Error geocoding {city}: {e}")
        return None


async def geocode_cities(
    cities: list[str],
    api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict]:
    """Geocode multiple cities concurrently. Deduplicates, preserves order."""
    unique = list(dict.fromkeys(cities))  # deduplicate, preserve order

    tasks = [geocode_city(city, api_key, http_client) for city in unique]
    results = await asyncio.gather(*tasks)

    cache = {city: result for city, result in zip(unique, results) if result}

    # Build results in original order (including duplicates)
    locations = []
    for city in cities:
        if city in cache:
            locations.append(cache[city])
        else:
            logger.warning(f"No geocode result for {city}")

    return locations
