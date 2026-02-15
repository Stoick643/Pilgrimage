"""Itinerary text parsing and HTML formatting."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services import get_image_url, get_weather_forecast_5d

logger = logging.getLogger(__name__)


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


def format_itinerary_weather(itinerary):
    """Format itinerary with city images and weather forecasts."""
    unsplash_url = "https://unsplash.com/?utm_source=your_app_name&utm_medium=referral"

    day_entries = extract_text_with_cities(itinerary)
    cities = [city for city, _ in day_entries]

    # Fetch all city data in parallel
    image_cache, weather_cache = _prefetch_city_data(cities)

    formatted = ""
    for city, day_plan in day_entries:
        lines = day_plan.strip().split('\n')
        title = f"<h3>{lines[0]}</h3>"
        plan = "<ul>" + "".join(f"<li>{line}</li>" for line in lines[1:] if line.strip()) + "</ul>"

        image_data = image_cache.get(city)
        if image_data:
            image_url, desc = image_data
        else:
            from src.services import ERROR_JPG, DEFAULT_DESCRIPTION
            image_url, desc = ERROR_JPG, DEFAULT_DESCRIPTION

        user_name = desc['name']
        links_html = desc['links_html']
        company = desc['company']

        image_html = f"""
        <div class="city-image d-flex align-items-center">
            <img src="{image_url}" alt="{city}" class="img-fluid" loading="lazy">
            <p class="ms-3"> {city} </p>
            <p class="ms-3 fs-6 fst-italic"> (Photo by <a href="{links_html}">{user_name}</a> on <a href="{unsplash_url}">{company})</a></p>
        </div>
        """

        weather = weather_cache.get(city)
        weather_block = weather_html_from_data(weather)

        formatted += f"{image_html}{title}{plan}{weather_block}<br><br>"

    return formatted


def weather_html(city):
    """Generate HTML for a city's 5-day weather forecast (standalone, non-cached)."""
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
