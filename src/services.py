import logging
import os
import random
from datetime import datetime, timedelta
from typing import Any

import requests
from flask import Flask

logger = logging.getLogger(__name__)

UNSPLASH_ACCESS_KEY: str | None = os.getenv('UNSPLASH_ACCESS_KEY')
OPENWEATHERMAP_API_KEY: str | None = os.getenv('OPENWEATHERMAP_API_KEY')

# LLM configuration — priority: DeepSeek > Moonshot > Anthropic
DEEPSEEK_API_KEY: str | None = os.getenv('DEEPSEEK_API_KEY')
MOONSHOT_API_KEY: str | None = os.getenv('MOONSHOT_API_KEY')
ANTHROPIC_API_KEY: str | None = os.getenv('ANTHROPIC_API_KEY')

# Provider configs: (env key, default model, base URL, provider name)
_PROVIDERS: list[tuple[str | None, str, str, str | None, str]] = [
    (DEEPSEEK_API_KEY, 'your_deepseek_api_key_here', 'DEEPSEEK_MODEL', "https://api.deepseek.com", "DeepSeek"),
    (MOONSHOT_API_KEY, 'your_moonshot_api_key_here', 'MOONSHOT_MODEL', "https://api.moonshot.cn/v1", "Moonshot"),
    (ANTHROPIC_API_KEY, 'your_anthropic_api_key_here', 'ANTHROPIC_MODEL', None, "Anthropic"),
]

# Default models — used if not specified in .env
_DEFAULT_MODELS: dict[str, str] = {
    "DeepSeek": "deepseek-chat",
    "Moonshot": "kimi-k2.5",
    "Anthropic": "claude-sonnet-4-5",
}

# Build list of all available providers (in priority order)
_AVAILABLE_PROVIDERS: list[dict[str, str | None]] = []

for _key, _placeholder, _model_env, _base_url, _provider in _PROVIDERS:
    if _key and _key != _placeholder:
        _AVAILABLE_PROVIDERS.append({
            "api_key": _key,
            "base_url": _base_url,
            "model": os.getenv(_model_env, _DEFAULT_MODELS[_provider]),
            "provider": _provider,
        })

# Primary provider (for logging and backward compat)
LLM_PROVIDER: str | None = _AVAILABLE_PROVIDERS[0]["provider"] if _AVAILABLE_PROVIDERS else None
LLM_MODEL: str | None = _AVAILABLE_PROVIDERS[0]["model"] if _AVAILABLE_PROVIDERS else None

UNSPLASH_URL: str = "https://unsplash.com/?utm_source=your_app_name&utm_medium=referral"
MY_PHOTOS: str = "https://flickriver.com/photos/belatrix/popular-interesting/"
ERROR_JPG: str = "https://img.freepik.com/free-vector/funny-error-404-background-design_1167-219.jpg?t=st=1726329382~exp=1726332982~hmac=2e78f27ff21ad1a7e197c98532a6faf10f387c08fea5726152e741a6376a57b1&w=1060"

PhotoDescription = dict[str, str]

DEFAULT_DESCRIPTION: PhotoDescription = {
    "name": "Darko Mulej",
    "links_html": MY_PHOTOS,
    "company": "Flickr",
}

WeatherEntry = dict[str, Any]
ForecastResult = list[WeatherEntry] | str

# Language name mapping for LLM prompts
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "de": "German",
    "it": "Italian",
    "ru": "Russian",
    "eo": "Esperanto",
    "sl": "Slovenian",
}


def _create_client(provider_config: dict[str, str | None]) -> Any:
    """Create an LLM client for the given provider config."""
    if provider_config["provider"] == "Anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=provider_config["api_key"])
    else:
        from openai import OpenAI
        kwargs: dict[str, str] = {"api_key": provider_config["api_key"]}
        if provider_config["base_url"]:
            kwargs["base_url"] = provider_config["base_url"]
        return OpenAI(**kwargs)


def initialize_extensions(app: Flask) -> None:
    """Initialize application extensions (LLM clients for all available providers)."""
    if not _AVAILABLE_PROVIDERS:
        logger.warning("No LLM API key set — itinerary generation will fail")
        app.llm_clients = []
        return

    app.llm_clients = []
    for config in _AVAILABLE_PROVIDERS:
        try:
            client = _create_client(config)
            app.llm_clients.append((client, config))
            logger.info(f"Initialized LLM provider: {config['provider']} (model: {config['model']})")
        except Exception as e:
            logger.error(f"Failed to initialize {config['provider']}: {e}")


def _call_provider(
    client: Any,
    config: dict[str, str | None],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call a single LLM provider."""
    if config["provider"] == "Anthropic":
        response = client.messages.create(
            model=config["model"],
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text
    else:
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content


def llm_complete(
    clients: list[tuple[Any, dict[str, str | None]]],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1900,
    temperature: float = 0.7,
) -> str:
    """Try LLM providers in priority order. Falls back to next on failure."""
    last_error: Exception | None = None

    for client, config in clients:
        try:
            logger.info(f"Trying {config['provider']} ({config['model']})...")
            result = _call_provider(client, config, system_prompt, user_prompt, max_tokens, temperature)
            logger.info(f"Success with {config['provider']}")
            return result
        except Exception as e:
            last_error = e
            logger.warning(f"{config['provider']} failed: {e} — trying next provider")

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


def _stream_provider(
    client: Any,
    config: dict[str, str | None],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
):
    """Stream text chunks from a single LLM provider."""
    if config["provider"] == "Anthropic":
        import anthropic
        with client.messages.stream(
            model=config["model"],
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    else:
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def llm_stream(
    clients: list[tuple[Any, dict[str, str | None]]],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1900,
    temperature: float = 0.7,
):
    """Stream LLM response. Tries providers in priority order. Yields text chunks."""
    last_error: Exception | None = None

    for client, config in clients:
        try:
            logger.info(f"Streaming from {config['provider']} ({config['model']})...")
            yielded = False
            for chunk in _stream_provider(client, config, system_prompt, user_prompt, max_tokens, temperature):
                yielded = True
                yield chunk
            if yielded:
                logger.info(f"Stream complete from {config['provider']}")
                return
        except Exception as e:
            last_error = e
            logger.warning(f"{config['provider']} stream failed: {e} — trying next provider")

    raise RuntimeError(f"All LLM providers failed to stream. Last error: {last_error}")


def get_language_name(code: str) -> str:
    """Get full language name from code."""
    return LANGUAGE_NAMES.get(code, "English")


# Manually added images for cities
my_images: dict[str, list[str]] = {
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


def get_image_url(city: str) -> tuple[str, PhotoDescription]:
    """Fetch a city image from personal collection, Unsplash, or fallback."""
    logger.info(f"Fetching image for {city}")

    if city in my_images:
        image_url: str = random.choice(my_images[city])
        return image_url, DEFAULT_DESCRIPTION

    if not UNSPLASH_ACCESS_KEY:
        logger.warning("UNSPLASH_ACCESS_KEY not set — using fallback image")
        return ERROR_JPG, DEFAULT_DESCRIPTION

    try:
        search_url: str = "https://api.unsplash.com/search/photos"
        params: dict[str, str | int] = {
            "query": city,
            "per_page": 1,
            "page": random.randint(1, 5),
            "client_id": UNSPLASH_ACCESS_KEY,
            "w": 1000,
            "h": 1000,
        }
        response = requests.get(search_url, params=params)
        logger.info(f"Unsplash API status: {response.status_code}")

        if response.status_code == 200:
            json_data: dict = response.json()
            if json_data['results']:
                data: dict = json_data['results'][0]
                image_url = data['urls']['regular']
                description: PhotoDescription = {
                    "name": data['user']['name'],
                    "links_html": data['user']['links']['html'],
                    "company": "Unsplash",
                }
                return image_url, description

        logger.warning(f"Unsplash returned no results for {city}")
        return ERROR_JPG, DEFAULT_DESCRIPTION

    except Exception as e:
        logger.error(f"Error fetching image for {city}: {e}")
        return ERROR_JPG, DEFAULT_DESCRIPTION


def get_weather_forecast_5d(city: str) -> ForecastResult:
    """Fetch 5-day weather forecast for a city (one entry per day at 15:00)."""
    if not OPENWEATHERMAP_API_KEY:
        logger.warning("OPENWEATHERMAP_API_KEY not set — skipping weather")
        return "Weather API key not configured"

    url: str = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data: dict = response.json()

        forecast_list: list[WeatherEntry] = []
        last_date: datetime | None = None

        for item in weather_data.get("list", []):
            dt_txt: str = item.get("dt_txt")
            dt: datetime = datetime.strptime(dt_txt, '%Y-%m-%d %H:%M:%S')

            if dt.hour == 15 and (last_date is None or last_date != dt.date()):
                weather_info: dict = item.get("weather", [])[0]
                temp_c: int = round(item.get("main", {}).get("temp"))
                forecast_entry: WeatherEntry = {
                    "date": dt.strftime("%d.%m"),
                    "temperature": temp_c,
                    "description": weather_info.get("description", ""),
                    "icon": weather_info.get("icon", ""),
                }
                forecast_list.append(forecast_entry)
                last_date = dt.date()

        return forecast_list

    except requests.RequestException as e:
        logger.error(f"Error fetching weather for {city}: {e}")
        return f"Error fetching weather data: {e}"
