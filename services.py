import os

import requests

OAI_MODEL = "gpt-4o-mini"
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')


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


# Manually added images for cities
city_images = {"Rome": "/static/images/rome.jpg"}


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
