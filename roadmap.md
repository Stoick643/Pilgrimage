# Pilgrimage - Project Roadmap

## Overview
Modernize, clean up, add features, and deploy the "Couch Traveller" itinerary planner.
Originally built on Replit (September 2024) with Flask + GPT-4o.

---

## V1: Flask App (Phase 1–2)

### Phase 1: 🧹 Clean Up ✅
*Foundation work — makes everything else easier.*

#### 1.1 Remove Replit Artifacts ✅
- [x] Delete `.replit` file
- [x] Remove hardcoded `replit.app` URL from `index.html` meta tags
- [x] Clean up `pyproject.toml` (remove Replit-specific config)

#### 1.2 Remove Dead Code ✅
- [x] Delete unused functions (`format_itinerary`, `format_itinerary_weather_V1`, `extract_special_lines`, `save_itinerary`, `extract_cities_gpt`, etc.)
- [x] Remove commented-out MongoDB/Redis initialization
- [x] Remove `main_mini.py`, `templates/index_orig.html`
- [x] Replace debug `print()` with proper `logging`

#### 1.3 Fix Bugs & Issues ✅
- [x] Fix `app.static_folder` config
- [x] Add error handling for missing env vars
- [x] Handle edge cases (empty activities, invalid country, duration=0)
- [x] Fix `get_image_url()` fallback when Unsplash key missing

#### 1.4 Project Structure ✅
- [x] `src/` package layout (`__init__.py`, `routes.py`, `services.py`, `maps.py`, `formatters.py`)
- [x] Virtual environment, `.flaskenv`, `.env.example`
- [x] Updated `requirements.txt`, `README.md`

#### 1.5 Test Cases ✅
- [x] pytest setup with mocks for all external APIs
- [x] Unit tests for parsing, formatting, image fetching, weather, geocoding
- [x] Integration tests for routes
- [x] 50 tests passing

### Phase 2: 🔧 Modernize (partial) ✅
- [x] Python 3.13, Bootstrap 5.3.3
- [x] Parallel API calls (weather, images, geocoding)
- [x] AJAX lazy loading — text first, photos/weather/map load after
- [x] SSE streaming (`/api/stream-itinerary`) with `&&&` marker parsing
- [x] LLM provider fallback chain (DeepSeek → Moonshot → Anthropic)
- [x] Prompt templates (concise/detailed) in `src/prompts.py`

---

## V2: FastAPI + JSON Mode ✅

### Architecture
- FastAPI (async), htmx + SSE extension, Pydantic Settings
- LLM returns structured JSON (`{"days": [{"city", "title", "morning", "afternoon", "evening", "tip"}]}`)
- Server-side rendered HTML day cards streamed via SSE
- SQLite caching (itineraries 24h, images 7d, weather 3h, geocoding forever)

### Completed
- [x] Full async backend (httpx, async LLM clients, provider fallback)
- [x] Pydantic models for request/response validation
- [x] htmx frontend with lazy-loaded partials (city images, weather)
- [x] SSE streams pre-rendered day cards (server parses JSON mid-stream)
- [x] Image dedup (different Unsplash pages per day), country disambiguation
- [x] Custom error pages (404, 500)
- [x] 91 V2 tests + 50 V1 tests = 141 total passing

### Known issues with V2 approach
- JSON streaming is fragile (brace-depth counting, partial parse recovery)
- htmx SSE fights character-level streaming control
- V1's word-by-word text flow felt more engaging than V2's card-popping

---

## V3: V1 Streaming Feel on V2 Backend (ACTIVE)

### Vision
Text flows word-by-word, photos pop in when `&&&` markers are detected.
Final result looks like V1 — text with photos on the side.
Powered by V2's FastAPI, async services, caching, and provider fallback chain.

### Architecture
- **Backend:** FastAPI (async) — carried over from V2
- **Frontend:** Vanilla JS + Bootstrap 5 (no htmx)
- **LLM output:** Raw text with `&&&` city markers (like V1, no JSON mode)
- **Streaming:** SSE via `StreamingResponse`, raw text chunks
- **Config:** Pydantic Settings (from V2)
- **Caching:** SQLite (from V2)

### V2 → V3 changes
| Area | V2 | V3 |
|---|---|---|
| LLM output format | Structured JSON | Raw text with `&&&` markers |
| LLM system prompt | "Always respond with valid JSON" | Standard travel assistant |
| OpenAI `response_format` | `{"type": "json_object"}` | Removed |
| Frontend framework | htmx + SSE extension | Vanilla JS + fetch SSE reader |
| Day rendering | Server-side HTML cards via SSE | Client-side: JS parses text, builds DOM |
| Photo/weather loading | htmx `hx-trigger="load"` partials | JS AJAX calls (like V1) |
| Non-streaming mode | Supported | Dropped — streaming only |
| `/api/generate` endpoint | Structured JSON (`DayPlan` model) | Simplified `{city, content}` list |
| Templates: partials | `day_card.html`, `city_image.html`, `weather.html` | Removed — all client-side |
| htmx dependency | Required | Removed |

### Unchanged from V2
- `config.py`, `app.py`, `services/cache.py`, `services/images.py`, `services/weather.py`, `services/geocoding.py`
- API endpoints: `/api/city-image`, `/api/city-weather`, `/api/geocode`

### Phase 1: LLM & Prompts ✅
- [x] `prompts/detailed.txt` — `&&&` marker format
- [x] `prompts/concise.txt` — `&&&` marker format
- [x] `services/llm.py` — Remove JSON mode, `llm_complete()` returns `str`, remove `parse_json_response()`, add `parse_marker_text()`

### Phase 2: Models & API ✅
- [x] `models.py` — Replace `DayPlan` with `DayEntry` (`{city, content}`), keep other models
- [x] `routers/api.py` — `/api/generate` parses `&&&` into list, `/api/stream` sends raw text
- [x] Remove non-streaming fallback logic

### Phase 3: Frontend & Templates ✅
- [x] `templates/base.html` — Remove htmx scripts
- [x] `templates/index.html` — Vanilla form submit (JS navigates to `/plan?...`)
- [x] `templates/itinerary.html` — Full rewrite: vanilla JS SSE, `&&&` detection, AJAX photos/weather, markdown rendering, auto-scroll, Google Maps on complete
- [x] Remove `templates/partials/` directory
- [x] `routers/pages.py` — Remove JSON parser, htmx partials; GET `/plan` passes stream config to template

### Phase 4: Cleanup & Tests ✅
- [x] Update tests for text-based format (84 V3 tests passing)
- [x] Remove obsolete tests (`_extract_complete_days`, `parse_json_response`)
- [x] Add `parse_marker_text` tests (6 test cases)
- [x] V1 (50) + V2 (91) + V3 (84) = 225 total tests passing
- [ ] Update `README.md`

### Phase 5: Map Enhancements ✅
*Map JS extracted to `v3/static/js/map.js`. All client-side, no backend changes.*

#### Quick wins ✅
- [x] Numbered markers (Day 1, 2, 3) with day title in info windows
- [x] Fit bounds — auto-zoom to show all markers
- [x] Satellite/terrain toggle (mapTypeControl)
- [x] Travel mode toggle (driving / transit / walking buttons)

#### Medium effort ✅
- [x] Distance & duration display (total trip stats under map)
- [x] Day-by-day distance breakdown table ("Rome → Florence: 3h, 275 km")
- [x] Click marker → scroll to day card (with highlight animation)
- [x] Click day card → bounce marker + pan map
- [x] Animated route reveal (markers drop one by one with 400ms delay)

#### Ambitious (selected) ✅
- [x] Street View thumbnails per city (with metadata check for coverage)
- [x] Embedded mini-maps per day card (Google Static Maps API)
- [ ] ~~Alternative routes~~ — dropped (medium effort, low value)

### Phase 6: Deployment ✅
- [x] Dockerfile (Python 3.12, uvicorn, V3 only)
- [x] fly.toml (Frankfurt region, volume mount for SQLite)
- [x] `CACHE_DB_PATH` env var for persistent `/data` volume
- [x] GitHub Actions CI/CD (auto-deploy on push to main)
- [x] Secrets via `fly secrets import`
- [x] Live at `pilgrimage.fly.dev`

### Phase 7: Polish ✅
- [x] Background photo (Mojca.jpg) on index page with frosted overlay (80% opacity)
- [x] Loading screen with rotating travel aphorisms + progress bar
- [x] Subtle warm gray background (`#fafaf8`)
- [x] Street View removed (boring, no value)
- [x] Side-by-side layout: city photo + mini map (`col-md-6` grid)
- [x] XSS sanitization (escapeHtml helper)
- [x] Mini-map match by index (not fragile name substring)
- [x] `var` → `const/let` in map.js
- [x] `onerror` fallback on mini-map images

### Phase 8: Export & Sharing (IN PROGRESS)
- [ ] 🖨️ Print to PDF (browser `window.print()` + `@media print` styles)
- [ ] 📋 Copy to clipboard (plain text)
- [ ] 🔗 Shareable link (`/trip/<uuid>` — save to SQLite, permanent URL)
- [ ] Social share buttons (WhatsApp, X/Twitter, Email — just links, no APIs)

### Design Decisions (V3)
- **`&&&` markers over JSON:** Streaming JSON needs brace-depth counting. `&&&` is a simple string match mid-stream.
- **Vanilla JS over htmx:** Character-level streaming needs fine-grained DOM control.
- **Drop non-streaming:** Streaming is the whole UX. One code path = less maintenance.
- **Keep `/api/generate`:** Cheap, useful for CLI/mobile/testing.
- **Keep V2 services:** Async backend is solid — no reason to touch it.
- **Map JS in separate file:** `static/js/map.js` — clean separation from template HTML, browser-cacheable.

---

## Future Phases
- [ ] Nearby POIs (Google Places API — restaurants, hotels, landmarks as toggleable markers)
- [ ] Draggable marker reorder (drag pins to rearrange route + itinerary)
- [ ] Prompt versioning / A-B testing
- [ ] Production hardening (CORS, rate limiting)
- [ ] User accounts & saved itineraries
- [ ] Budget estimator, hotel/restaurant suggestions

---

## Status
- **Active:** V3 Phase 8 — Export & Sharing
- **Last Updated:** 2026-02-16
