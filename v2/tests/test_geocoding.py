"""Tests for services/geocoding.py — geocoding."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from v2.services.geocoding import geocode_city, geocode_cities


@pytest.mark.asyncio
class TestGeocodeCity:

    async def test_no_api_key(self):
        result = await geocode_city("Rome", api_key=None)
        assert result is None

    async def test_successful_geocode(self):
        mock_data = {
            "status": "OK",
            "results": [{"geometry": {"location": {"lat": 41.9, "lng": 12.5}}}],
        }
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("v2.services.geocoding.httpx.AsyncClient", return_value=mock_client):
            result = await geocode_city("Rome", api_key="test-key")

        assert result == {"name": "Rome", "lat": 41.9, "lng": 12.5}

    async def test_failed_geocode(self):
        mock_data = {"status": "ZERO_RESULTS", "results": []}
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("v2.services.geocoding.httpx.AsyncClient", return_value=mock_client):
            result = await geocode_city("Nonexistent", api_key="test-key")

        assert result is None

    async def test_api_exception(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("v2.services.geocoding.httpx.AsyncClient", return_value=mock_client):
            result = await geocode_city("Rome", api_key="test-key")

        assert result is None


@pytest.mark.asyncio
class TestGeocodeCities:

    async def test_multiple_cities(self):
        async def mock_geocode(city, api_key=None, http_client=None):
            coords = {"Rome": (41.9, 12.5), "Florence": (43.8, 11.3)}
            if city in coords:
                return {"name": city, "lat": coords[city][0], "lng": coords[city][1]}
            return None

        with patch("v2.services.geocoding.geocode_city", side_effect=mock_geocode):
            result = await geocode_cities(["Rome", "Florence", "Rome"], api_key="test")

        assert len(result) == 3  # Includes duplicate Rome
        assert result[0]["name"] == "Rome"
        assert result[1]["name"] == "Florence"
        assert result[2]["name"] == "Rome"

    async def test_deduplicates_api_calls(self):
        call_count = 0

        async def mock_geocode(city, api_key=None, http_client=None):
            nonlocal call_count
            call_count += 1
            return {"name": city, "lat": 0.0, "lng": 0.0}

        with patch("v2.services.geocoding.geocode_city", side_effect=mock_geocode):
            await geocode_cities(["Rome", "Rome", "Rome"], api_key="test")

        assert call_count == 1  # Only one API call despite 3 cities
