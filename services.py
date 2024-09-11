import logging
import os

import requests
from openai import OpenAI
from pymongo import MongoClient

OAI_MODEL = "gpt-4o"
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def initialize_extensions(app):
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
            "client_id": UNSPLASH_ACCESS_KEY
        }
        response = requests.get(search_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                return data['results'][0]['urls']['regular']
    return "/static/images/default.jpg"  # Return a default image if no result found
