import logging
import os
import random
from datetime import datetime, timedelta

import requests
from openai import OpenAI

logger = logging.getLogger(__name__)

UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')

# LLM configuration — supports OpenAI, DeepSeek, Moonshot (all OpenAI-compatible)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
MOONSHOT_API_KEY = os.getenv('MOONSHOT_API_KEY')

# Pick the first available provider
if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != 'your_deepseek_api_key_here':
    LLM_API_KEY = DEEPSEEK_API_KEY
    LLM_BASE_URL = "https://api.deepseek.com"
    LLM_MODEL = "deepseek-chat"
    LLM_PROVIDER = "DeepSeek"
elif MOONSHOT_API_KEY and MOONSHOT_API_KEY != 'your_moonshot_api_key_here':
    LLM_API_KEY = MOONSHOT_API_KEY
    LLM_BASE_URL = "https://api.moonshot.cn/v1"
    LLM_MODEL = "moonshot-v1-8k"
    LLM_PROVIDER = "Moonshot"
elif OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_api_key_here':
    LLM_API_KEY = OPENAI_API_KEY
    LLM_BASE_URL = None  # default OpenAI URL
    LLM_MODEL = "gpt-4o"
    LLM_PROVIDER = "OpenAI"
else:
    LLM_API_KEY = None
    LLM_BASE_URL = None
    LLM_MODEL = None
    LLM_PROVIDER = None
MY_PHOTOS = "https://flickriver.com/photos/belatrix/popular-interesting/"
ERROR_JPG = "https://img.freepik.com/free-vector/funny-error-404-background-design_1167-219.jpg?t=st=1726329382~exp=1726332982~hmac=2e78f27ff21ad1a7e197c98532a6faf10f387c08fea5726152e741a6376a57b1&w=1060"

DEFAULT_DESCRIPTION = {
    "name": "Darko Mulej",
    "links_html": MY_PHOTOS,
    "company": "Flickr",
}


def initialize_extensions(app):
    """Initialize application extensions (LLM client)."""
    if not LLM_API_KEY:
        logger.warning("No LLM API key set — itinerary generation will fail")
        app.oai_client = None
    else:
        kwargs = {"api_key": LLM_API_KEY}
        if LLM_BASE_URL:
            kwargs["base_url"] = LLM_BASE_URL
        app.oai_client = OpenAI(**kwargs)
        logger.info(f"Using LLM provider: {LLM_PROVIDER} (model: {LLM_MODEL})")


def call_openai_api(client, prompt: str, model: str = None) -> str:
    """Call LLM API with a travel assistant prompt."""
    response = client.chat.completions.create(
        model=model or LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful travel assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=900,
        temperature=0.3,
    )
    return response.choices[0].message.content


def translate_itinerary(client, itinerary, language):
    """Translate itinerary to the specified language. Returns as-is for English."""
    if language == "en":
        return itinerary

    prompt = f"""
    Translate the whole following itinerary to {language} while leaving lines which start with '&&&' (3 ampersand characters) untranslated (but important, these lines must be included).
    Example for Italian language:
     &&& Florence
    ### Day 1: Welcome to Florence
    ->
     &&& Florence
    ### Giorno 1: Benvenuti a Firenze
    {itinerary}
    """
    logger.info(f"Translating itinerary to {language}")

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"You are fluent in English and {language}. Translate from English to {language}.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2900,
            temperature=0.7,
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error translating itinerary: {e}")
        return f"Error translating itinerary: {str(e)}"


# Manually added images for cities
my_images = {
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


def get_image_url(city):
    """Fetch a city image from personal collection, Unsplash, or fallback."""
    logger.info(f"Fetching image for {city}")

    if city in my_images:
        image_url = random.choice(my_images[city])
        return image_url, DEFAULT_DESCRIPTION

    if not UNSPLASH_ACCESS_KEY:
        logger.warning("UNSPLASH_ACCESS_KEY not set — using fallback image")
        return ERROR_JPG, DEFAULT_DESCRIPTION

    try:
        search_url = "https://api.unsplash.com/search/photos"
        params = {
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
            json_data = response.json()
            if json_data['results']:
                data = json_data['results'][0]
                image_url = data['urls']['regular']
                description = {
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


def get_weather_forecast_5d(city):
    """Fetch 5-day weather forecast for a city (one entry per day at 15:00)."""
    if not OPENWEATHERMAP_API_KEY:
        logger.warning("OPENWEATHERMAP_API_KEY not set — skipping weather")
        return "Weather API key not configured"

    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()

        forecast_list = []
        last_date = None

        for item in weather_data.get("list", []):
            dt_txt = item.get("dt_txt")
            dt = datetime.strptime(dt_txt, '%Y-%m-%d %H:%M:%S')

            if dt.hour == 15 and (last_date is None or last_date != dt.date()):
                weather_info = item.get("weather", [])[0]
                temp_c = round(item.get("main", {}).get("temp"))
                forecast_entry = {
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
