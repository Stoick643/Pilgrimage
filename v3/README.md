# Couch Traveller V3

AI-powered travel itinerary planner with real-time streaming, city photos, weather forecasts, and route maps.

## Stack

- **Backend:** FastAPI (async) + Pydantic Settings
- **Frontend:** Vanilla JS + Bootstrap 5 (no htmx)
- **LLM:** DeepSeek / Moonshot / Anthropic (fallback chain, `&&&` marker format)
- **Streaming:** Server-Sent Events — text flows word-by-word, photos pop in per city
- **APIs:** Unsplash (photos), OpenWeatherMap (weather), Google Maps (geocoding + routes)
- **Cache:** SQLite (streams 24h, images 7d, weather 3h, geocoding forever)

## Setup

```bash
cd pilgrimage
python -m venv venv
source venv/Scripts/activate   # Windows
pip install -r v3/requirements.txt

# Copy and fill in API keys
cp .env.example .env
```

## Run

```bash
python -m uvicorn v3.app:app --reload --port 8000
```

Open http://localhost:8000

## Test

```bash
# V3 tests only
python -m pytest v3/tests/ -v

# All versions
python -m pytest tests/ v2/tests/ v3/tests/ -v
```

## Project Structure

```
v3/
├── app.py                  # FastAPI app factory + lifespan
├── config.py               # Pydantic Settings (env vars)
├── models.py               # Request/response models (DayEntry, ImageResponse, etc.)
├── prompts/
│   ├── concise.txt         # Short itinerary prompt (&&& markers)
│   └── detailed.txt        # Detailed itinerary prompt (&&& markers)
├── routers/
│   ├── api.py              # JSON + SSE endpoints (/api/generate, /api/stream, /api/city-image, etc.)
│   └── pages.py            # HTML pages (/, /plan)
├── services/
│   ├── cache.py            # SQLite cache
│   ├── geocoding.py        # Google geocoding (async)
│   ├── images.py           # Unsplash + personal photos (async)
│   ├── llm.py              # LLM completion, streaming, &&& parsing
│   └── weather.py          # OpenWeather forecast (async)
├── static/
│   └── css/styles.css      # Styles
├── templates/
│   ├── base.html           # Base layout (Bootstrap 5, no htmx)
│   ├── error.html          # Error pages (404, 500)
│   ├── index.html          # Form page
│   └── itinerary.html      # Streaming itinerary (vanilla JS SSE)
└── tests/                  # 84 tests
```

## How It Works

1. User fills in form → JS navigates to `/plan?country=...&duration=...`
2. Itinerary page loads → JS calls `POST /api/stream` with SSE
3. LLM streams text with `&&&` city markers → JS renders line by line
4. When `&&&` detected → AJAX fires for city photo + weather
5. On stream complete → Google Maps route loads

## V3 vs V2

| Area | V2 | V3 |
|---|---|---|
| LLM output | Structured JSON | Raw text with `&&&` markers |
| Frontend | htmx + SSE extension | Vanilla JS |
| Streaming cache | Not cached | Cached (24h) |
| Non-streaming | Supported | Dropped |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/generate` | Generate itinerary (JSON response) |
| POST | `/api/stream` | Stream itinerary (SSE, cache-aware) |
| GET | `/api/city-image?city=...&country=...` | City photo |
| GET | `/api/city-weather?city=...` | 5-day forecast |
| GET | `/api/geocode?cities=...` | Geocode cities |

## Environment Variables

See `.env.example` for all options. At minimum, set one LLM key:

```
DEEPSEEK_API_KEY=...     # or
MOONSHOT_API_KEY=...     # or
ANTHROPIC_API_KEY=...
```
