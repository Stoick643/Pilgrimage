"""SQLite cache service — key/value with TTL + shared trips storage."""

import json
import logging
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(os.getenv("CACHE_DB_PATH", str(Path(__file__).parent.parent / "couch_traveller.db")))


class Cache:
    """Simple key/value cache backed by SQLite."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_seconds INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shared_trips (
                    id TEXT PRIMARY KEY,
                    country TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    language TEXT NOT NULL,
                    activities TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()
        logger.info(f"Cache initialized: {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get(self, key: str) -> Any | None:
        """Get a cached value. Returns None if missing or expired."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value, created_at, ttl_seconds FROM cache WHERE key = ?",
                (key,)
            ).fetchone()

        if not row:
            return None

        value, created_at, ttl = row
        if ttl > 0 and (time.time() - created_at) > ttl:
            # Expired — clean up
            self.delete(key)
            logger.debug(f"Cache expired: {key}")
            return None

        logger.debug(f"Cache hit: {key}")
        return json.loads(value)

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Store a value. TTL in seconds (0 = never expires)."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, created_at, ttl_seconds) VALUES (?, ?, ?, ?)",
                (key, json.dumps(value), time.time(), ttl),
            )
            conn.commit()
        logger.debug(f"Cache set: {key} (ttl={ttl}s)")

    def delete(self, key: str) -> None:
        """Delete a cached entry."""
        with self._connect() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()

    def clear_expired(self) -> int:
        """Remove all expired entries. Returns count deleted."""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM cache WHERE ttl_seconds > 0 AND (? - created_at) > ttl_seconds",
                (time.time(),),
            )
            conn.commit()
            count = cursor.rowcount
        if count:
            logger.info(f"Cleared {count} expired cache entries")
        return count

    def clear_all(self) -> None:
        """Clear entire cache."""
        with self._connect() as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()
        logger.info("Cache cleared")


    def save_shared_trip(self, country: str, duration: int, language: str,
                         activities: str, content: str) -> str:
        """Save a trip for sharing. Returns unique ID."""
        trip_id = uuid.uuid4().hex[:12]
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO shared_trips (id, country, duration, language, activities, content, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (trip_id, country, duration, language, activities, content, time.time()),
            )
            conn.commit()
        logger.info(f"Saved shared trip: {trip_id} ({country})")
        return trip_id

    def get_shared_trip(self, trip_id: str) -> dict | None:
        """Get a shared trip by ID. Returns dict or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, country, duration, language, activities, content, created_at "
                "FROM shared_trips WHERE id = ?",
                (trip_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "country": row[1],
            "duration": row[2],
            "language": row[3],
            "activities": row[4],
            "content": row[5],
            "created_at": row[6],
        }


def make_cache_key(prefix: str, *args: str) -> str:
    """Build a cache key from prefix and args. e.g. make_cache_key('itinerary', 'sicily', '5')"""
    parts = [prefix] + [str(a).lower().strip() for a in args]
    return ":".join(parts)
