import re

from openai import OpenAI

from image_fetcher import get_image_url

OAI_MODEL = "gpt-4o-mini"


def create_prompt(country: str, duration: str, activities: list) -> str:
    return f"""
    Create a detailed {duration}-day itinerary for visiting {country}.
    The itinerary should include activities such as {', '.join(activities)}.
    Please suggest popular landmarks, hidden gems, cultural experiences, and outdoor activities.
    Balance each day with time for relaxation and exploration.
    Make sure the itinerary is well-suited for someone interested in {', '.join(activities)}.
    """


def call_openai_api(client, prompt: str, model: str = OAI_MODEL) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "system",
            "content": "You are a helpful travel assistant."
        }, {
            "role": "user",
            "content": prompt
        }],
        max_tokens=900,
        temperature=0.7)

    return response.choices[0].message.content


def __format_itinerary(itinerary: str) -> str:
    days = re.split(r'(Day \d+(?:-\d+)?:)', itinerary)
    formatted_itinerary = ""
    current_day = None

    for day in days:
        if re.match(r'Day \d+(?:-\d+)?:', day):
            current_day = f"<h3>{day.strip()}</h3>"
        elif current_day:
            activities = day.strip().split(' - ')
            activity_list = "<ul>" + "".join(
                [f"<li>{activity}</li>" for activity in activities]) + "</ul>"
            formatted_itinerary += f"{current_day} {activity_list}"
            current_day = None

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


def extract_and_geocode_cities(itinerary):
    cities = extract_cities_gpt(itinerary)  # Extract city names using GPT-4
    print(f"Extracted cities: {cities}")  # Debugging line
    locations = []

    for city in cities:
        print(f"city: {city}")
        lat, lng = geocode_location(city)
        if lat and lng:
            locations.append({"name": city, "lat": lat, "lng": lng})
        else:
            print(f"Failed to geocode {city}")

    print(f"Geocoded locations: {locations}")
    return locations


# Extract city names using GPT-4
def extract_cities_gpt(itinerary):
    prompt = f"""
    Extract all the city names mentioned in the following itinerary: 
    {itinerary}. 
    Please provide the city names separated by commas.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": "You are an expert in travel."
            }, {
                "role": "user",
                "content": prompt
            }],
            max_tokens=500,
            temperature=0.3)

        cities_text = response.choices[0].message.content
        print(f"- >> Extracted cities: {cities_text}")
        cities = [city.strip() for city in cities_text.split(", ")]
        return cities

    except Exception as e:
        print(f"Error during city extraction: {str(e)}")
        return []


# Geocode the extracted cities using Google Maps API
def geocode_location(location_name):
    api_key = os.getenv('GOOGLE_DIRECTIONS_API_KEY')
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location_name}&key={api_key}"

    try:
        response = requests.get(geocode_url)
        geocode_data = response.json()
        print("status = " + geocode_data['status'])

        if geocode_data['status'] == 'OK':
            lat_lng = geocode_data['results'][0]['geometry']['location']
            print(str(lat_lng['lat']) + " - " + str(lat_lng['lng']))
            return lat_lng['lat'], lat_lng['lng']
        else:
            return None, None
    except Exception as e:
        print(f"Error during geocode_location: {str(e)}")
        return None, None
