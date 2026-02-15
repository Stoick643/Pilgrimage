"""Pages router — HTML page routes + SSE HTML streaming + htmx partials."""

import json
import logging
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from v2.config import settings
from v2.services.images import get_image_url
from v2.services.llm import build_prompt, llm_stream, parse_json_response
from v2.services.weather import get_forecast

logger = logging.getLogger(__name__)

V2_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(V2_DIR / "templates"))

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
        days_sent = 0
        try:
            async for chunk in llm_stream(
                clients=clients,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            ):
                full_text += chunk

                # Try to extract complete day objects as they stream in
                new_days = _extract_complete_days(full_text, days_sent)
                for day in new_days:
                    days_sent += 1
                    pct = min(90, int(days_sent / duration * 90))
                    yield f"event: progress\ndata: {pct}\n\n"

                    html = templates.get_template("partials/day_card.html").render(
                        day=day,
                        country=country,
                    )
                    sse_data = "\n".join(f"data: {line}" for line in html.split("\n"))
                    yield f"event: day\n{sse_data}\n\n"

            # After stream ends, check for any remaining days not yet sent
            remaining = _extract_complete_days(full_text, days_sent, final=True)
            for day in remaining:
                days_sent += 1
                html = templates.get_template("partials/day_card.html").render(
                    day=day,
                    country=country,
                )
                sse_data = "\n".join(f"data: {line}" for line in html.split("\n"))
                yield f"event: day\n{sse_data}\n\n"

            if days_sent == 0:
                # Nothing parsed — try full parse as fallback
                parsed = parse_json_response(full_text)
                if "error" in parsed:
                    yield f"event: day\ndata: <div class='alert alert-danger'>{parsed['error']}</div>\n\n"
                else:
                    for day in parsed.get("days", []):
                        html = templates.get_template("partials/day_card.html").render(
                            day=day, country=country,
                        )
                        sse_data = "\n".join(f"data: {line}" for line in html.split("\n"))
                        yield f"event: day\n{sse_data}\n\n"

            yield "event: complete\ndata: done\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"event: day\ndata: <div class='alert alert-danger'>Error: {str(e)}</div>\n\n"
            yield "event: complete\ndata: done\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _extract_complete_days(text: str, already_sent: int, final: bool = False) -> list[dict]:
    """Extract complete day JSON objects from a partial stream.

    Tracks brace depth to find complete {...} objects within the "days" array.
    Returns only new days (skipping already_sent ones).
    """
    days = []

    # Find the start of the days array
    days_start = text.find('"days"')
    if days_start == -1:
        return []

    bracket_pos = text.find('[', days_start)
    if bracket_pos == -1:
        return []

    # Walk through text finding complete day objects by brace matching
    pos = bracket_pos + 1
    while pos < len(text):
        # Skip whitespace and commas
        while pos < len(text) and text[pos] in ' \t\n\r,':
            pos += 1

        if pos >= len(text) or text[pos] == ']':
            break

        if text[pos] == '{':
            # Found start of an object — find its end by brace counting
            depth = 0
            start = pos
            in_string = False
            escape_next = False

            for i in range(start, len(text)):
                ch = text[i]
                if escape_next:
                    escape_next = False
                    continue
                if ch == '\\' and in_string:
                    escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        # Complete object found
                        obj_text = text[start:i + 1]
                        try:
                            day = json.loads(obj_text)
                            days.append(day)
                        except json.JSONDecodeError:
                            pass
                        pos = i + 1
                        break
            else:
                # Incomplete object — not enough text yet
                break
        else:
            pos += 1

    # Return only new days
    return days[already_sent:]


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
