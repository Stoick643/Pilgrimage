"""Shared test fixtures for V3."""

import pytest
from fastapi.testclient import TestClient
from v3.app import create_app


@pytest.fixture
def app():
    """Create a test app instance."""
    return create_app()
