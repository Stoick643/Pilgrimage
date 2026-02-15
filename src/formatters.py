"""Itinerary text parsing and HTML formatting."""

import logging

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


def format_itinerary_weather(itinerary):
    """Format itinerary with city images and weather forecasts."""
    unsplash_url = "https://unsplash.com/?utm_source=your_app_name&utm_medium=referral"
    formatted = ""

    for city, day_plan in extract_text_with_cities(itinerary):
        lines = day_plan.strip().split('\n')
        title = f"<h3>{lines[0]}</h3>"
        plan = "<ul>" + "".join(f"<li>{line}</li>" for line in lines[1:] if line.strip()) + "</ul>"

        image_url, desc = get_image_url(city)
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

        formatted += f"{image_html}{title}{plan}{weather_html(city)}<br><br>"

    return formatted


def weather_html(city):
    """Generate HTML for a city's 5-day weather forecast."""
    forecast = get_weather_forecast_5d(city)

    if isinstance(forecast, str):
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
