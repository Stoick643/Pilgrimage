import logging
import os
import time

from flask import current_app, render_template, request

from src.formatters import prepare_itinerary_data
from src.maps import extract_and_geocode_cities
from src.services import LLM_MODEL, translate_itinerary

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register all application routes."""

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/generate-itinerary', methods=['POST'])
    def generate_itinerary():
        country = request.form.get('country', '').strip()
        duration = request.form.get('duration', '').strip()
        activities = request.form.getlist('activities')
        language = request.form.get('language', 'en')

        # Input validation
        if not country:
            return render_template('index.html', error="Please enter a country or region."), 400
        if not duration or not duration.isdigit() or int(duration) < 1:
            return render_template('index.html', error="Please enter a valid duration (1+ days)."), 400

        client = current_app.oai_client
        logger.info(f"Generating itinerary: {country}, {duration} days, {activities}, {language}")

        prompt = f"""
        1. Generate a detailed {duration}-day day-by-day itinerary for visiting {country.title()}. The itinerary should include a mix of popular landmarks and {', '.join(activities) if activities else 'general sightseeing'}. The itinerary should balance exploration and relaxation each day.

        2. If the destination is clearly not a real place, return an error message beginning with Error. Accept reasonable variations of place names (e.g. misspellings, lowercase).

        3. Format each day's details using the special text `&&&` in a dedicated line before the header, as shown below. After special text add the main city (or geographic location) for that day, ensuring only one city is used. If no city is available, use an appropriate geographic location. Example if Paris is in that day's itinerary:
        &&& Paris
        ### Day X: [Title]
        """

        start = time.time()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1900,
            temperature=0.7,
        )
        elapsed = round(time.time() - start, 2)
        logger.info(f"Itinerary generation took {elapsed}s")

        text = response.choices[0].message.content

        # Check if GPT returned an error (invalid country)
        if text.strip().startswith("Error"):
            return render_template('index.html', error=text), 400

        # Translate if needed
        start_translate = time.time()
        text = translate_itinerary(client, text, language)
        logger.info(f"Translation took {round(time.time() - start_translate, 2)}s")

        # Extract cities and geocode for the map
        city_coordinates = extract_and_geocode_cities(text)

        # Prepare structured itinerary data for the template
        itinerary_data = prepare_itinerary_data(text)

        return render_template(
            'itinerary.html',
            itinerary_data=itinerary_data,
            locations=city_coordinates,
            google_directions_api_key=os.getenv('GOOGLE_DIRECTIONS_API_KEY'),
        )
