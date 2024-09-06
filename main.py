import os

from flask import Flask, render_template, request
from openai import OpenAI

from maps import extract_and_geocode_cities  # Import from maps.py
import re

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
    prompt = f"Create a {duration}-day itinerary for visiting {country}. Include activities such as {', '.join(activities)}."

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


def format_itinerary(itinerary):
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
    app.run(debug=True)
