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

## Phase 2: Frontend
- [ ] `templates/base.html` — Bootstrap 5 + htmx + icons
- [ ] `templates/index.html` — form, htmx submit
- [ ] `templates/partials/day_card.html` — card with image overlay, weather, text
- [ ] `templates/partials/weather.html` — weather strip
- [ ] `routers/pages.py` — HTML page routes
- [ ] SSE rendering via htmx `hx-ext="sse"` (cards build incrementally)
- [ ] Lazy-load images/weather per card via htmx (no custom JS)
- [ ] Google Maps route at bottom
- [ ] `static/css/styles.css` — card design, responsive layout
- [ ] Loading UX (htmx indicators, skeleton cards)

## Phase 3: Polish, Deploy & Retire V1
- [ ] Error handling (422 validation, 500 pages, graceful API degradation)
- [ ] Caching layer (Redis or SQLite — keyed on country+duration+activities+language)
- [ ] Prompt versioning / A-B testing support
- [ ] Dockerfile / docker-compose
- [ ] Production config (uvicorn, CORS, rate limiting)
- [ ] Smoke test in production
- [ ] Delete V1 code, update root README.md

## Known V1 Bugs to Fix
- [ ] `country.title()` breaks multi-word countries ("Bosnia And Herzegovina")
- [ ] Same Unsplash photo when city repeats across days (need variation/offset)
- [ ] "Syracuse" returns Syracuse, NY — append country to image search
- [ ] Weather icons too small
- [ ] No visual separation between days (needs cards)
- [ ] City name + photo layout awkward (use overlay or full-width image)

## Design Decisions
- **JSON mode over text markers:** LLM returns `{"days": [{"city": "...", "title": "...", "activities": [...]}]}` — reliable, no parsing hacks
- **htmx over vanilla JS:** Declarative, SSE built-in, ~14KB, no build step
- **FastAPI over Flask:** Native async, Pydantic validation, auto OpenAPI docs, better SSE support
- **Prompt files over Python strings:** Easier to edit, version, A/B test
- **Services split into separate files:** Each integration testable in isolation
- **Image search includes country:** `"Syracuse Sicily"` not just `"Syracuse"`
