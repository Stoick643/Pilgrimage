"""Tests for maps.py — city extraction and geocoding."""

import pytest
from unittest.mock import patch, MagicMock
from src.maps import extract_cities, extract_and_geocode_cities, geocode_location


# --- Unit tests for extract_cities ---

class TestExtractCities:

    def test_basic_extraction(self):
        text = """&&& Rome
### Day 1: Rome
&&& Florence
### Day 2: Florence"""
        result = extract_cities(text)
        assert result == ["Rome", "Florence"]

    def test_empty_text(self):
        assert extract_cities("") == []

    def test_no_markers(self):
        assert extract_cities("Just a regular itinerary text.") == []

    def test_whitespace_in_city_name(self):
        text = "&&&   New York  "
        result = extract_cities(text)
        assert result == ["New York"]

    def test_empty_marker_excluded(self):
        text = "&&&\n&&& Paris"
        result = extract_cities(text)
        assert result == ["Paris"]

    def test_multiple_cities(self):
        text = """&&& Paris
Day 1 content
&&& Lyon
Day 2 content
&&& Marseille
Day 3 content"""
        result = extract_cities(text)
        assert result == ["Paris", "Lyon", "Marseille"]


# --- Unit tests for geocode_location ---

class TestGeocodeLocation:

    @patch('src.maps.GOOGLE_DIRECTIONS_API_KEY', None)
    def test_no_api_key_returns_none(self):
        lat, lng = geocode_location("Rome")
        assert lat is None
        assert lng is None

    @patch('src.maps.GOOGLE_DIRECTIONS_API_KEY', 'fake-key')
    @patch('src.maps.requests.get')
    def test_successful_geocode(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {
                'status': 'OK',
                'results': [{
                    'geometry': {
                        'location': {'lat': 41.9028, 'lng': 12.4964}
                    }
                }]
            }
        )
        lat, lng = geocode_location("Rome")
        assert lat == 41.9028
        assert lng == 12.4964

    @patch('src.maps.GOOGLE_DIRECTIONS_API_KEY', 'fake-key')
    @patch('src.maps.requests.get')
    def test_failed_geocode(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {'status': 'ZERO_RESULTS', 'results': []}
        )
        lat, lng = geocode_location("xyznonexistent")
        assert lat is None
        assert lng is None

    @patch('src.maps.GOOGLE_DIRECTIONS_API_KEY', 'fake-key')
    @patch('src.maps.requests.get')
    def test_api_exception(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        lat, lng = geocode_location("Rome")
        assert lat is None
        assert lng is None


# --- Integration test for extract_and_geocode_cities ---

class TestExtractAndGeocodeCities:

    @patch('src.maps.GOOGLE_DIRECTIONS_API_KEY', 'fake-key')
    @patch('src.maps.requests.get')
    def test_full_pipeline(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {
                'status': 'OK',
                'results': [{
                    'geometry': {
                        'location': {'lat': 48.8566, 'lng': 2.3522}
                    }
                }]
            }
        )
        text = """&&& Paris
### Day 1: Paris
Visit the Louvre."""
        result = extract_and_geocode_cities(text)
        assert len(result) == 1
        assert result[0]['name'] == "Paris"
        assert result[0]['lat'] == 48.8566
        assert result[0]['lng'] == 2.3522
