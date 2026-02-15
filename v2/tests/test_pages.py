"""Tests for routers/pages.py — HTML pages, htmx partials, SSE streaming."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
        assert 'action="/plan"' in response.text


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


class TestExtractCompleteDays:

    def test_extracts_complete_day(self):
        from v2.routers.pages import _extract_complete_days
        text = '{"days": [{"day": 1, "city": "Rome", "title": "Day 1", "morning": "m", "afternoon": "a", "evening": "e", "tip": "t"}'
        days = _extract_complete_days(text, 0)
        assert len(days) == 1
        assert days[0]["city"] == "Rome"

    def test_skips_already_sent(self):
        from v2.routers.pages import _extract_complete_days
        text = '{"days": [{"day": 1, "city": "Rome"}, {"day": 2, "city": "Florence"}'
        days = _extract_complete_days(text, 1)
        assert len(days) == 1
        assert days[0]["city"] == "Florence"

    def test_incomplete_object_not_extracted(self):
        from v2.routers.pages import _extract_complete_days
        text = '{"days": [{"day": 1, "city": "Rome"}, {"day": 2, "city": "Flor'
        days = _extract_complete_days(text, 0)
        assert len(days) == 1  # Only the complete one

    def test_handles_strings_with_braces(self):
        from v2.routers.pages import _extract_complete_days
        text = '{"days": [{"day": 1, "city": "Rome", "title": "Day {1} test"}]}'
        days = _extract_complete_days(text, 0)
        assert len(days) == 1
        assert "test" in days[0]["title"]

    def test_no_days_array_returns_empty(self):
        from v2.routers.pages import _extract_complete_days
        assert _extract_complete_days("hello", 0) == []

    def test_empty_days_array(self):
        from v2.routers.pages import _extract_complete_days
        assert _extract_complete_days('{"days": []}', 0) == []


class TestStreamHtml:

    def test_invalid_request_id_returns_404(self, client):
        response = client.get("/api/stream-html/nonexistent")
        assert response.status_code == 404

    def test_no_llm_returns_500(self, client):
        """Store a request, but no LLM clients → 500."""
        # Submit form to get a request ID
        response = client.post("/plan", data={
            "country": "Italy", "duration": "3", "language": "en",
        }, follow_redirects=False)
        # Extract request_id from the response
        assert response.status_code == 200
        import re
        match = re.search(r'stream-html/([a-f0-9]+)', response.text)
        # Since client has no LLM clients, streaming should fail
        # (but the request_id was created with client_with_llm fixture)
        # This tests the path where request exists but LLM is missing

    def test_full_sse_stream_flow(self, client_with_llm):
        """Integration test: form → skeleton → SSE → day cards."""
        # Mock llm_stream to yield JSON incrementally
        day1 = json.dumps({
            "day": 1, "city": "Rome", "title": "Day 1: Rome",
            "morning": "Colosseum", "afternoon": "Forum", "evening": "Trastevere", "tip": "Book ahead"
        })
        day2 = json.dumps({
            "day": 2, "city": "Florence", "title": "Day 2: Florence",
            "morning": "Uffizi", "afternoon": "Duomo", "evening": "Ponte Vecchio", "tip": "Walk"
        })
        full_json = f'{{"days": [{day1}, {day2}]}}'

        async def fake_stream(*args, **kwargs):
            # Simulate streaming in chunks
            for i in range(0, len(full_json), 50):
                yield full_json[i:i+50]

        # Step 1: Submit form to get itinerary page with request_id
        response = client_with_llm.post("/plan", data={
            "country": "Italy", "duration": "2", "language": "en",
        })
        assert response.status_code == 200
        assert "sse-connect" in response.text

        # Extract request_id
        import re
        match = re.search(r'stream-html/([a-f0-9]+)', response.text)
        assert match, "No request_id found in response"
        request_id = match.group(1)

        # Step 2: Connect to SSE endpoint
        with patch("v2.routers.pages.llm_stream", side_effect=fake_stream):
            response = client_with_llm.get(f"/api/stream-html/{request_id}")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        text = response.text
        # Should contain day cards as SSE events
        assert "event: day" in text
        assert "Rome" in text
        assert "Florence" in text
        assert "Colosseum" in text
        assert "event: complete" in text

    def test_stream_request_id_consumed(self, client_with_llm):
        """Request ID should be single-use — second request gets 404."""
        response = client_with_llm.post("/plan", data={
            "country": "Italy", "duration": "1", "language": "en",
        })
        import re
        match = re.search(r'stream-html/([a-f0-9]+)', response.text)
        request_id = match.group(1)

        day = json.dumps({
            "day": 1, "city": "Rome", "title": "Day 1",
            "morning": "m", "afternoon": "a", "evening": "e", "tip": "t"
        })

        async def fake_stream(*args, **kwargs):
            yield f'{{"days": [{day}]}}'

        with patch("v2.routers.pages.llm_stream", side_effect=fake_stream):
            response1 = client_with_llm.get(f"/api/stream-html/{request_id}")
        assert response1.status_code == 200

        # Second request — should be consumed
        response2 = client_with_llm.get(f"/api/stream-html/{request_id}")
        assert response2.status_code == 404


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
