import os
import re

from flask import Flask, render_template, request
from openai import OpenAI

from image_fetcher import get_image_url  # Import from image_fetcher.py
from maps import (
    extract_and_geocode_cities,  # Import from maps.py
    extract_cities_gpt,
)

app = Flask(__name__)

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate-itinerary', methods=['POST'])
def generate_itinerary():
    country = request.form['country']
    duration = request.form['duration']
    activities = request.form.getlist('activities')
    language = request.form['language']

    # Create a prompt for the OpenAI API to generate an itinerary
    prompt = f"""
    Create a detailed {duration}-day itinerary for visiting {country}.
    The itinerary should include activities such as {', '.join(activities)}.
    Please suggest popular landmarks, hidden gems, cultural experiences, and outdoor activities.
    Balance each day with time for relaxation and exploration.
    Make sure the itinerary is well-suited for someone interested in {', '.join(activities)}.
    """

    # Call the OpenAI API to generate the itinerary
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "system",
            "content": "You are a helpful travel assistant."
        }, {
            "role": "user",
            "content": prompt
        }],
        max_tokens=900,
        temperature=0.7)

    # Extract the generated itinerary from the response
    raw_it = response.choices[0].message.content
    formatted_it = format_itinerary(raw_it)

    # Translate the itinerary if needed
    if language and language != 'en':
        formatted_it = translate_itinerary(formatted_it, language)

    # Extract and geocode the cities from the itinerary
    city_coordinates = extract_and_geocode_cities(formatted_it)

    # Pass the formatted itinerary and city coordinates to the template
    return render_template(
        'itinerary.html',
        itinerary=formatted_it,
        locations=city_coordinates,
        google_directions_api_key=os.getenv('GOOGLE_DIRECTIONS_API_KEY'))


def format_itinerary_V1(itinerary):
    # Split by either "Day X-Y:" or "Day X:" using regex
    days = re.split(r'(Day \d+(?:-\d+)?:)', itinerary)

    formatted_itinerary = ""
    current_day = None

    for day in days:
        if re.match(r'Day \d+(?:-\d+)?:', day):
            current_day = f"<h3>{day.strip()}</h3>"  # Wrap day in an h3 tag for better readability
        elif current_day:
            # Create an unordered list of activities
            activities = day.strip().split(' - ')  # Split activities by " - "
            activity_list = "<ul>" + "".join(
                [f"<li>{activity}</li>" for activity in activities]) + "</ul>"

            # Append the day heading and activity list to the formatted itinerary
            formatted_itinerary += f"{current_day} {activity_list}"
            current_day = None  # Reset for the next iteration

    return formatted_itinerary


def format_itinerary(itinerary):
    days = re.split(r'(Day \d+(?:-\d+)?:)', itinerary)
    formatted_itinerary = ""
    current_day = None

    # Extract city names from the entire itinerary using GPT
    extracted_cities = extract_cities_gpt(itinerary)

    # Counter to match cities to each day
    city_counter = 0

    for day in days:
        if re.match(r'Day \d+(?:-\d+)?:', day):
            current_day = f"<h3>{day.strip()}</h3>"
        elif current_day:
            # Use the GPT-extracted city for the current day
            if city_counter < len(extracted_cities):
                city_name = extracted_cities[city_counter]
                city_counter += 1
            else:
                city_name = "Unknown Location"

            # Fetch the image URL for the city
            image_url = get_image_url(city_name)

            # Include the image HTML
            image_html = f'''
            <div class="city-image">
                <img src="{image_url}" alt="{city_name}" class="img-fluid" loading="lazy">
            </div>
            '''

            # Create an unordered list of activities
            activities = day.strip().split(' - ')
            activity_list = "<ul>" + "".join(
                [f"<li>{activity}</li>" for activity in activities]) + "</ul>"

            # Combine the image, day heading, and activities
            formatted_itinerary += f"{image_html}{current_day}{activity_list}<br><br>"
            current_day = None

    return formatted_itinerary


# Translate itinerary if necessary
def translate_itinerary(itinerary, target_language):
    prompt = f"Translate the following itinerary to {target_language}: {itinerary}"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": f"Translate to {target_language}."
            }, {
                "role": "user",
                "content": prompt
            }],
            max_tokens=500,
            temperature=0.7)

        translated_itinerary = response.choices[0].message.content
        return translated_itinerary

    except Exception as e:
        print(f"Error during translation: {str(e)}")
        return itinerary


if __name__ == '__main__':
    app.run(debug=False)
