# Couch Traveller V2 — Roadmap

## Architecture
- **Backend:** FastAPI (async)
- **Frontend:** htmx + Bootstrap 5 + minimal JS
- **LLM output:** Structured JSON (no `&&&` marker parsing)
- **Config:** Pydantic Settings
- **Streaming:** SSE by default via FastAPI `StreamingResponse`

## Phase 1: Foundation
- [ ] `config.py` — Pydantic Settings class (all env vars, typed, validated at startup)
- [ ] `services/llm.py` — async LLM client, JSON mode, streaming, provider fallback chain
- [ ] `app.py` — FastAPI app factory, lifespan for client init
- [ ] `prompts/detailed.txt` + `prompts/concise.txt` — prompt templates as files
- [ ] Basic tests for config + LLM service

## Phase 2: Core API
- [ ] `routers/api.py` — POST `/api/generate` returns structured JSON itinerary
- [ ] `routers/api.py` — POST `/api/stream` returns SSE stream of JSON day blocks
- [ ] Input validation with Pydantic models (country, duration, activities, language)
- [ ] Tests for API endpoints

## Phase 3: Frontend
- [ ] `templates/base.html` — Bootstrap 5 + htmx + icons
- [ ] `templates/index.html` — form, htmx submit
- [ ] `templates/partials/day_card.html` — single day card (image overlay, weather, text)
- [ ] `templates/partials/weather.html` — weather strip
- [ ] `routers/pages.py` — HTML page routes
- [ ] SSE rendering via htmx `hx-ext="sse"` (text streams in, cards build incrementally)
- [ ] `static/css/styles.css` — card design, image overlays, responsive layout

## Phase 4: Integrations (port from V1)
- [ ] `services/images.py` — Unsplash image search (append country to query for disambiguation)
- [ ] `services/weather.py` — OpenWeather 5-day forecast
- [ ] `services/geocoding.py` — Google geocoding
- [ ] Lazy-load images/weather per card via htmx (no custom JS)
- [ ] Google Maps route at bottom
- [ ] Tests for all services

## Phase 5: Polish
- [ ] Error handling (422 validation, 500 pages, graceful API degradation)
- [ ] Caching layer (Redis or SQLite — keyed on country+duration+activities+language)
- [ ] Loading UX (htmx indicators, skeleton cards)
- [ ] Prompt versioning / A-B testing support
- [ ] Mobile responsive tweaks

## Phase 6: Deploy & Retire V1
- [ ] Dockerfile / docker-compose
- [ ] Production config (uvicorn, CORS, rate limiting)
- [ ] Migrate `.env` keys
- [ ] Smoke test in production
- [ ] Delete V1 code
- [ ] Update root README.md

## Known V1 Bugs to Fix in V2
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
