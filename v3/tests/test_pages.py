"""Tests for routers/pages.py — HTML pages, streaming itinerary."""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from v3.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.state.llm_clients = []
    app.state.http_client = None
    return TestClient(app)


@pytest.fixture
def client_with_llm():
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

    def test_index_has_form(self, client):
        response = client.get("/")
        assert 'name="country"' in response.text
        assert 'name="duration"' in response.text

    def test_index_no_htmx(self, client):
        """V3 should not use htmx."""
        response = client.get("/")
        assert "htmx" not in response.text


class TestPlanPage:

    def test_plan_returns_itinerary_page(self, client_with_llm):
        response = client_with_llm.get("/plan?country=Sicily&duration=3&language=en")
        assert response.status_code == 200
        assert "Sicily" in response.text
        assert "3 Days" in response.text
        assert "/api/stream" in response.text  # SSE stream URL present

    def test_plan_empty_country_shows_error(self, client):
        response = client.get("/plan?country=&duration=3&language=en")
        assert response.status_code == 400
        assert "country" in response.text.lower()

    def test_plan_invalid_duration(self, client):
        response = client.get("/plan?country=Italy&duration=0&language=en")
        assert response.status_code == 400

    def test_plan_passes_stream_body(self, client_with_llm):
        response = client_with_llm.get("/plan?country=Japan&duration=5&language=de&activities=food&activities=culture")
        assert response.status_code == 200
        assert "Japan" in response.text
        assert "5 Days" in response.text

    def test_plan_default_duration(self, client_with_llm):
        response = client_with_llm.get("/plan?country=France")
        assert response.status_code == 200
        assert "France" in response.text
