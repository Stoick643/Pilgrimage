"""Tests for services/images.py — image fetching."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from v3.services.images import get_image_url, ERROR_JPG, DEFAULT_CREDIT, MY_IMAGES


@pytest.mark.asyncio
class TestGetImageUrl:

    async def test_personal_photo_rome(self):
        url, credit = await get_image_url("Rome")
        assert "staticflickr.com" in url
        assert credit["name"] == "Darko Mulej"

    async def test_personal_photo_venice(self):
        url, credit = await get_image_url("Venice")
        assert "staticflickr.com" in url
        assert credit["company"] == "Flickr"

    async def test_no_unsplash_key_returns_fallback(self):
        url, credit = await get_image_url("Unknown City", unsplash_key=None)
        assert url == ERROR_JPG

    async def test_unsplash_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{
                "urls": {"regular": "https://images.unsplash.com/photo-test"},
                "user": {
                    "name": "Test User",
                    "links": {"html": "https://unsplash.com/@test"},
                },
            }]
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("v3.services.images.httpx.AsyncClient", return_value=mock_client):
            url, credit = await get_image_url("Agrigento", country="Sicily", unsplash_key="test-key")

        assert url == "https://images.unsplash.com/photo-test"
        assert credit["name"] == "Test User"
        assert credit["company"] == "Unsplash"

        # Verify country was appended to query
        call_args = mock_client.get.call_args
        assert "Sicily" in call_args[1]["params"]["query"]

    async def test_unsplash_empty_results(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("v3.services.images.httpx.AsyncClient", return_value=mock_client):
            url, credit = await get_image_url("Nonexistent", unsplash_key="test-key")

        assert url == ERROR_JPG

    async def test_seen_urls_avoided(self):
        """Should avoid returning already-seen URLs for personal photos."""
        all_urls = set(MY_IMAGES["Rome"])
        seen = set(list(all_urls)[:2])  # Mark 2 of 3 as seen

        url, _ = await get_image_url("Rome", seen_urls=seen)
        # Should prefer the unseen URL
        unseen = all_urls - seen
        if unseen:
            assert url in unseen
