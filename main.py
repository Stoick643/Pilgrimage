import logging
import os
import time

from dotenv import load_dotenv
from flask import Flask, current_app, render_template, request

from maps import extract_and_geocode_cities
from services import (
    LLM_MODEL,
    LLM_PROVIDER,
    get_image_url,
    get_weather_forecast_5d,
    initialize_extensions,
    translate_itinerary,
)

load_dotenv()

logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder='static')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s]: %(message)s',
    )

    initialize_extensions(app)
    register_routes(app)

    return app


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
        1. Generate a detailed {duration}-day day-by-day itinerary for visiting [{country}]. The itinerary should include a mix of popular landmarks and {', '.join(activities) if activities else 'general sightseeing'}. The itinerary should balance exploration and relaxation each day.

        2. If the text inside square brackets `[]` does not represent a valid region, city, or country, return an error message beginning with Error and provide details about the issue.

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

        # Format itinerary with images and weather
        formatted = format_itinerary_weather(text)

        return render_template(
            'itinerary.html',
            itinerary=formatted,
            locations=city_coordinates,
            google_directions_api_key=os.getenv('GOOGLE_DIRECTIONS_API_KEY'),
        )


def extract_text_with_cities(text):
    """Parse itinerary text into list of (city, content) tuples based on '&&&' markers."""
    result = []
    lines = text.split('\n')
    current_block = []
    current_city = None

    for line in lines:
        line = line.strip()
        if line.startswith('&&&'):
            if current_block and current_city:
                result.append((current_city, '\n'.join(current_block)))
                current_block = []
            current_city = line[3:].strip()
        else:
            if current_city:
                current_block.append(line)

    if current_block and current_city:
        result.append((current_city, '\n'.join(current_block)))

    return result


def format_itinerary_weather(itinerary):
    """Format itinerary with city images and weather forecasts."""
    unsplash_url = "https://unsplash.com/?utm_source=your_app_name&utm_medium=referral"
    formatted = ""

    for city, day_plan in extract_text_with_cities(itinerary):
        lines = day_plan.strip().split('\n')
        title = f"<h3>{lines[0]}</h3>"
        plan = "<ul>" + "".join(f"<li>{line}</li>" for line in lines[1:] if line.strip()) + "</ul>"

        image_url, desc = get_image_url(city)
        user_name = desc['name']
        links_html = desc['links_html']
        company = desc['company']

        image_html = f"""
        <div class="city-image d-flex align-items-center">
            <img src="{image_url}" alt="{city}" class="img-fluid" loading="lazy">
            <p class="ms-3"> {city} </p>
            <p class="ms-3 fs-6 fst-italic"> (Photo by <a href="{links_html}">{user_name}</a> on <a href="{unsplash_url}">{company})</a></p>
        </div>
        """

        formatted += f"{image_html}{title}{plan}{weather_html(city)}<br><br>"

    return formatted


def weather_html(city):
    """Generate HTML for a city's 5-day weather forecast."""
    forecast = get_weather_forecast_5d(city)

    if isinstance(forecast, str):
        return ""

    html = "<div class='weather-container d-flex justify-content-between'>"
    for day in forecast:
        icon_url = f"https://openweathermap.org/img/wn/{day['icon']}.png"
        html += f"""
        <div class="weather-icon">
            <img src="{icon_url}" class="img-fluid" loading="lazy">
            <p>{day['temperature']} °C ({day['date']})</p>
        </div>
        """
    html += "</div>"
    return html


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
