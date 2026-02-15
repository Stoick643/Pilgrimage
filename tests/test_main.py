"""Tests for routes and itinerary formatting."""

import pytest
from src.formatters import extract_text_with_cities, prepare_itinerary_data, weather_html


# --- Unit tests for extract_text_with_cities ---

class TestExtractTextWithCities:

    def test_basic_extraction(self):
        text = """&&& Paris
### Day 1: Welcome to Paris
Visit the Eiffel Tower.
&&& Lyon
### Day 2: Explore Lyon
Visit the old town."""
        result = extract_text_with_cities(text)
        assert len(result) == 2
        assert result[0][0] == "Paris"
        assert "Eiffel Tower" in result[0][1]
        assert result[1][0] == "Lyon"
        assert "old town" in result[1][1]

    def test_empty_text(self):
        assert extract_text_with_cities("") == []

    def test_no_markers(self):
        text = "Just some random text without any markers."
        assert extract_text_with_cities(text) == []

    def test_single_city(self):
        text = """&&& Rome
### Day 1: Rome
Visit the Colosseum."""
        result = extract_text_with_cities(text)
        assert len(result) == 1
        assert result[0][0] == "Rome"

    def test_whitespace_handling(self):
        text = """  &&& Berlin  
### Day 1: Berlin
Visit Brandenburg Gate."""
        result = extract_text_with_cities(text)
        assert len(result) == 1
        assert result[0][0] == "Berlin"

    def test_empty_marker_ignored(self):
        text = """&&&
### Day 1: Nowhere
Some text."""
        result = extract_text_with_cities(text)
        # Empty city name after &&&, current_city becomes "" which is falsy
        assert len(result) == 0

    def test_multiple_days_same_city(self):
        text = """&&& Tokyo
### Day 1: Arrival in Tokyo
Explore Shibuya.
&&& Tokyo
### Day 2: More Tokyo
Visit Asakusa."""
        result = extract_text_with_cities(text)
        assert len(result) == 2
        assert result[0][0] == "Tokyo"
        assert result[1][0] == "Tokyo"


# --- Unit tests for weather_html ---

class TestWeatherHtml:

    def test_returns_empty_on_error_string(self, monkeypatch):
        monkeypatch.setattr('src.formatters.get_weather_forecast_5d', lambda city: "Error: API failed")
        assert weather_html("Paris") == ""

    def test_returns_html_on_valid_forecast(self, monkeypatch):
        mock_forecast = [
            {"date": "15.02", "temperature": 8, "icon": "04d"},
            {"date": "16.02", "temperature": 10, "icon": "01d"},
        ]
        monkeypatch.setattr('src.formatters.get_weather_forecast_5d', lambda city: mock_forecast)
        result = weather_html("Paris")
        assert "weather-container" in result
        assert "8 °C" in result
        assert "10 °C" in result
        assert "04d" in result

    def test_returns_empty_on_empty_list(self, monkeypatch):
        monkeypatch.setattr('src.formatters.get_weather_forecast_5d', lambda city: [])
        result = weather_html("Paris")
        assert "weather-container" in result  # container still rendered, just empty


# --- Integration tests for routes ---

class TestRoutes:

    def test_index_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'Itinerary Planning App' in response.data

    def test_generate_itinerary_missing_country(self, client):
        response = client.post('/generate-itinerary', data={
            'country': '',
            'duration': '3',
            'language': 'en',
        })
        assert response.status_code == 400

    def test_generate_itinerary_missing_duration(self, client):
        response = client.post('/generate-itinerary', data={
            'country': 'Italy',
            'duration': '',
            'language': 'en',
        })
        assert response.status_code == 400

    def test_generate_itinerary_invalid_duration(self, client):
        response = client.post('/generate-itinerary', data={
            'country': 'Italy',
            'duration': '0',
            'language': 'en',
        })
        assert response.status_code == 400

    def test_generate_itinerary_negative_duration(self, client):
        response = client.post('/generate-itinerary', data={
            'country': 'Italy',
            'duration': '-3',
            'language': 'en',
        })
        assert response.status_code == 400


class TestStreamRoute:

    def test_stream_missing_country(self, client):
        response = client.post('/api/stream-itinerary', data={
            'country': '',
            'duration': '3',
            'language': 'en',
        })
        assert response.status_code == 400
        assert b'error' in response.data

    def test_stream_invalid_duration(self, client):
        response = client.post('/api/stream-itinerary', data={
            'country': 'Italy',
            'duration': '0',
            'language': 'en',
        })
        assert response.status_code == 400

    def test_stream_no_llm_returns_500(self, client):
        """No LLM clients configured → 500."""
        response = client.post('/api/stream-itinerary', data={
            'country': 'Italy',
            'duration': '3',
            'language': 'en',
        })
        assert response.status_code == 500

    def test_stream_returns_sse(self, client, monkeypatch):
        """With a mocked LLM, should return SSE text/event-stream."""
        def fake_stream(*args, **kwargs):
            yield "&&&Rome\n"
            yield "### Day 1: Rome\n"
            yield "Visit the Colosseum\n"

        monkeypatch.setattr('src.routes.llm_stream', fake_stream)
        # Give the app a fake client so the "no clients" check passes
        from flask import current_app
        with client.application.app_context():
            client.application.llm_clients = [("fake_client", {"provider": "Test"})]

        response = client.post('/api/stream-itinerary', data={
            'country': 'Italy',
            'duration': '3',
            'language': 'en',
        })
        assert response.status_code == 200
        assert 'text/event-stream' in response.content_type
        data = response.get_data(as_text=True)
        assert 'Rome' in data
        assert 'Colosseum' in data
        assert '"done": true' in data
