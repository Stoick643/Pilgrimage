import logging
import os
import time

from flask import Flask, current_app, render_template, request

from src.formatters import prepare_itinerary_data
from src.maps import extract_and_geocode_cities
from src.services import LLM_PROVIDER, get_language_name, llm_complete

logger = logging.getLogger(__name__)


def register_routes(app: Flask) -> None:
    """Register all application routes."""

    @app.route('/')
    def index() -> str:
        return render_template('index.html')

    @app.route('/generate-itinerary', methods=['POST'])
    def generate_itinerary() -> str | tuple[str, int]:
        country: str = request.form.get('country', '').strip()
        duration: str = request.form.get('duration', '').strip()
        activities: list[str] = request.form.getlist('activities')
        language: str = request.form.get('language', 'en')

        # Input validation
        if not country:
            return render_template('index.html', error="Please enter a country or region."), 400
        if not duration or not duration.isdigit() or int(duration) < 1:
            return render_template('index.html', error="Please enter a valid duration (1+ days)."), 400

        clients = current_app.llm_clients
        if not clients:
            return render_template('index.html', error="No LLM API key configured."), 500

        language_name: str = get_language_name(language)
        logger.info(f"Generating itinerary: {country}, {duration} days, {activities}, {language_name}, provider={LLM_PROVIDER}")

        # Build prompt — generate directly in target language (no separate translation step)
        language_instruction: str = ""
        if language != "en":
            language_instruction = f"\n        4. Write the ENTIRE itinerary in {language_name}. All day titles, descriptions, and details must be in {language_name}. Only the '&&&' city name lines must remain in English (the original city name)."

        prompt: str = f"""
        1. Generate a detailed {duration}-day day-by-day itinerary for visiting {country.title()}. The itinerary should include a mix of popular landmarks and {', '.join(activities) if activities else 'general sightseeing'}. The itinerary should balance exploration and relaxation each day.

        2. If the destination is clearly not a real place, return an error message beginning with Error. Accept reasonable variations of place names (e.g. misspellings, lowercase).

        3. Format each day's details using the special text `&&&` in a dedicated line before the header, as shown below. After special text add the main city (or geographic location) for that day, ensuring only one city is used. If no city is available, use an appropriate geographic location. Example if Paris is in that day's itinerary:
        &&& Paris
        ### Day X: [Title]
        {language_instruction}"""

        start: float = time.time()

        try:
            text: str = llm_complete(
                clients=clients,
                system_prompt="You are a helpful travel assistant.",
                user_prompt=prompt,
                max_tokens=1900,
                temperature=0.7,
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return render_template('index.html', error=f"Failed to generate itinerary: {str(e)}"), 500

        elapsed: float = round(time.time() - start, 2)
        logger.info(f"Itinerary generation took {elapsed}s")

        # Check if LLM returned an error (invalid country)
        if text.strip().startswith("Error"):
            return render_template('index.html', error=text), 400

        # Extract cities and geocode for the map
        city_coordinates: list[dict[str, str | float]] = extract_and_geocode_cities(text)

        # Prepare structured itinerary data for the template
        itinerary_data: dict = prepare_itinerary_data(text)

        return render_template(
            'itinerary.html',
            itinerary_data=itinerary_data,
            locations=city_coordinates,
            google_directions_api_key=os.getenv('GOOGLE_DIRECTIONS_API_KEY'),
        )
