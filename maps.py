import os

import requests
from openai import OpenAI

from services import call_openai_api

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def geocode_cities(cities):
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


# Use GPT to extract cities and then geocode them
def extract_and_geocode_cities(itinerary):
    cities = extract_cities(itinerary)  # Extract city names using GPT-4
    print(f"Extracted cities: {cities}")  # Debugg    ing line
    return geocode_cities(cities)  # Geocode the cities


def extract_cities(text):
    result = []  # To store the strings from lines starting with "&&&"
    lines = text.split('\n')  # Split the input text into lines

    for line in lines:
        line = line.strip()  # Remove leading/trailing spaces
        if line.startswith('&&&'):  # Check if the line starts with "&&&"
            result.append(line[3:].strip()
                          )  # Extract the part after "&&&" and add to list

    return result


# Extract city names using GPT-4
def extract_cities_gpt(itinerary):
    prompt = f"""
    Extract all the city names mentioned in the following itinerary: 
    {itinerary}. 
    Please provide the city names separated by commas.
    """
    try:
        cities = call_openai_api(client, prompt)
        print(f"- >> Extracted cities: {cities}")
        cities = [city.strip() for city in cities.split(", ")]
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
