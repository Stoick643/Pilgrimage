"""FastAPI application — Couch Traveller V2."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

V2_DIR = Path(__file__).parent

from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from v2.config import settings
from v2.routers.api import router as api_router
from v2.routers.pages import router as pages_router

error_templates = Jinja2Templates(directory=str(V2_DIR / "templates"))
from v2.services.cache import Cache
from v2.services.llm import create_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LLM clients and shared HTTP client at startup."""
    # Shared HTTP client for all services (connection pooling)
    app.state.http_client = httpx.AsyncClient(timeout=15.0)

    # SQLite cache
    app.state.cache = Cache()
    app.state.cache.clear_expired()

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

    # Static files
    app.mount("/static", StaticFiles(directory=str(V2_DIR / "static")), name="static")

    # Routers
    app.include_router(api_router)
    app.include_router(pages_router)

    # Error handlers
    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        return error_templates.TemplateResponse(request, "error.html", {
            "status_code": 404,
            "title": "Page Not Found",
            "message": "The page you're looking for doesn't exist.",
        }, status_code=404)

    @app.exception_handler(500)
    async def server_error(request: Request, exc):
        return error_templates.TemplateResponse(request, "error.html", {
            "status_code": 500,
            "title": "Something Went Wrong",
            "message": "We hit a snag. Please try again.",
        }, status_code=500)

    return app


app = create_app()
