import logging
import os
import time

from flask import Flask, current_app, jsonify, render_template, request

from src.formatters import extract_text_with_cities
from src.maps import extract_cities, geocode_cities
from src.prompts import (
    ACTIVE_PROMPT,
    PROMPT_CONCISE,
    PROMPT_DETAILED,
    SYSTEM_CONCISE,
    SYSTEM_DETAILED,
)
from src.services import (
    LLM_PROVIDER,
    get_image_url,
    get_language_name,
    get_weather_forecast_5d,
    llm_complete,
    UNSPLASH_URL,
)

logger = logging.getLogger(__name__)

import re

def _clean_markdown(text: str) -> str:
    """Convert basic Markdown to clean text/HTML."""
    text = text.strip()
    # Remove heading markers
    text = re.sub(r'^#{1,4}\s*', '', text)
    # Remove list markers (- , * , numbered)
    text = re.sub(r'^[-*]\s+', '', text)
    text = re.sub(r'^\d+\.\s+', '', text)
    # Convert **bold** to <strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Convert *italic* to <em>
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


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
            language_instruction = f"\nWrite in {language_name}. Keep '&&&' city names in English only."

        activities_text: str = ', '.join(activities) if activities else 'general sightseeing'

        if ACTIVE_PROMPT == "concise":
            prompt_template = PROMPT_CONCISE
            system_prompt = SYSTEM_CONCISE
            max_tokens: int = min(300 * int(duration), 2500)
        else:
            prompt_template = PROMPT_DETAILED
            system_prompt = SYSTEM_DETAILED
            max_tokens = 1900

        prompt: str = prompt_template.format(
            duration=duration,
            country=country.title(),
            activities=activities_text,
            language_instruction=language_instruction,
        )

        start: float = time.time()

        try:
            text: str = llm_complete(
                clients=clients,
                system_prompt=system_prompt,
                user_prompt=prompt,
                max_tokens=max_tokens,
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

        # Parse text into days — fast, no API calls
        day_entries: list = extract_text_with_cities(text)
        days: list = []
        for city, day_plan in day_entries:
            lines = day_plan.strip().split('\n')
            title = _clean_markdown(lines[0]) if lines else ""
            activities_list = [_clean_markdown(line) for line in lines[1:] if line.strip()]
            days.append({
                'city': city,
                'title': title,
                'activities': activities_list,
            })

        cities: list[str] = [d['city'] for d in days]

        return render_template(
            'itinerary.html',
            days=days,
            cities=cities,
            google_directions_api_key=os.getenv('GOOGLE_DIRECTIONS_API_KEY'),
            unsplash_url=UNSPLASH_URL,
        )

    # --- AJAX API endpoints (called after page loads) ---

    @app.route('/api/city-image')
    def api_city_image():
        """Fetch image for a city. Returns JSON."""
        city: str = request.args.get('city', '').strip()
        if not city:
            return jsonify({"error": "city parameter required"}), 400

        image_url, desc = get_image_url(city)
        return jsonify({
            "image_url": image_url,
            "photo_credit": {
                "name": desc["name"],
                "link": desc["links_html"],
                "company": desc["company"],
            },
        })

    @app.route('/api/city-weather')
    def api_city_weather():
        """Fetch 5-day weather for a city. Returns JSON."""
        city: str = request.args.get('city', '').strip()
        if not city:
            return jsonify({"error": "city parameter required"}), 400

        forecast = get_weather_forecast_5d(city)
        if isinstance(forecast, str):
            return jsonify({"forecast": [], "error": forecast})

        for entry in forecast:
            entry['icon_url'] = f"https://openweathermap.org/img/wn/{entry['icon']}.png"

        return jsonify({"forecast": forecast})

    @app.route('/api/geocode')
    def api_geocode():
        """Geocode a list of cities. Returns JSON."""
        cities_param: str = request.args.get('cities', '').strip()
        if not cities_param:
            return jsonify({"error": "cities parameter required"}), 400

        cities: list[str] = [c.strip() for c in cities_param.split(',') if c.strip()]
        locations = geocode_cities(cities)
        return jsonify({"locations": locations})
