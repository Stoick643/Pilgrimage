import pytest
from maps import extract_cities_gpt, geocode_location


def test_extract_cities_gpt():
    itinerary_text = "Visit Rome, Florence, and Venice on your 7-day trip to Italy."

    cities = extract_cities_gpt(itinerary_text)

    assert "Rome" in cities
    assert "Florence" in cities
    assert "Venice" in cities
    assert len(cities) == 3


def test_geocode_location(monkeypatch):
    # Mocking the response from geocode_location
    def mock_geocode_location(city_name):
        if city_name == "Rome":
            return (41.9028, 12.4964)  # Rome coordinates
        return (None, None)

    monkeypatch.setattr('maps.geocode_location', mock_geocode_location)

    lat, lng = geocode_location("Rome")
    assert lat == 41.9028
    assert lng == 12.4964

    lat, lng = geocode_location("Unknown City")
    assert lat is None
    assert lng is None
