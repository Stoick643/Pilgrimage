"""Tests for services/weather.py — weather forecast."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from v3.services.weather import get_forecast


@pytest.mark.asyncio
class TestGetForecast:

    async def test_no_api_key(self):
        result = await get_forecast("Rome", api_key=None)
        assert result == []

    async def test_successful_forecast(self):
        mock_data = {
            "list": [
                {
                    "dt_txt": "2026-02-16 15:00:00",
                    "main": {"temp": 12.3},
                    "weather": [{"description": "cloudy", "icon": "04d"}],
                },
                {
                    "dt_txt": "2026-02-16 18:00:00",
                    "main": {"temp": 10},
                    "weather": [{"description": "rain", "icon": "10d"}],
                },
                {
                    "dt_txt": "2026-02-17 15:00:00",
                    "main": {"temp": 14.7},
                    "weather": [{"description": "sunny", "icon": "01d"}],
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("v3.services.weather.httpx.AsyncClient", return_value=mock_client):
            result = await get_forecast("Rome", api_key="test-key")

        assert len(result) == 2  # Only 15:00 entries, one per day
        assert result[0]["temperature"] == 12
        assert result[0]["date"] == "16.02"
        assert result[1]["temperature"] == 15
        assert "icon_url" in result[0]

    async def test_api_error_returns_empty(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("v3.services.weather.httpx.AsyncClient", return_value=mock_client):
            result = await get_forecast("Rome", api_key="test-key")

        assert result == []
