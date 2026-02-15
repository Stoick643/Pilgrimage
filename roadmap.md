# Pilgrimage - Project Roadmap

## Overview
Modernize, clean up, add features, and deploy the "Couch Traveller" itinerary planner.
Originally built on Replit (September 2024) with Flask + GPT-4o.

---

## Phase 1: 🧹 Clean Up
*Foundation work — makes everything else easier.*

### 1.1 Remove Replit Artifacts
- [ ] Delete `.replit` file
- [ ] Remove hardcoded `replit.app` URL from `index.html` meta tags
- [ ] Clean up `pyproject.toml` (remove Replit-specific config)

### 1.2 Remove Dead Code
- [ ] Remove unused `format_itinerary()` function (replaced by `format_itinerary_weather()`)
- [ ] Remove unused `format_itinerary_weather_V1()` function
- [ ] Remove unused `extract_special_lines()` and `extract_special_lines_as_map()` functions
- [ ] Remove unused `save_itinerary()` function
- [ ] Remove commented-out MongoDB initialization in `initialize_extensions()`
- [ ] Remove commented-out Redis setup
- [ ] Remove unused `initialize_extensions_etc()` function
- [ ] Remove unused `extract_cities_gpt()` function in `maps.py`
- [ ] Remove `main_mini.py` if obsolete
- [ ] Remove `templates/index_orig.html` if obsolete
- [ ] Clean up debug `print()` statements — replace with proper `logging`

### 1.3 Fix Bugs & Issues
- [ ] Fix `app.static_folder` config (`configure_app()` is defined but never called)
- [ ] Ensure `static/` folder is served correctly (CSS, images)
- [ ] Add error handling for missing environment variables
- [ ] Handle edge cases: empty activities list, invalid country, duration=0
- [ ] Fix `get_image_url()` — returns `None` if Unsplash key is missing (no fallback)

### 1.4 Project Structure
- [ ] Create virtual environment (`venv`) — isolate from global packages
- [ ] Restructure into `src/` package layout:
  - [ ] `src/__init__.py` — Flask app factory
  - [ ] `src/routes.py` — route handlers
  - [ ] `src/services.py` — business logic
  - [ ] `src/maps.py` — maps/geocoding
  - [ ] Remove all `.py` files from root
- [ ] Add `.env.example` with all required env variables documented
- [ ] Add proper `python-dotenv` loading in app startup
- [ ] Update `requirements.txt` to match actual dependencies (remove `pymongo`, `gunicorn` if unused)
- [ ] Add/update `README.md` with setup instructions
- [ ] Organize imports consistently across all files

### 1.5 Test Cases
- [ ] Set up `pytest` as test runner
- [ ] Review and fix existing tests (`tests/test_main.py`, `tests/test_maps.py`, `tests/test_image_fetcher.py`)
- [ ] Add unit tests:
  - [ ] `extract_text_with_cities()` — parsing `&&&` markers
  - [ ] `extract_cities()` — city extraction from text
  - [ ] `weather_html()` — HTML generation, error handling
  - [ ] `format_itinerary_weather()` — end-to-end formatting
  - [ ] `translate_itinerary()` — passthrough for English, API call for others
  - [ ] `get_image_url()` — Unsplash, fallback to hardcoded, error cases
  - [ ] `get_weather_forecast()` — valid data, out-of-range dates, API errors
  - [ ] `geocode_location()` — valid city, invalid city, API errors
- [ ] Add integration tests:
  - [ ] `GET /` returns index page
  - [ ] `POST /generate-itinerary` with valid input
  - [ ] `POST /generate-itinerary` with missing/invalid input
- [ ] Add mocks for external APIs (OpenAI, Unsplash, Google Maps, OpenWeatherMap)
- [ ] Add test configuration (separate from production env)

---

## Phase 2: 🔧 Modernize
*Upgrade tech and improve architecture.*

### 2.1 Python & Dependencies
- [ ] Upgrade to Python 3.12+
- [ ] Migrate from `poetry` to modern `pyproject.toml` with `pip`
- [ ] Pin dependency versions properly

### 2.2 Code Architecture
- [ ] Replace raw HTML string building in `main.py` with Jinja2 template logic
- [ ] Move itinerary formatting into templates (partial templates per day)
- [ ] Separate concerns: routes, services, formatters into clean modules
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
- **Current Phase:** Phase 1 — Clean Up
- **Last Updated:** 2026-02-15
