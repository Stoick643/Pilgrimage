import logging
import os
import random
from datetime import datetime, timedelta

import requests
from openai import OpenAI
from pymongo import MongoClient

OAI_MODEL = "gpt-4o"
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def initialize_extensions_etc(app):
    # Initialize MongoDB
    app.mongo_client = MongoClient(MONGO_URI)
    app.db = app.mongo_client['itinerary_db']
    app.itinerary_collection = app.db['itineraries']

    # Test MongoDB connection before using it in the app
    try:
        print(app.mongo_client.server_info())
        logging.info("Successfully connected to MongoDB")
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {e}")
    # Initialize OpenAI client

    app.oai_client = OpenAI(api_key=OPENAI_API_KEY)


def initialize_extensions(app):
    app.oai_client = OpenAI(api_key=OPENAI_API_KEY)


def call_openai_api(client, prompt: str, model: str = OAI_MODEL) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "system",
            "content": "You are a helpful travel assistant."
        }, {
            "role": "user",
            "content": prompt
        }],
        max_tokens=900,
        temperature=0.3)

    return response.choices[0].message.content


def translate_itinerary(client, itinerary, language):
    prompt = f"Translate the following itinerary to {language} while keeping the HTML tags intact. Only translate the text outside the HTML tags: {itinerary}"
    print(f"translate_itinerary start for {prompt}")

    if (language == "en"):
        return itinerary

    try:
        response = client.chat.completions.create(
            model=OAI_MODEL,
            messages=[{
                "role":
                "system",
                "content":
                f"Translate to {language} and preserve HTML tags (if there are any)."
            }, {
                "role": "user",
                "content": prompt
            }],
            max_tokens=900,
            temperature=0.7)

        # Get the translated itinerary with HTML tags preserved
        translation = response.choices[0].message.content
        print(f"translate_itinerary translated:\n {translation}")
        return translation

    except Exception as e:
        return f"Error translating itinerary: {str(e)}"


# Manually added images for cities
city_images = {"Rome": "/static/images/rome.jpg"}


# Function to fetch images dynamically from Unsplash
def get_image_url(query):
    print(f"get_image_url start for {query}")
    # Check if the city has a manually added image first
    if query in city_images:
        return city_images[query]

    # If not, try fetching from Unsplash
    if UNSPLASH_ACCESS_KEY:
        search_url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "per_page": 1,
            "page": random.randint(1, 10),
            "client_id": UNSPLASH_ACCESS_KEY,
        }
        response = requests.get(search_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                return data['results'][0]['urls']['regular']
    return "/static/images/default.jpg"  # Return a default image if no result found


OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')


def get_weather_forecast(city, date):
    """
    Fetches the weather forecast for the given city and date, selecting the forecast with the highest temperature.

    :param city: City name (e.g., 'Paris')
    :param date: Date in 'YYYY-MM-DD' format
    :return: Weather forecast with the highest temperature for the city on the specified date.
    """
    print(f"get_weather_forecast start for {city} and {date}")
    # Convert the date string to a datetime object
    target_date = datetime.strptime(date, '%Y-%m-%d')

    # Check if the requested date is within the next 5 days
    today = datetime.now()
    if target_date > today + timedelta(days=5):
        return "Date is beyond the 5-day forecast range."

    # OpenWeatherMap API URL
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        forecast_list = data['list']

        # Find the forecast with the highest temperature for the specified date
        highest_temp_forecast = None
        max_temperature = float('-inf')

        for forecast in forecast_list:
            forecast_time = datetime.fromtimestamp(forecast['dt'])
            if forecast_time.date() == target_date.date():
                temperature = forecast['main']['temp']
                if temperature > max_temperature:
                    max_temperature = temperature
                    highest_temp_forecast = {
                        'time': forecast_time.strftime('%H:%M'),
                        'temperature': round(temperature),  # Rounding
                        'description': forecast['weather'][0]['description']
                    }

        if highest_temp_forecast:
            return highest_temp_forecast
        else:
            return "No weather data available for the specified date."

    else:
        return f"Error fetching data: {response.status_code}"


# Function to get weather forecast data for a specified city
def get_weather_forecast_data(city):
    """
    Fetch 5-day forecast data for a given city using OpenWeatherMap API
    """
    forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {'q': city, 'appid': OPENWEATHERMAP_API_KEY, 'units': 'metric'}
    try:
        response = requests.get(forecast_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching forecast data: {e}")
        return None
