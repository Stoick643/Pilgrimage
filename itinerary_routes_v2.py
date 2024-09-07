import logging
import os

from flask import current_app, jsonify, render_template, request

from services import (
    call_openai_api,
    create_prompt,
    extract_and_geocode_cities,
    format_itinerary,
)


def index():
    """Root route for testing purposes."""
    itinerary_collection = current_app.itinerary_collection
    # For test only
    itineraries = itinerary_collection.find({"user_id": "user123"})
    for itin in itineraries:
        print(itin)
    return render_template('index.html')


def generate_itinerary():
    """Generate an itinerary based on user input."""
    print("generate_itinerary start!!")
    try:
        country = request.form['country']
        duration = request.form['duration']
        activities = request.form.getlist('activities')
        language = request.form['language']

        prompt = create_prompt(country, duration, activities)
        raw_it = call_openai_api(current_app.openai_client, prompt)
        city_coordinates = extract_and_geocode_cities(raw_it)
        formatted_it = format_itinerary(raw_it)

        if language and language != 'en':
            translation_prompt = f"Translate the following itinerary to {language}: {formatted_it}"
            formatted_it = call_openai_api(current_app.openai_client,
                                           translation_prompt)

        return render_template(
            'itinerary.html',
            itinerary=formatted_it,
            locations=city_coordinates,
            google_directions_api_key=os.getenv('GOOGLE_DIRECTIONS_API_KEY'))

    except Exception as e:
        logging.error(f"Error in generate_itinerary: {e}")
        return jsonify({'error': str(e)}), 500


def register_itinerary_routes(app):
    """Register itinerary routes with the Flask application."""
    print("register_itinerary_routes start!!")
    app.add_url_rule('/generate-itinerary',
                     'generate_itinerary',
                     generate_itinerary,
                     methods=['POST'])
    app.add_url_rule('/', 'index', index)
