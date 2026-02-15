"""Tests for routers/api.py — API endpoints."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from v2.app import create_app


@pytest.fixture
def client():
    """Test client with no LLM clients."""
    app = create_app()
    app.state.llm_clients = []
    app.state.http_client = None
    return TestClient(app)


@pytest.fixture
def client_with_llm():
    """Test client with a mocked async LLM client."""
    app = create_app()

    mock_llm = AsyncMock()
    mock_llm.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps({
            "days": [{
                "day": 1,
                "city": "Rome",
                "title": "Day 1: Ancient Rome",
                "morning": "Visit the Colosseum.",
                "afternoon": "Explore the Roman Forum.",
                "evening": "Dinner in Trastevere.",
                "tip": "Buy skip-the-line tickets.",
            }]
        })))]
    )
    config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}
    app.state.llm_clients = [(mock_llm, config)]
    app.state.http_client = None

    return TestClient(app)


class TestGenerateEndpoint:

    def test_missing_country(self, client):
        response = client.post("/api/generate", json={
            "country": "",
            "duration": 3,
        })
        assert response.status_code == 422  # Pydantic validation

    def test_invalid_duration_zero(self, client):
        response = client.post("/api/generate", json={
            "country": "Italy",
            "duration": 0,
        })
        assert response.status_code == 422

    def test_invalid_duration_negative(self, client):
        response = client.post("/api/generate", json={
            "country": "Italy",
            "duration": -3,
        })
        assert response.status_code == 422

    def test_duration_too_long(self, client):
        response = client.post("/api/generate", json={
            "country": "Italy",
            "duration": 31,
        })
        assert response.status_code == 422

    def test_no_llm_returns_500(self, client):
        response = client.post("/api/generate", json={
            "country": "Italy",
            "duration": 3,
        })
        assert response.status_code == 500
        assert "No LLM" in response.json()["detail"]

    def test_successful_generation(self, client_with_llm):
        response = client_with_llm.post("/api/generate", json={
            "country": "Italy",
            "duration": 3,
            "activities": ["history", "food"],
            "language": "en",
        })
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert data["days"][0]["city"] == "Rome"
        assert data["days"][0]["morning"] == "Visit the Colosseum."
        assert data["country"] == "Italy"  # Country injected for image disambiguation

    def test_default_activities_and_language(self, client_with_llm):
        """Should work with minimal input."""
        response = client_with_llm.post("/api/generate", json={
            "country": "Italy",
            "duration": 1,
        })
        assert response.status_code == 200


class TestStreamEndpoint:

    def test_no_llm_returns_500(self, client):
        response = client.post("/api/stream", json={
            "country": "Italy",
            "duration": 3,
        })
        assert response.status_code == 500

    def test_stream_returns_sse(self, client_with_llm):
        """Streaming should return text/event-stream with chunks."""
        async def fake_stream(*args, **kwargs):
            yield '{"days": [{'
            yield '"day": 1, "city": "Rome"'
            yield '}]}'

        with patch("v2.routers.api.llm_stream", side_effect=fake_stream):
            response = client_with_llm.post("/api/stream", json={
                "country": "Italy",
                "duration": 3,
            })

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        text = response.text
        assert "Rome" in text
        assert '"done": true' in text

    def test_validation_on_stream(self, client):
        response = client.post("/api/stream", json={
            "country": "",
            "duration": 3,
        })
        assert response.status_code == 422


class TestCityImageEndpoint:

    def test_empty_city(self, client):
        response = client.get("/api/city-image?city=")
        assert response.status_code == 400

    def test_personal_photo(self, client):
        response = client.get("/api/city-image?city=Rome")
        assert response.status_code == 200
        data = response.json()
        assert "staticflickr.com" in data["image_url"]
        assert data["credit"]["name"] == "Darko Mulej"

    def test_with_country_param(self, client):
        """Country param should be accepted."""
        response = client.get("/api/city-image?city=Syracuse&country=Sicily")
        assert response.status_code == 200


class TestWeatherEndpoint:

    def test_empty_city(self, client):
        response = client.get("/api/city-weather?city=")
        assert response.status_code == 400

    def test_no_api_key_returns_empty(self, client):
        with patch("v2.routers.api.settings") as mock_settings:
            mock_settings.openweathermap_api_key = None
            response = client.get("/api/city-weather?city=Rome")
        assert response.status_code == 200
        assert response.json()["forecast"] == []


class TestGeocodeEndpoint:

    def test_empty_cities(self, client):
        response = client.get("/api/geocode?cities=")
        assert response.status_code == 400

    def test_no_api_key_returns_empty(self, client):
        with patch("v2.routers.api.settings") as mock_settings:
            mock_settings.google_directions_api_key = None
            response = client.get("/api/geocode?cities=Rome,Florence")
        assert response.status_code == 200
        assert response.json()["locations"] == []
