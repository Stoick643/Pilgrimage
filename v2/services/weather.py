"""Weather service — OpenWeatherMap 5-day forecast."""

import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

WeatherEntry = dict[str, str | int]


async def get_forecast(city: str, api_key: str | None = None) -> list[WeatherEntry]:
    """Fetch 5-day weather forecast for a city (one entry per day at 15:00).

    Returns empty list if no API key or on error.
    """
    if not api_key:
        logger.warning("No OpenWeatherMap key — skipping weather")
        return []

    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        forecast: list[WeatherEntry] = []
        last_date: datetime | None = None

        for item in data.get("list", []):
            dt = datetime.strptime(item["dt_txt"], "%Y-%m-%d %H:%M:%S")

            if dt.hour == 15 and (last_date is None or last_date != dt.date()):
                weather_info = item.get("weather", [{}])[0]
                icon = weather_info.get("icon", "")
                forecast.append({
                    "date": dt.strftime("%d.%m"),
                    "temperature": round(item.get("main", {}).get("temp", 0)),
                    "description": weather_info.get("description", ""),
                    "icon": icon,
                    "icon_url": f"https://openweathermap.org/img/wn/{icon}.png",
                })
                last_date = dt.date()

        return forecast

    except Exception as e:
        logger.error(f"Error fetching weather for {city}: {e}")
        return []
