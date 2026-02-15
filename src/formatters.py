"""Itinerary text parsing and data preparation."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services import get_image_url, get_weather_forecast_5d, ERROR_JPG, DEFAULT_DESCRIPTION

logger = logging.getLogger(__name__)

UNSPLASH_URL = "https://unsplash.com/?utm_source=your_app_name&utm_medium=referral"


def extract_text_with_cities(text):
    """Parse itinerary text into list of (city, content) tuples based on '&&&' markers."""
    result = []
    lines = text.split('\n')
    current_block = []
    current_city = None

    for line in lines:
        line = line.strip()
        if line.startswith('&&&'):
            if current_block and current_city:
                result.append((current_city, '\n'.join(current_block)))
                current_block = []
            current_city = line[3:].strip()
        else:
            if current_city:
                current_block.append(line)

    if current_block and current_city:
        result.append((current_city, '\n'.join(current_block)))

    return result


def _prefetch_city_data(cities):
    """Fetch images and weather for all unique cities in parallel. Returns cached dicts."""
    unique_cities = list(dict.fromkeys(cities))  # preserve order, deduplicate
    image_cache = {}
    weather_cache = {}

    start = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        image_futures = {executor.submit(get_image_url, city): city for city in unique_cities}
        weather_futures = {executor.submit(get_weather_forecast_5d, city): city for city in unique_cities}

        for future in as_completed(image_futures):
            city = image_futures[future]
            try:
                image_cache[city] = future.result()
            except Exception as e:
                logger.error(f"Error fetching image for {city}: {e}")
                image_cache[city] = None

        for future in as_completed(weather_futures):
            city = weather_futures[future]
            try:
                weather_cache[city] = future.result()
            except Exception as e:
                logger.error(f"Error fetching weather for {city}: {e}")
                weather_cache[city] = None

    elapsed = round(time.time() - start, 2)
    logger.info(f"Prefetched data for {len(unique_cities)} cities in {elapsed}s (parallel)")

    return image_cache, weather_cache


def prepare_itinerary_data(itinerary):
    """Parse itinerary and fetch all city data. Returns structured data for templates."""
    day_entries = extract_text_with_cities(itinerary)
    cities = [city for city, _ in day_entries]

    image_cache, weather_cache = _prefetch_city_data(cities)

    days = []
    for city, day_plan in day_entries:
        lines = day_plan.strip().split('\n')
        title = lines[0] if lines else ""
        activities = [line for line in lines[1:] if line.strip()]

        image_data = image_cache.get(city)
        if image_data:
            image_url, desc = image_data
        else:
            image_url, desc = ERROR_JPG, DEFAULT_DESCRIPTION

        forecast = weather_cache.get(city)
        if isinstance(forecast, str) or forecast is None:
            forecast = []

        # Add icon URLs to forecast entries
        for entry in forecast:
            entry['icon_url'] = f"https://openweathermap.org/img/wn/{entry['icon']}.png"

        days.append({
            'city': city,
            'title': title,
            'activities': activities,
            'image_url': image_url,
            'photo_credit': {
                'name': desc['name'],
                'link': desc['links_html'],
                'company': desc['company'],
            },
            'forecast': forecast,
        })

    return {'days': days, 'unsplash_url': UNSPLASH_URL}


def weather_html(city):
    """Generate HTML for a city's 5-day weather forecast (standalone, for tests)."""
    forecast = get_weather_forecast_5d(city)
    return weather_html_from_data(forecast)


def weather_html_from_data(forecast):
    """Generate HTML from weather forecast data."""
    if forecast is None or isinstance(forecast, str):
        return ""

    html = "<div class='weather-container d-flex justify-content-between'>"
    for day in forecast:
        icon_url = f"https://openweathermap.org/img/wn/{day['icon']}.png"
        html += f"""
        <div class="weather-icon">
            <img src="{icon_url}" class="img-fluid" loading="lazy">
            <p>{day['temperature']} °C ({day['date']})</p>
        </div>
        """
    html += "</div>"
    return html
