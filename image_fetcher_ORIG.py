import os

import requests

# Manually added images for cities
city_images = {
    "Rome": "/static/images/rome.jpg",
    "Florence": "/static/images/florence.jpg",
    "Venice": "/static/images/venice.jpg"
}

UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')


# Function to fetch images dynamically from Unsplash
def get_image_url(query):
    print(f"get_image_url start for {query}")
    # Check if the city has a manually added image first
    if query in city_images:
        return city_images[query]

    # If not, try fetching from Unsplash
    if UNSPLASH_ACCESS_KEY:
        search_url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "per_page": 1,
            "client_id": UNSPLASH_ACCESS_KEY
        }
        response = requests.get(search_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                return data['results'][0]['urls']['regular']  
    return "/static/images/default.jpg"  # Return a default image if no result found
