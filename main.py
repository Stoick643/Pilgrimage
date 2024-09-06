import os
from openai import OpenAI
from flask import Flask, render_template, request

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
        model="gpt-3.5-turbo",  # Using GPT-3.5
        messages=[{
            "role": "system",
            "content": "You are a helpful travel assistant."
        }, {
            "role": "user",
            "content": prompt
        }],
        max_tokens=900,  # Adjust this based on the length of the output needed
        temperature=0.7)

    # Extract the generated itinerary from the response
    itinerary = response.choices[0].message

    # Display the itinerary
    return render_template('itinerary.html',
                           country=country,
                           duration=duration,
                           itinerary=itinerary)


if __name__ == '__main__':
    app.run(debug=True)
