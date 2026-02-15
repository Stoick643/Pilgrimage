"""Image service — Unsplash search with country disambiguation."""

import logging
import random

import httpx

logger = logging.getLogger(__name__)

ERROR_JPG = "https://img.freepik.com/free-vector/funny-error-404-background-design_1167-219.jpg"
MY_PHOTOS = "https://flickriver.com/photos/belatrix/popular-interesting/"

PhotoCredit = dict[str, str]

DEFAULT_CREDIT: PhotoCredit = {
    "name": "Darko Mulej",
    "link": MY_PHOTOS,
    "company": "Flickr",
}

# Personal photo collection — used before Unsplash
MY_IMAGES: dict[str, list[str]] = {
    "Rome": [
        "https://live.staticflickr.com/2567/3733159660_15bc2cf915_z.jpg",
        "https://live.staticflickr.com/2527/3731547873_f2e21555bd_z.jpg",
        "https://live.staticflickr.com/3484/3732280478_0efa027a1d_z.jpg",
    ],
    "Venice": [
        "https://live.staticflickr.com/3588/3516271920_bb48869777_z.jpg",
        "https://live.staticflickr.com/3616/3518637231_2f849c1228_z.jpg",
        "https://live.staticflickr.com/3584/3516274972_3fedea6e1c_z.jpg",
        "https://live.staticflickr.com/3613/3517500225_6e27f7c8c4_z.jpg",
    ],
}


async def get_image_url(
    city: str,
    country: str | None = None,
    unsplash_key: str | None = None,
    seen_urls: set[str] | None = None,
) -> tuple[str, PhotoCredit]:
    """Fetch a city image. Priority: personal → Unsplash → fallback.

    Args:
        city: City name to search for.
        country: Country name to append for disambiguation (e.g. "Syracuse Sicily").
        unsplash_key: Unsplash API key.
        seen_urls: Set of already-used URLs to avoid duplicates across days.
    """
    logger.info(f"Fetching image for {city}")

    if city in MY_IMAGES:
        urls = MY_IMAGES[city]
        if seen_urls:
            available = [u for u in urls if u not in seen_urls]
            url = random.choice(available) if available else random.choice(urls)
        else:
            url = random.choice(urls)
        return url, DEFAULT_CREDIT

    if not unsplash_key:
        logger.warning("No Unsplash key — using fallback image")
        return ERROR_JPG, DEFAULT_CREDIT

    # Append country for disambiguation ("Syracuse Sicily" not "Syracuse")
    query = f"{city} {country}" if country else city

    try:
        async with httpx.AsyncClient() as client:
            params = {
                "query": query,
                "per_page": 5,
                "page": random.randint(1, 3),
                "client_id": unsplash_key,
                "w": 1000,
                "h": 1000,
            }
            response = await client.get("https://api.unsplash.com/search/photos", params=params)
            logger.info(f"Unsplash API status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                # Filter out already-seen URLs
                if seen_urls:
                    results = [r for r in results if r["urls"]["regular"] not in seen_urls]

                if results:
                    photo = results[0]
                    image_url = photo["urls"]["regular"]
                    credit: PhotoCredit = {
                        "name": photo["user"]["name"],
                        "link": photo["user"]["links"]["html"],
                        "company": "Unsplash",
                    }
                    return image_url, credit

        logger.warning(f"Unsplash returned no results for '{query}'")
        return ERROR_JPG, DEFAULT_CREDIT

    except Exception as e:
        logger.error(f"Error fetching image for {city}: {e}")
        return ERROR_JPG, DEFAULT_CREDIT
