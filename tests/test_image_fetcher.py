import pytest

from image_fetcher import get_image_url


def test_get_image_url(monkeypatch):
    # Mocking the API response
    def mock_get_image_url(city_name):
        if city_name == "Rome":
            return "https://example.com/rome.jpg"
        return "https://example.com/default.jpg"

    monkeypatch.setattr('image_fetcher.get_image_url', mock_get_image_url)

    # Test for a known city
    image_url = get_image_url("Rome")
    assert image_url == "https://example.com/rome.jpg"

    # Test for an unknown city
    image_url = get_image_url("Unknown City")
    assert image_url == "https://example.com/default.jpg"
