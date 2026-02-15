# Pilgrimage — AI Travel Itinerary Planner

Generate detailed day-by-day travel itineraries powered by AI, complete with city photos, weather forecasts, and interactive maps.

## Features

- 🗺️ AI-generated itineraries for any country or region
- 🌤️ 5-day weather forecasts per city (OpenWeatherMap)
- 📸 City photos from Unsplash (with personal photo fallbacks)
- 🗾 Interactive route map (Google Maps)
- 🌍 Multi-language support (translation via LLM)
- 🤖 Multiple LLM providers: DeepSeek, Moonshot, OpenAI

## Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd pilgrimage
python -m venv venv
source venv/Scripts/activate   # Windows (Git Bash)
source venv/bin/activate        # macOS / Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys. At minimum, one LLM key is required:

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | One of these | DeepSeek LLM (highest priority) |
| `MOONSHOT_API_KEY` | One of these | Moonshot LLM |
| `OPENAI_API_KEY` | One of these | OpenAI GPT-4o |
| `UNSPLASH_ACCESS_KEY` | Optional | City photos from Unsplash |
| `GOOGLE_DIRECTIONS_API_KEY` | Optional | Map geocoding & route display |
| `OPENWEATHERMAP_API_KEY` | Optional | 5-day weather forecasts |

### 4. Run the app

```bash
python -m flask run
```

Open http://127.0.0.1:5000 in your browser.

## Running Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
pilgrimage/
├── src/
│   ├── __init__.py      # Flask app factory
│   ├── routes.py        # Route handlers
│   ├── formatters.py    # Itinerary parsing & HTML formatting
│   ├── services.py      # LLM, images, weather, translation
│   └── maps.py          # City extraction & geocoding
├── tests/               # pytest test suite (39 tests)
├── templates/           # Jinja2 HTML templates
├── static/              # CSS, images
├── .env.example         # Environment variable template
├── .flaskenv            # Flask auto-configuration
├── requirements.txt     # Python dependencies
└── pyproject.toml       # Project metadata & tool config
```
