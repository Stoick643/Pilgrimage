"""FastAPI application — Couch Traveller V2."""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from v2.config import settings
from v2.routers.api import router as api_router
from v2.services.llm import create_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LLM clients and shared HTTP client at startup."""
    # Shared HTTP client for all services (connection pooling)
    app.state.http_client = httpx.AsyncClient(timeout=15.0)

    # LLM clients
    providers = settings.llm_providers
    if not providers:
        logger.warning("No LLM API key set — itinerary generation will fail")
        app.state.llm_clients = []
    else:
        clients = []
        for config in providers:
            try:
                client = create_client(config)
                clients.append((client, config))
                logger.info(f"Initialized LLM: {config['provider']} ({config['model']})")
            except Exception as e:
                logger.error(f"Failed to initialize {config['provider']}: {e}")
        app.state.llm_clients = clients

    logger.info(f"Streaming: {'enabled' if settings.streaming_enabled else 'disabled'}")
    logger.info(f"Active prompt: {settings.active_prompt}")

    yield  # App runs here

    # Cleanup
    await app.state.http_client.aclose()
    logger.info("Shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Couch Traveller",
        description="AI-powered travel itinerary planner",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Routers
    app.include_router(api_router)

    return app


app = create_app()
