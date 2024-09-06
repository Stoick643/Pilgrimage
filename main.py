import os
from openai import OpenAI
from flask import Flask, render_template, request
import re

app = Flask(__name__)

# Load the OpenAI API key from the environment variables
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
    raw_itinerary = response.choices[0].message.content

    # Check if the language is not English, then request a translation
    if language and language != 'en':  # If the user selected a non-English language
        raw_itinerary = translate_itinerary(raw_itinerary, language)

    # Format the itinerary by detecting day ranges and cleaning up text
    formatted_itinerary = format_itinerary(raw_itinerary)

    # Pass the formatted itinerary to the template
    return render_template('itinerary.html',
                           country=country,
                           duration=duration,
                           itinerary=formatted_itinerary)


# Custom function to format the itinerary by day ranges
def format_itinerary(itinerary):
    # Split by either "Day X-Y:" or "Day X:" using regex
    days = re.split(r'(Day \d+(?:-\d+)?:)', itinerary)

    formatted_days = []
    current_day = None

    for day in days:
        if re.match(r'Day \d+(?:-\d+)?:', day):
            current_day = day.strip()  # This is the day marker
        elif current_day:
            # Append the day marker and its associated activities
            formatted_days.append(f"{current_day} {day.strip()}")
            current_day = None  # Reset for the next iteration

    return formatted_days


def translate_itinerary(itinerary, target_language):
    # Prompt OpenAI to translate the itinerary while preserving HTML tags
    prompt = f"Translate the following itinerary to {target_language} while keeping the HTML tags intact. Only translate the text within the tags: {itinerary}"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role":
                "system",
                "content":
                f"Translate to {target_language} and preserve HTML tags."
            }, {
                "role": "user",
                "content": prompt
            }],
            max_tokens=500,
            temperature=0.7)

        # Get the translated itinerary with HTML tags preserved
        translated_itinerary = response.choices[0].message.content
        return translated_itinerary

    except Exception as e:
        return f"Error translating itinerary: {str(e)}"


if __name__ == '__main__':
    app.run(debug=True)
