# Couch Traveller V2

AI-powered travel itinerary planner with streaming generation, city photos, weather forecasts, and route maps.

## Stack

- **Backend:** FastAPI (async) + Pydantic
- **Frontend:** htmx + Bootstrap 5 (minimal JS)
- **LLM:** DeepSeek / Moonshot / Anthropic (fallback chain, JSON mode)
- **APIs:** Unsplash (photos), OpenWeatherMap (weather), Google Maps (geocoding + routes)
- **Cache:** SQLite (itineraries 24h, images 7d, weather 3h, geocoding forever)
- **Streaming:** Server-Sent Events — day cards appear one-by-one as LLM generates

## Setup

```bash
cd pilgrimage
python -m venv venv
source venv/Scripts/activate   # Windows
pip install -r v2/requirements.txt

# Copy and fill in API keys
cp .env.example .env
```

## Run

```bash
python -m uvicorn v2.app:app --reload --port 8000
```

- **App:** http://127.0.0.1:8000
- **API docs (Swagger):** http://127.0.0.1:8000/docs

## Test

```bash
python -m pytest v2/tests/ -v
```

## Project Structure

```
v2/
├── app.py                  # FastAPI app, lifespan, error handlers
├── config.py               # Pydantic Settings (.env)
├── models.py               # Request/response Pydantic models
├── couch_traveller.db      # SQLite cache (auto-created)
├── requirements.txt
├── prompts/
│   ├── detailed.txt        # Rich itinerary prompt
│   └── concise.txt         # Short itinerary prompt
├── routers/
│   ├── api.py              # JSON API + SSE streaming
│   └── pages.py            # HTML pages + htmx partials
├── services/
│   ├── cache.py            # SQLite cache (key/value + TTL)
│   ├── llm.py              # LLM completion + streaming + JSON mode
│   ├── images.py           # Unsplash with country disambiguation
│   ├── weather.py          # OpenWeatherMap 5-day forecast
│   └── geocoding.py        # Google Maps geocoding
├── static/css/styles.css
├── templates/
│   ├── base.html           # Bootstrap + htmx
│   ├── index.html          # Form
│   ├── itinerary.html      # Streaming itinerary page
│   ├── error.html          # 404/500 error page
│   └── partials/
│       ├── day_card.html   # Single day card
│       ├── city_image.html # Image with overlay
│       └── weather.html    # Weather strip
└── tests/                  # 79+ tests
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate` | Full itinerary (JSON) |
| POST | `/api/stream` | Stream itinerary (SSE) |
| GET | `/api/city-image` | City photo + credit |
| GET | `/api/city-weather` | 5-day forecast |
| GET | `/api/geocode` | Geocode cities |

## Configuration (.env)

```
DEEPSEEK_API_KEY=...        # Required (at least one LLM key)
MOONSHOT_API_KEY=...        # Optional fallback
ANTHROPIC_API_KEY=...       # Optional fallback
UNSPLASH_ACCESS_KEY=...     # Optional (city photos)
OPENWEATHERMAP_API_KEY=...  # Optional (weather)
GOOGLE_DIRECTIONS_API_KEY=... # Optional (maps)
ACTIVE_PROMPT=detailed      # or "concise"
STREAMING_ENABLED=true
```
