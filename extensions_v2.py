import logging
import os

from openai import OpenAI
from pymongo import MongoClient

OAI_MODEL = "gpt-4o-mini"
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def initialize_extensions(app):
    """Initialize Flask extensions and external services like MongoDB and OpenAI."""

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
    app.openai_client = OpenAI(api_key=OPENAI_API_KEY)
