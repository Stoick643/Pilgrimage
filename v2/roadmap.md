# Couch Traveller V2 — Roadmap

## Architecture
- **Backend:** FastAPI (async)
- **Frontend:** htmx + Bootstrap 5 + minimal JS
- **LLM output:** Structured JSON (no `&&&` marker parsing)
- **Config:** Pydantic Settings
- **Streaming:** SSE by default via FastAPI `StreamingResponse`

## Phase 1: Backend ✅
- [x] `config.py` — Pydantic Settings class (all env vars, typed, validated at startup)
- [x] `services/llm.py` — LLM client, JSON mode, streaming, provider fallback chain
- [x] `services/images.py` — Unsplash image search (append country for disambiguation)
- [x] `services/weather.py` — OpenWeather 5-day forecast (async with httpx)
- [x] `services/geocoding.py` — Google geocoding (async, concurrent)
- [x] `prompts/detailed.txt` + `prompts/concise.txt` — prompt templates as files
- [x] `models.py` — Pydantic models for request/response validation
- [x] `app.py` — FastAPI app factory, lifespan for client init
- [x] `routers/api.py` — POST `/api/generate` (JSON), POST `/api/stream` (SSE), GET endpoints
- [x] Input validation with Pydantic models (country, duration, activities, language)
- [x] Auto-generated OpenAPI docs at `/docs`
- [x] 62 tests passing (config, LLM, images, weather, geocoding, API routes)
- [x] All V1 tests still pass (50 tests)

## Phase 2: Frontend ✅
- [x] `templates/base.html` — Bootstrap 5 + htmx 2.0 + SSE extension + icons
- [x] `templates/index.html` — form with htmx submit, activities checkboxes, language select
- [x] `templates/itinerary.html` — skeleton page with SSE connection
- [x] `templates/partials/day_card.html` — card with image overlay, morning/afternoon/evening, tip
- [x] `templates/partials/city_image.html` — image with gradient overlay + credit
- [x] `templates/partials/weather.html` — weather strip with icons
- [x] `routers/pages.py` — HTML page routes + SSE HTML streaming + htmx partials
- [x] SSE streams pre-rendered HTML day cards (server-side rendering, not client JSON parsing)
- [x] Lazy-load images/weather per card via htmx `hx-trigger="load"` (zero custom JS)
- [x] Google Maps route at bottom (loads after stream completes)
- [x] `static/css/styles.css` — card design, animations, responsive layout
- [x] Loading UX (htmx indicators, gradient placeholders, spinners)
- [x] 69 V2 tests + 50 V1 tests = 119 total passing

## Phase 3: Polish, Deploy & Retire V1
- [x] Error handling — custom 404/500 HTML pages
- [x] SQLite caching — itineraries (24h), images (7d), weather (3h), geocoding (forever)
- [x] Image dedup — different Unsplash pages per day number
- [x] CSS polish — bigger weather icons, progress bar, mobile responsive
- [x] `requirements.txt` — pinned V2 dependencies
- [x] `README.md` — setup, run, test, structure docs
- [x] 91 V2 tests + 50 V1 tests = 141 total passing
- [ ] Prompt versioning / A-B testing support
- [ ] Dockerfile / docker-compose
- [ ] Production config (uvicorn, CORS, rate limiting)
- [ ] Smoke test in production
- [ ] Delete V1 code, update root README.md

## Known V1 Bugs — Status in V2
- [x] `country.title()` — not used in V2 (Pydantic handles input as-is)
- [x] Same Unsplash photo when city repeats — page param varies per day
- [x] "Syracuse" → Syracuse, NY — country appended to image search
- [x] Weather icons too small — CSS fix, 50px
- [x] No visual separation between days — card-based layout
- [x] City name + photo layout — gradient overlay on image

## Design Decisions
- **JSON mode over text markers:** LLM returns `{"days": [{"city": "...", "title": "...", "activities": [...]}]}` — reliable, no parsing hacks
- **htmx over vanilla JS:** Declarative, SSE built-in, ~14KB, no build step
- **FastAPI over Flask:** Native async, Pydantic validation, auto OpenAPI docs, better SSE support
- **Prompt files over Python strings:** Easier to edit, version, A/B test
- **Services split into separate files:** Each integration testable in isolation
- **Image search includes country:** `"Syracuse Sicily"` not just `"Syracuse"`
