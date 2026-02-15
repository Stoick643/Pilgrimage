import logging
import os

import requests

logger = logging.getLogger(__name__)

GOOGLE_DIRECTIONS_API_KEY = os.getenv('GOOGLE_DIRECTIONS_API_KEY')


def extract_and_geocode_cities(itinerary):
    """Extract city names from itinerary markers and geocode them."""
    cities = extract_cities(itinerary)
    logger.info(f"Extracted cities: {cities}")
    return geocode_cities(cities)


def extract_cities(text):
    """Extract city names from lines starting with '&&&' markers."""
    result = []
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('&&&'):
            city = line[3:].strip()
            if city:
                result.append(city)
    return result


def geocode_cities(cities):
    """Geocode a list of city names to lat/lng coordinates."""
    locations = []
    for city in cities:
        lat, lng = geocode_location(city)
        if lat and lng:
            locations.append({"name": city, "lat": lat, "lng": lng})
        else:
            logger.warning(f"Failed to geocode {city}")
    return locations


def geocode_location(location_name):
    """Geocode a single location using Google Maps API."""
    if not GOOGLE_DIRECTIONS_API_KEY:
        logger.warning("GOOGLE_DIRECTIONS_API_KEY not set — skipping geocoding")
        return None, None

    geocode_url = (
        f"https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={location_name}&key={GOOGLE_DIRECTIONS_API_KEY}"
    )

    try:
        response = requests.get(geocode_url)
        geocode_data = response.json()
        if geocode_data['status'] == 'OK':
            lat_lng = geocode_data['results'][0]['geometry']['location']
            logger.info(f"Geocoded {location_name}: {lat_lng['lat']}, {lat_lng['lng']}")
            return lat_lng['lat'], lat_lng['lng']
        else:
            logger.warning(f"Geocoding failed for {location_name}: {geocode_data['status']}")
            return None, None
    except Exception as e:
        logger.error(f"Error during geocoding {location_name}: {e}")
        return None, None
