"""Tests for routers/pages.py — HTML pages + htmx partials."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from v2.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.state.llm_clients = []
    app.state.http_client = None
    return TestClient(app)


@pytest.fixture
def client_with_llm():
    from unittest.mock import AsyncMock, MagicMock
    app = create_app()

    mock_llm = AsyncMock()
    config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}
    app.state.llm_clients = [(mock_llm, config)]
    app.state.http_client = None

    return TestClient(app)


class TestIndexPage:

    def test_index_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Couch Traveller" in response.text
        assert "htmx" in response.text

    def test_index_has_form(self, client):
        response = client.get("/")
        assert 'name="country"' in response.text
        assert 'name="duration"' in response.text
        assert 'hx-post="/plan"' in response.text


class TestPlanPage:

    def test_plan_returns_itinerary_skeleton(self, client_with_llm):
        response = client_with_llm.post("/plan", data={
            "country": "Sicily",
            "duration": "3",
            "language": "en",
        })
        assert response.status_code == 200
        assert "Sicily" in response.text
        assert "3 Days" in response.text
        assert "sse-connect" in response.text  # SSE connection present

    def test_plan_empty_country_shows_error(self, client):
        response = client.post("/plan", data={
            "country": "",
            "duration": "3",
            "language": "en",
        })
        assert response.status_code == 400
        assert "country" in response.text.lower()

    def test_plan_invalid_duration(self, client):
        response = client.post("/plan", data={
            "country": "Italy",
            "duration": "0",
            "language": "en",
        })
        assert response.status_code == 400


class TestPartials:

    def test_city_image_partial(self, client):
        """Personal photos should return rendered HTML."""
        response = client.get("/partials/city-image?city=Rome&country=Italy")
        assert response.status_code == 200
        assert "Rome" in response.text
        assert "img" in response.text
        assert "Darko Mulej" in response.text

    def test_weather_partial_no_key(self, client):
        with patch("v2.routers.pages.settings") as mock_settings:
            mock_settings.openweathermap_api_key = None
            response = client.get("/partials/weather?city=Rome")
        assert response.status_code == 200
        # Empty response when no API key
        assert "°C" not in response.text
