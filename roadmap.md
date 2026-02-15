# Pilgrimage - Project Roadmap

## Overview
Modernize, clean up, add features, and deploy the "Couch Traveller" itinerary planner.
Originally built on Replit (September 2024) with Flask + GPT-4o.

---

## Phase 1: 🧹 Clean Up
*Foundation work — makes everything else easier.*

### 1.1 Remove Replit Artifacts ✅
- [x] Delete `.replit` file
- [x] Remove hardcoded `replit.app` URL from `index.html` meta tags
- [x] Clean up `pyproject.toml` (remove Replit-specific config)

### 1.2 Remove Dead Code ✅
- [x] Remove unused `format_itinerary()` function (replaced by `format_itinerary_weather()`)
- [x] Remove unused `format_itinerary_weather_V1()` function
- [x] Remove unused `extract_special_lines()` and `extract_special_lines_as_map()` functions
- [x] Remove unused `save_itinerary()` function
- [x] Remove commented-out MongoDB initialization in `initialize_extensions()`
- [x] Remove commented-out Redis setup
- [x] Remove unused `initialize_extensions_etc()` function
- [x] Remove unused `extract_cities_gpt()` function in `maps.py`
- [x] Remove `main_mini.py` if obsolete
- [x] Remove `templates/index_orig.html` if obsolete
- [x] Clean up debug `print()` statements — replace with proper `logging`

### 1.3 Fix Bugs & Issues ✅
- [x] Fix `app.static_folder` config (`configure_app()` is defined but never called)
- [x] Ensure `static/` folder is served correctly (CSS, images)
- [x] Add error handling for missing environment variables
- [x] Handle edge cases: empty activities list, invalid country, duration=0
- [x] Fix `get_image_url()` — returns `None` if Unsplash key is missing (no fallback)

### 1.4 Project Structure ✅
- [x] Create virtual environment (`venv`) — isolate from global packages
- [x] Restructure into `src/` package layout:
  - [x] `src/__init__.py` — Flask app factory
  - [x] `src/routes.py` — route handlers
  - [x] `src/services.py` — business logic
  - [x] `src/maps.py` — maps/geocoding
  - [x] `src/formatters.py` — itinerary parsing & HTML formatting
  - [x] Remove all `.py` files from root
- [x] Add `.flaskenv` for automatic Flask app discovery
- [x] Add `.env.example` with all required env variables documented
- [x] Add proper `python-dotenv` loading in app startup
- [x] Update `requirements.txt` to match actual dependencies (remove `pymongo`, `gunicorn` if unused)
- [x] Add/update `README.md` with setup instructions
- [x] Organize imports consistently across all files

### 1.5 Test Cases ✅
- [x] Set up `pytest` as test runner
- [x] Review and fix existing tests (`tests/test_main.py`, `tests/test_maps.py`, `tests/test_image_fetcher.py`)
- [x] Add unit tests:
  - [x] `extract_text_with_cities()` — parsing `&&&` markers
  - [x] `extract_cities()` — city extraction from text
  - [x] `weather_html()` — HTML generation, error handling
  - [x] `format_itinerary_weather()` — end-to-end formatting
  - [x] `translate_itinerary()` — passthrough for English, API call for others
  - [x] `get_image_url()` — Unsplash, fallback to hardcoded, error cases
  - [x] `get_weather_forecast()` — valid data, out-of-range dates, API errors
  - [x] `geocode_location()` — valid city, invalid city, API errors
- [x] Add integration tests:
  - [x] `GET /` returns index page
  - [ ] `POST /generate-itinerary` with valid input
  - [x] `POST /generate-itinerary` with missing/invalid input
- [x] Add mocks for external APIs (OpenAI, Unsplash, Google Maps, OpenWeatherMap)
- [x] Add test configuration (separate from production env)

---

## Phase 2: 🔧 Modernize
*Upgrade tech and improve architecture.*

### 2.1 Python & Dependencies
- [x] Upgrade to Python 3.12+ (using 3.13)
- [x] Migrate from `poetry` to modern `pyproject.toml` with `pip`
- [ ] Pin dependency versions properly

### 2.2 Code Architecture
- [ ] Replace raw HTML string building in `formatters.py` with Jinja2 template logic
- [ ] Move itinerary formatting into templates (partial templates per day)
- [x] Separate concerns: routes, services, formatters into clean modules
- [ ] Add type hints throughout

### 2.3 Performance
- [ ] Parallelize API calls (weather, images, geocoding are independent per city)
- [ ] Add caching layer for repeated city lookups (images, geocoding, weather)

### 2.4 Frontend
- [ ] Update Bootstrap to latest version
- [ ] Improve responsive design / mobile experience
- [ ] Add loading progress indicators (streaming results)
- [ ] Modernize UI/UX

### 2.5 Error Handling
- [ ] Proper Flask error pages (404, 500)
- [ ] Graceful degradation when APIs fail
- [ ] Input validation (server-side + client-side)

---

## Phase 3: ✨ Add Features
*New functionality.*

- [ ] User accounts & saved itineraries (with database)
- [ ] Multiple AI model options (GPT-4o, Claude, local models)
- [ ] Interactive map — drag & reorder stops
- [ ] Export itinerary as PDF
- [ ] Share itinerary via link
- [ ] More activity types & customization options
- [ ] Better language support (auto-detect, more languages)
- [ ] Day-by-day budget estimator
- [ ] Hotel / restaurant suggestions per city
- [ ] Packing list generator based on weather + activities

---

## Phase 4: 🚀 Deploy
*Get it live.*

- [ ] Dockerize the application (`Dockerfile` + `docker-compose.yml`)
- [ ] Choose hosting platform (Railway / Fly.io / Azure / Vercel)
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Environment variable management (secrets)
- [ ] Domain name & SSL
- [ ] Monitoring & logging (production-grade)
- [ ] Rate limiting for API calls

---

## Status
- **Current Phase:** Phase 1 nearly complete (README remaining), ready for Phase 2
- **Last Updated:** 2026-02-15
