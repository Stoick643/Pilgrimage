import logging
import os
import random
from datetime import datetime, timedelta

import redis
import requests
from flask import current_app
from openai import OpenAI
from pymongo import MongoClient

OAI_MODEL = "gpt-4o"
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')
MY_PHOTOS = "https://flickriver.com/photos/belatrix/popular-interesting/"
ERROR_JPG = "https://img.freepik.com/free-vector/funny-error-404-background-design_1167-219.jpg?t=st=1726329382~exp=1726332982~hmac=2e78f27ff21ad1a7e197c98532a6faf10f387c08fea5726152e741a6376a57b1&w=1060"


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
    # REDIS_URL = f"redis://:{REDIS_PASSWORD}@redis-10812.c135.eu-central-1-1.ec2.redns.redis-cloud.com:10812"
    # app.redis_client = redis.StrictRedis.from_url(REDIS_URL)


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
    prompt = f"""
    Translate the whole following itinerary to {language} while leaving lines which start with '&&&' (3 ampersand characters) untraslated (but important, this lines must be included.\nExample for Italian language:\n
     &&& Florence
    ### Day 1: Wellcome to Florence
    ->
     &&& Florence
    ### Giorno 1: Benvenuti a Firenze
    {itinerary}
    """
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
                f"You are fluent in English and {language}. Translate from English to {language}."
            }, {
                "role": "user",
                "content": prompt
            }],
            max_tokens=2900,
            temperature=0.7)

        # Get the translated itinerary with HTML tags preserved
        translation = response.choices[0].message.content
        # print(f"translate_itinerary translated:\n {translation}")
        return translation

    except Exception as e:
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


# Function to fetch images dynamically from Unsplash
def get_image_url(city):
    print(f"get_image_url start for {city}")

    if city in my_images:
        image_url = random.choice(my_images[city])
        description = {
            "name": "Darko Mulej",
            "links_html": MY_PHOTOS,
            "company": "Flickr"
        }
        return image_url, description

    if UNSPLASH_ACCESS_KEY:
        try:
            search_url = "https://api.unsplash.com/search/photos"
            search_url += "?w=1000&h=1000"
            params = {
                "query": city,
                "per_page": 1,
                "page": random.randint(1, 5),
                "client_id": UNSPLASH_ACCESS_KEY,
            }
            response = requests.get(search_url, params=params)
            # print(f"get_image_url status code = {response.status_code}")
            if response.status_code == 200:
                json = response.json()
                # description = data['results'][0]['alternative_slugs']['en']
                # print(data['results'][0])
                if json['results']:
                    data = json['results'][0]
                    # url = data['results'][0]['urls']['regular']
                    image_url = data['urls']['regular']
                    #  user.links.html # = https://unsplash.com/@p1mm1
                    description = {
                        "name": data['user']['name'],
                        "links_html": data['user']['links']['html'],
                        "company": "Unsplash",
                    }
                    return image_url, description

        except Exception as e:
            print(f"Error fetching image for {city}: {e}")
            return ERROR_JPG, {
                "name": "Darko Mulej",
                "links_html": MY_PHOTOS
            }  # Return a default error image


def get_weather_forecast_5d(city):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status(
        )  # Raises HTTPError for bad responses (4xx and 5xx)
        weather_data = response.json()

        # List to hold the forecast dictionaries
        forecast_list = []

        last_date = None
        for item in weather_data.get("list", []):
            dt_txt = item.get("dt_txt")
            dt = datetime.strptime(dt_txt, '%Y-%m-%d %H:%M:%S')

            # Choose the forecast for 15:00 PM each day
            if dt.hour == 15 and (last_date is None or last_date != dt.date()):
                weather_info = item.get("weather", [])[0]
                temp_c = round(item.get("main", {}).get("temp"))
                forecast_entry = {
                    "date": dt.strftime("%d.%m"),  # Date formatted as dd.mm
                    "temperature": temp_c,
                    "description": weather_info.get("description", ""),
                    "icon": weather_info.get("icon", "")
                }
                forecast_list.append(forecast_entry)
                # Update last_date to ensure only one entry per day
                last_date = dt.date()

        return forecast_list

    except requests.RequestException as e:
        return f"Error fetching weather data: {e}"


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
                        'description': forecast['weather'][0]['description'],
                        'icon': forecast['weather'][0]['icon'],
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
