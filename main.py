import logging
import os
from datetime import datetime, timedelta

from flask import Flask, current_app, render_template, request

from maps import (
    extract_and_geocode_cities,  # Import from maps.py
)
from services import (
    get_image_url,
    get_weather_forecast,
    get_weather_forecast_5d,
    initialize_extensions,
)


def configure_app(app):
    """Configure the Flask application."""
    app.static_folder = 'templates'
    # app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    # Add additional configuration settings here if needed


def setup_logging(app):
    """Setup logging for the application."""
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s:%(message)s')


def create_app():
    print("creat_app 0")
    app = Flask(__name__)
    print("creat_app 1")
    configure_app(app)
    print("creat_app 2")
    setup_logging(app)
    print("creat_app 3")
    initialize_extensions(app)
    print("creat_app 4")
    #register_itinerary_routes(app)
    print("creat_app 5")

    return app


app = create_app()

# app = Flask(__name__)

if __name__ == '__main__':
    app.run(debug=True)
    # app.run(host='0.0.0.0', port=8080, debug=True)  # Change the port to 8080


@app.route('/')
def index():
    print("Index route hit")
    return render_template('index.html')


@app.route('/generate-itinerary', methods=['POST'])
def generate_itinerary():
    print("Received request on /generate-itinerary")
    country = request.form['country']
    duration = request.form['duration']
    activities = request.form.getlist('activities')
    language = request.form['language']
    client = current_app.oai_client
    print(
        f"generate_itinerary start for {country} {duration} {activities} {language}"
    )

    prompt = f"""
    1. Generate a detailed {duration}-day day-by-day itinerary for visiting [{country}]. The     itinerary should include a mix of popular landmarks and {', '.join(activities)}. The itinerary should balance exploration and relaxation each day.

    2. If the text inside square brackets `[]` does not represent a valid region, city, or country, return an error message beginning with Error and provide details about the issue.

    3. Format each day's details using the special text `&&&` in a dedicated line before the header, as shown below. After special text add the main city (or geographic location) for that day, ensuring only one city is used. If no city is available, use an appropriate geographic location. Example if Paris is in that day's itinerary:
    &&& Paris   
    ### Day X: [Title]
    """

    if (language != "en"):
        prompt += f"\n4. Translate the itinerary to language '{language}' (ISO 639-1 language code). But leave cities in lines with special text `&&&` untranslated.  Return only translated text."

    # Call the OpenAI API to generate the itinerary
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "system",
            "content": "You are a helpful travel assistant."
        }, {
            "role": "user",
            "content": prompt
        }],
        max_tokens=900,
        temperature=0.7)

    # Access the content of the response
    text = response.choices[0].message.content
    # print(f"raw_text:\n {text}" + "\n")
    city_coordinates = extract_and_geocode_cities(text)
    # text = translate_itinerary(client, raw_text, language)
    text = format_itinerary_weather(text)

    # Pass the formatted itinerary and city coordinates to the template
    return render_template(
        'itinerary.html',
        itinerary=text,
        locations=city_coordinates,
        google_directions_api_key=os.getenv('GOOGLE_DIRECTIONS_API_KEY'))


def extract_special_lines(text):
    result = set()  # To store unique entries
    lines = text.split('\n')  # Split the input text into lines

    for line in lines:
        line = line.strip()  # Remove leading/trailing spaces
        if line.startswith('&&&'):  # Check if line starts with "&&&"
            entry = line[3:].strip(
            )  # Extract the part after "&&&" and remove extra spaces
            result.add(entry)  # Add it to the set

    return result


def extract_special_lines_as_map(text):
    result = {}  # To store sequential entries
    lines = text.split('\n')  # Split the input text into lines
    counter = 1  # Start numbering from 1

    for line in lines:
        line = line.strip()  # Remove leading/trailing spaces
        if line.startswith('&&&'):  # Check if line starts with "&&&"
            entry = line[3:].strip(
            )  # Extract the part after "&&&" and remove extra spaces
            result[
                counter] = entry  # Store in the dictionary with a sequential number
            counter += 1  # Increment counter for the next city

    return result


def extract_text_with_cities(text):
    # return list of tuples as
    # [  ("Florence", "Text block for Florence"),  ("Siena", "Text block for Siena"),  ...]
    result = []  # To store tuples of (city, content)
    lines = text.split('\n')  # Split the input text into lines
    current_block = []  # Temporary list to collect lines between "&&&" markers
    current_city = None  # Variable to store the current city name

    for line in lines:
        line = line.strip()  # Remove leading/trailing spaces
        if line.startswith('&&&'):
            if current_block and current_city:
                result.append(
                    (current_city,
                     '\n'.join(current_block)))  # Add city and block to result
                current_block = []  # Reset the block for next section
            current_city = line[3:].strip()  # Update city name
        else:
            if current_city:
                current_block.append(
                    line)  # Collect lines for the current city

    if current_block and current_city:
        result.append((current_city,
                       '\n'.join(current_block)))  # Add the last block if any

    return result


def format_itinerary(itinerary):
    formatted = ""
    for city, day_plan in extract_text_with_cities(itinerary):
        lines = day_plan.strip().split('\n')
        title = f"<h3>{lines[0]}</h3>"
        plan = "<ul>" + "".join([f"<li>{line}</li>"
                                 for line in lines[1:]]) + "</ul>"

        image_url, description = get_image_url(city)
        # Include the image HTML
        image_html = f'''
        <div class="city-image d-flex align-items-center">
            <img src="{image_url}" alt="{city}" class="img-fluid" loading="lazy">
            <h5 class="ms-3">{description}</h5> 
        </div>
        '''
        # Combine the image, day heading, and activities
        formatted += f"{image_html}{title}{plan}<br><br>"
    return formatted


def format_itinerary_weather(itinerary):
    formatted = ""
    for city, day_plan in extract_text_with_cities(itinerary):
        lines = day_plan.strip().split('\n')
        title = f"<h3>{lines[0]}</h3>"
        plan = "<ul>" + "".join([f"<li>{line}</li>"
                                 for line in lines[1:]]) + "</ul>"
        # Fetch the image URL
        image_url, description = get_image_url(city)
        # "position-absolute bottom-0 end-0 mb-2 me-2 bg-white p-1"
        image_html = f'''
        <div class="city-image d-flex align-items-center">
            <img src="{image_url}" alt="{city}" class="img-fluid" loading="lazy">
            <p class="ms-3">{city}</p> 
        </div>
        '''
        # Combine the image, day heading, activities, and weather
        formatted += f"{image_html}{title}{plan}{weather_html(city)}<br><br>"

    return formatted


def weather_html(city):
    forecast = get_weather_forecast_5d(city)
    # print(f"forecast for {city} is {forecast}")
    if (isinstance(forecast, str)):
        # Print error or messagge
        return ""

    weather_html = "<div class='weather-container d-flex justify-content-between'>"
    for day in forecast:
        icon_url = f"https://openweathermap.org/img/wn/{day['icon']}.png"
        weather_html += f"""
        <div class="weather-icon">
            <img src="{icon_url}" class="img-fluid" loading="lazy">
            <p>{day['temperature']} °C ({day['date']})</p>
        </div>
        """
    weather_html += "</div>"
    return weather_html


def format_itinerary_weather_V1(itinerary):
    formatted = ""
    today = datetime.now()
    cnt = 0

    for city, day_plan in extract_text_with_cities(itinerary):
        lines = day_plan.strip().split('\n')
        title = f"<h3>{lines[0]}</h3>"
        plan = "<ul>" + "".join([f"<li>{line}</li>"
                                 for line in lines[1:]]) + "</ul>"
        # Fetch the image URL
        image_url = get_image_url(city)

        # Fetch the weather data
        target_date = today + timedelta(days=cnt)
        cnt += 1
        date = target_date.strftime('%Y-%m-%d')
        if (cnt > 5):
            weather_html = ""  # default
        else:
            forecast = get_weather_forecast(city, date)
            # print(f"forecast for {city} and {date} is {forecast}")
            if (isinstance(forecast, str) or cnt > 5):
                weather_html = f"<p>{forecast}</p>"  # Print error or message
            else:
                icon = forecast['icon']
                icon_url = f"https://openweathermap.org/img/wn/{icon}@2x.png"
                weather_html = f"""
                <div class="weather-icon">
                    <img src="{icon_url}" class="img-fluid" loading="lazy">
                    <p>{forecast['temperature']}°C ({date})</p>
                </div>
                """

        image_html = f'''
        <div class="city-image">
            <img src="{image_url}" alt="{city}" class="img-fluid" loading="lazy">
        </div>
        '''
        # Combine the image, day heading, activities, and weather
        formatted += f"{image_html}{title}{plan}{weather_html}<br><br>"

    return formatted


def save_itinerary(itinerary_data):
    result = current_app.itinerary_collection.insert_one(itinerary_data)
    return result.inserted_id
