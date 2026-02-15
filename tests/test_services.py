"""Tests for services.py — image fetching, weather, translation."""

import pytest
from unittest.mock import patch, MagicMock
from src.services import (
    get_image_url,
    get_weather_forecast_5d,
    translate_itinerary,
    DEFAULT_DESCRIPTION,
    ERROR_JPG,
)


# --- Unit tests for get_image_url ---

class TestGetImageUrl:

    def test_hardcoded_rome(self):
        url, desc = get_image_url("Rome")
        assert "staticflickr.com" in url
        assert desc['name'] == "Darko Mulej"

    def test_hardcoded_venice(self):
        url, desc = get_image_url("Venice")
        assert "staticflickr.com" in url
        assert desc['company'] == "Flickr"

    @patch('src.services.UNSPLASH_ACCESS_KEY', None)
    def test_no_unsplash_key_returns_fallback(self):
        url, desc = get_image_url("Berlin")
        assert url == ERROR_JPG
        assert desc == DEFAULT_DESCRIPTION

    @patch('src.services.UNSPLASH_ACCESS_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_unsplash_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'results': [{
                    'urls': {'regular': 'https://unsplash.com/photo.jpg'},
                    'user': {
                        'name': 'Photographer',
                        'links': {'html': 'https://unsplash.com/@photographer'},
                    },
                }]
            }
        )
        url, desc = get_image_url("Berlin")
        assert url == "https://unsplash.com/photo.jpg"
        assert desc['name'] == "Photographer"
        assert desc['company'] == "Unsplash"

    @patch('src.services.UNSPLASH_ACCESS_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_unsplash_empty_results(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {'results': []}
        )
        url, desc = get_image_url("Xyznoplace")
        assert url == ERROR_JPG

    @patch('src.services.UNSPLASH_ACCESS_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_unsplash_api_error(self, mock_get):
        mock_get.side_effect = Exception("Connection failed")
        url, desc = get_image_url("Berlin")
        assert url == ERROR_JPG

    @patch('src.services.UNSPLASH_ACCESS_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_unsplash_non_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=403)
        url, desc = get_image_url("Berlin")
        assert url == ERROR_JPG


# --- Unit tests for get_weather_forecast_5d ---

class TestGetWeatherForecast5d:

    @patch('src.services.OPENWEATHERMAP_API_KEY', None)
    def test_no_api_key(self):
        result = get_weather_forecast_5d("Paris")
        assert isinstance(result, str)
        assert "not configured" in result

    @patch('src.services.OPENWEATHERMAP_API_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_successful_forecast(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'list': [
                    {
                        'dt_txt': '2026-02-15 15:00:00',
                        'main': {'temp': 8.4},
                        'weather': [{'description': 'cloudy', 'icon': '04d'}],
                    },
                    {
                        'dt_txt': '2026-02-15 18:00:00',
                        'main': {'temp': 6.0},
                        'weather': [{'description': 'clear', 'icon': '01n'}],
                    },
                    {
                        'dt_txt': '2026-02-16 15:00:00',
                        'main': {'temp': 12.1},
                        'weather': [{'description': 'sunny', 'icon': '01d'}],
                    },
                ]
            }
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = get_weather_forecast_5d("Paris")
        assert isinstance(result, list)
        assert len(result) == 2  # Two days at 15:00
        assert result[0]['temperature'] == 8
        assert result[1]['temperature'] == 12
        assert result[0]['date'] == "15.02"

    @patch('src.services.OPENWEATHERMAP_API_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_api_request_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("Timeout")
        result = get_weather_forecast_5d("Paris")
        assert isinstance(result, str)
        assert "Error" in result


# --- Unit tests for translate_itinerary ---

class TestTranslateItinerary:

    def test_english_passthrough(self):
        """English should return itinerary unchanged without API call."""
        itinerary = "&&& Rome\n### Day 1: Welcome to Rome"
        result = translate_itinerary(None, itinerary, "en")
        assert result == itinerary

    @patch('src.services.LLM_MODEL', 'deepseek-chat')
    def test_translation_called(self):
        """Non-English should call the OpenAI API."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="&&& Rome\n### Giorno 1: Benvenuti a Roma"))]
        )
        result = translate_itinerary(mock_client, "&&& Rome\n### Day 1: Welcome to Rome", "it")
        assert "Giorno 1" in result
        mock_client.chat.completions.create.assert_called_once()

    def test_translation_error_handling(self):
        """API failure should return error string, not crash."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API down")
        result = translate_itinerary(mock_client, "Some text", "de")
        assert "Error" in result
