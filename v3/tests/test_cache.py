"""Tests for services/cache.py — SQLite cache."""

import time
import pytest
from pathlib import Path
from v3.services.cache import Cache, make_cache_key


@pytest.fixture
def cache(tmp_path):
    """Create a cache with a temp database."""
    return Cache(db_path=tmp_path / "test.db")


class TestCache:

    def test_set_and_get(self, cache):
        cache.set("key1", {"hello": "world"}, ttl=3600)
        result = cache.get("key1")
        assert result == {"hello": "world"}

    def test_get_missing_returns_none(self, cache):
        assert cache.get("nonexistent") is None

    def test_expired_returns_none(self, cache):
        cache.set("key1", "value", ttl=1)
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_zero_ttl_never_expires(self, cache):
        cache.set("key1", "forever", ttl=0)
        result = cache.get("key1")
        assert result == "forever"

    def test_overwrite(self, cache):
        cache.set("key1", "old", ttl=3600)
        cache.set("key1", "new", ttl=3600)
        assert cache.get("key1") == "new"

    def test_delete(self, cache):
        cache.set("key1", "value", ttl=3600)
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear_expired(self, cache):
        cache.set("keep", "value", ttl=3600)
        cache.set("expire", "value", ttl=1)
        time.sleep(1.1)
        count = cache.clear_expired()
        assert count == 1
        assert cache.get("keep") == "value"
        assert cache.get("expire") is None

    def test_clear_all(self, cache):
        cache.set("a", 1, ttl=3600)
        cache.set("b", 2, ttl=3600)
        cache.clear_all()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_complex_values(self, cache):
        data = {"days": [{"city": "Rome", "temp": 15.5}], "count": 3}
        cache.set("complex", data, ttl=3600)
        assert cache.get("complex") == data


class TestSharedTrips:

    def test_save_and_get(self, cache):
        trip_id = cache.save_shared_trip(
            country="Italy", duration=5, language="en",
            activities="history, food", content="&&& Rome\n### Day 1"
        )
        assert len(trip_id) == 12

        trip = cache.get_shared_trip(trip_id)
        assert trip is not None
        assert trip["country"] == "Italy"
        assert trip["duration"] == 5
        assert trip["language"] == "en"
        assert trip["activities"] == "history, food"
        assert "Rome" in trip["content"]
        assert trip["created_at"] > 0

    def test_get_nonexistent(self, cache):
        assert cache.get_shared_trip("doesnotexist") is None

    def test_unique_ids(self, cache):
        id1 = cache.save_shared_trip("Italy", 3, "en", "", "content1")
        id2 = cache.save_shared_trip("Italy", 3, "en", "", "content2")
        assert id1 != id2


class TestMakeCacheKey:

    def test_basic(self):
        assert make_cache_key("itinerary", "Sicily", "5") == "itinerary:sicily:5"

    def test_normalizes_case(self):
        assert make_cache_key("geo", "ROME") == "geo:rome"

    def test_strips_whitespace(self):
        assert make_cache_key("weather", " Rome ") == "weather:rome"
