"""Tests for routers/api.py — API endpoints."""

import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from v3.app import create_app
from v3.services.cache import Cache


@pytest.fixture
def client():
    """Test client with no LLM clients."""
    app = create_app()
    app.state.llm_clients = []
    app.state.http_client = None
    return TestClient(app)


@pytest.fixture
def client_with_llm(tmp_path):
    """Test client with a mocked async LLM client returning &&& marker text."""
    app = create_app()

    mock_llm = AsyncMock()
    mock_llm.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(
            content="&&& Rome\n### Day 1: Ancient Rome\n- Morning: Visit the Colosseum.\n- Afternoon: Explore the Roman Forum.\n- Evening: Dinner in Trastevere."
        ))]
    )
    config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}
    app.state.llm_clients = [(mock_llm, config)]
    app.state.http_client = None
    app.state.cache = Cache(db_path=tmp_path / "test_cache.db")

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
        assert "Colosseum" in data["days"][0]["content"]
        assert data["country"] == "Italy"

    def test_default_activities_and_language(self, client_with_llm):
        """Should work with minimal input."""
        response = client_with_llm.post("/api/generate", json={
            "country": "Italy",
            "duration": 1,
        })
        assert response.status_code == 200

    def test_error_response_from_llm(self):
        """LLM returning 'Error: ...' should return 400."""
        app = create_app()
        mock_llm = AsyncMock()
        mock_llm.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Error: Not a recognized destination"))]
        )
        config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}
        app.state.llm_clients = [(mock_llm, config)]
        app.state.http_client = None

        client = TestClient(app)
        response = client.post("/api/generate", json={
            "country": "Narnia",
            "duration": 3,
        })
        assert response.status_code == 400


class TestStreamEndpoint:

    def test_no_llm_returns_500(self, client):
        response = client.post("/api/stream", json={
            "country": "Italy",
            "duration": 3,
        })
        assert response.status_code == 500

    def test_stream_returns_sse(self, client_with_llm):
        """Streaming should return text/event-stream with raw text chunks."""
        async def fake_stream(*args, **kwargs):
            yield "&&& Rome\n"
            yield "### Day 1: Ancient Rome\n"
            yield "- Visit the Colosseum\n"

        with patch("v3.routers.api.llm_stream", side_effect=fake_stream):
            response = client_with_llm.post("/api/stream", json={
                "country": "Italy",
                "duration": 3,
            })

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        text = response.text
        assert "Rome" in text
        assert '"done": true' in text

    def test_stream_caches_result(self, client_with_llm):
        """First stream should cache; second stream should serve from cache without calling LLM."""
        call_count = 0

        async def fake_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            yield "&&& Rome\n### Day 1: Ancient Rome\n- Visit the Colosseum\n"

        with patch("v3.routers.api.llm_stream", side_effect=fake_stream):
            # First request — calls LLM
            response1 = client_with_llm.post("/api/stream", json={
                "country": "CacheTest",
                "duration": 1,
            })
            assert response1.status_code == 200
            assert "Rome" in response1.text
            assert call_count == 1

            # Second request — should hit cache, NOT call LLM
            response2 = client_with_llm.post("/api/stream", json={
                "country": "CacheTest",
                "duration": 1,
            })
            assert response2.status_code == 200
            assert "Rome" in response2.text
            assert call_count == 1  # Still 1 — cache hit

    def test_stream_cache_returns_done(self, client_with_llm):
        """Cached stream should still end with done signal."""
        async def fake_stream(*args, **kwargs):
            yield "&&& Paris\n### Day 1\n- Eiffel Tower\n"

        with patch("v3.routers.api.llm_stream", side_effect=fake_stream):
            client_with_llm.post("/api/stream", json={
                "country": "CacheDoneTest",
                "duration": 1,
            })

            # Second request from cache
            response = client_with_llm.post("/api/stream", json={
                "country": "CacheDoneTest",
                "duration": 1,
            })
            assert '"done": true' in response.text

    def test_validation_on_stream(self, client):
        response = client.post("/api/stream", json={
            "country": "",
            "duration": 3,
        })
        assert response.status_code == 422


class TestShareEndpoint:

    def test_share_creates_trip(self, client_with_llm):
        response = client_with_llm.post("/api/share", json={
            "country": "Italy",
            "duration": 5,
            "language": "en",
            "activities": "history, food",
            "content": "&&& Rome\n### Day 1: Ancient Rome\n- Visit the Colosseum",
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["url"].startswith("/trip/")
        assert len(data["id"]) == 12

    def test_share_missing_content(self, client_with_llm):
        response = client_with_llm.post("/api/share", json={
            "country": "Italy",
            "duration": 5,
            "content": "",
        })
        assert response.status_code == 422  # Pydantic validation

    def test_share_missing_country(self, client_with_llm):
        response = client_with_llm.post("/api/share", json={
            "country": "",
            "duration": 5,
            "content": "Some content",
        })
        assert response.status_code == 422  # Pydantic validation

    def test_shared_trip_viewable(self, client_with_llm):
        # Create shared trip
        share_resp = client_with_llm.post("/api/share", json={
            "country": "Japan",
            "duration": 3,
            "language": "en",
            "activities": "culture",
            "content": "&&& Tokyo\n### Day 1: Tokyo\n- Visit Meiji Shrine",
        })
        trip_id = share_resp.json()["id"]

        # View it
        view_resp = client_with_llm.get(f"/trip/{trip_id}")
        assert view_resp.status_code == 200
        assert "Japan" in view_resp.text
        assert "Tokyo" in view_resp.text

    def test_shared_trip_not_found(self, client_with_llm):
        response = client_with_llm.get("/trip/nonexistent99")
        assert response.status_code == 404


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
        with patch("v3.routers.api.settings") as mock_settings:
            mock_settings.openweathermap_api_key = None
            response = client.get("/api/city-weather?city=Rome")
        assert response.status_code == 200
        assert response.json()["forecast"] == []


class TestGeocodeEndpoint:

    def test_empty_cities(self, client):
        response = client.get("/api/geocode?cities=")
        assert response.status_code == 400

    def test_no_api_key_returns_empty(self, client):
        with patch("v3.routers.api.settings") as mock_settings:
            mock_settings.google_directions_api_key = None
            response = client.get("/api/geocode?cities=Rome,Florence")
        assert response.status_code == 200
        assert response.json()["locations"] == []
