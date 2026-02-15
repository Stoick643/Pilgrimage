"""Pages router — HTML page routes + SSE HTML streaming + htmx partials."""

import json
import logging
import uuid

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from v2.config import settings
from v2.services.images import get_image_url
from v2.services.llm import build_prompt, llm_stream
from v2.services.weather import get_forecast

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="v2/templates")

router = APIRouter(tags=["pages"])

# In-memory store for pending stream requests
_pending_requests: dict[str, dict] = {}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.post("/plan", response_class=HTMLResponse)
async def plan(
    request: Request,
    country: str = Form(...),
    duration: int = Form(...),
    activities: list[str] = Form(default=[]),
    language: str = Form(default="en"),
):
    """Accept form, store params, return itinerary skeleton with SSE connection."""
    # Validate
    if not country.strip():
        return templates.TemplateResponse(request, "index.html", {
            "error": "Please enter a country or region.",
        }, status_code=400)
    if duration < 1 or duration > 30:
        return templates.TemplateResponse(request, "index.html", {
            "error": "Duration must be between 1 and 30 days.",
        }, status_code=400)

    # Store request params for the SSE endpoint
    request_id = str(uuid.uuid4())[:8]
    _pending_requests[request_id] = {
        "country": country.strip(),
        "duration": duration,
        "activities": activities,
        "language": language,
    }

    return templates.TemplateResponse(request, "itinerary.html", {
        "request_id": request_id,
        "country": country.strip(),
        "duration": duration,
        "google_api_key": settings.google_directions_api_key or "",
    })


@router.get("/api/stream-html/{request_id}")
async def stream_html(request_id: str, request: Request):
    """Stream rendered day cards as SSE events (consumed by htmx sse extension)."""
    params = _pending_requests.pop(request_id, None)
    if not params:
        return HTMLResponse("Invalid or expired request", status_code=404)

    clients = getattr(request.app.state, "llm_clients", [])
    if not clients:
        return HTMLResponse("No LLM configured", status_code=500)

    country = params["country"]
    duration = params["duration"]
    activities_text = ", ".join(params["activities"]) if params["activities"] else "general sightseeing"

    system_prompt, user_prompt, max_tokens = build_prompt(
        active_prompt=settings.active_prompt,
        duration=duration,
        country=country,
        activities=activities_text,
        language=params["language"],
    )

    async def generate():
        full_text = ""
        char_count = 0
        try:
            async for chunk in llm_stream(
                clients=clients,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            ):
                full_text += chunk
                char_count += len(chunk)
                # Send progress updates every ~200 chars so user sees activity
                if char_count % 200 < len(chunk):
                    pct = min(90, char_count // 20)
                    yield f"event: progress\ndata: {pct}\n\n"

            # Parse the accumulated JSON
            parsed = _parse_streamed_json(full_text)
            if "error" in parsed:
                yield f"event: day\ndata: <div class='alert alert-danger'>{parsed['error']}</div>\n\n"
                yield "event: complete\ndata: \n\n"
                return

            # Render each day as an HTML card
            for day in parsed.get("days", []):
                html = templates.get_template("partials/day_card.html").render(
                    day=day,
                    country=country,
                )
                # SSE multi-line: each line needs "data: " prefix
                sse_data = "\n".join(f"data: {line}" for line in html.split("\n"))
                yield f"event: day\n{sse_data}\n\n"

            yield "event: complete\ndata: done\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"event: day\ndata: <div class='alert alert-danger'>Error: {str(e)}</div>\n\n"
            yield "event: complete\ndata: \n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _parse_streamed_json(text: str) -> dict:
    """Parse LLM JSON response, handling code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw text: {text[:500]}")
        return {"error": "Failed to parse itinerary. Please try again."}


# --- htmx partial endpoints (lazy-loaded by day cards) ---

@router.get("/partials/city-image", response_class=HTMLResponse)
async def partial_city_image(request: Request, city: str, country: str = ""):
    """Return rendered city image HTML (called by htmx hx-get on each card)."""
    http_client = getattr(request.app.state, "http_client", None)
    image_url, credit = await get_image_url(
        city=city.strip(),
        country=country or None,
        unsplash_key=settings.unsplash_access_key,
        http_client=http_client,
    )
    return templates.TemplateResponse(request, "partials/city_image.html", {
        "city": city,
        "image_url": image_url,
        "credit": credit,
    })


@router.get("/partials/weather", response_class=HTMLResponse)
async def partial_weather(request: Request, city: str):
    """Return rendered weather HTML (called by htmx hx-get on each card)."""
    http_client = getattr(request.app.state, "http_client", None)
    forecast = await get_forecast(
        city=city.strip(),
        api_key=settings.openweathermap_api_key,
        http_client=http_client,
    )
    return templates.TemplateResponse(request, "partials/weather.html", {
        "forecast": forecast,
    })
