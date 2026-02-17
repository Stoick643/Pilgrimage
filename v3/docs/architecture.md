# V3 Architecture — How It Works

## Overview

Couch Traveller V3 is an AI travel planner that **streams** itineraries word-by-word.
The user sees text appearing in real time, with photos, weather, and maps loading alongside.

Stack: **FastAPI** (async Python) → **SSE** (Server-Sent Events) → **Vanilla JS** (no frameworks).

---

## 1. Streaming: From LLM to Browser

### The flow

```
Browser                          Server (FastAPI)                LLM (DeepSeek)
   │                                │                                │
   │  POST /api/stream              │                                │
   │  {country:"Sicily", days:5}    │                                │
   │ ──────────────────────────►    │                                │
   │                                │  "Generate 5-day Sicily..."    │
   │                                │ ──────────────────────────►    │
   │                                │                                │
   │                                │   chunk: "&&& Pal"             │
   │                                │ ◄─────────────────             │
   │  data: {"text":"&&& Pal"}      │                                │
   │ ◄─────────────────────────     │   chunk: "ermo\n"              │
   │                                │ ◄─────────────────             │
   │  data: {"text":"ermo\n"}       │                                │
   │ ◄─────────────────────────     │         ...                    │
   │         ...                    │                                │
   │                                │   (LLM done)                   │
   │  data: {"done":true}           │                                │
   │ ◄─────────────────────────     │                                │
```

### The problem: random chunk boundaries

The LLM doesn't send neat lines — it sends word fragments. `"&&& Palermo"` might arrive as:

```
chunk 1: "&&& Pal"
chunk 2: "ermo\n### Da"
chunk 3: "y 1: Explori"
chunk 4: "ng Palermo\n- Visit"
```

### The solution: lineBuffer

A string buffer reassembles random chunks into complete lines.
Only complete lines (ending with `\n`) get processed:

```
chunk 1 arrives: "&&& Pal"
  lineBuffer = "&&& Pal"
  No \n found → wait

chunk 2 arrives: "ermo\n### Da"
  lineBuffer = "&&& Palermo\n### Da"
  Found \n! Split:
    → processLine("&&& Palermo")   ← creates day card, fires AJAX
    lineBuffer = "### Da"           ← leftover, wait for more

chunk 3 arrives: "y 1: Explori"
  lineBuffer = "### Day 1: Explori"
  No \n → wait

chunk 4 arrives: "ng Palermo\n- Visit"
  lineBuffer = "### Day 1: Exploring Palermo\n- Visit"
  Found \n! Split:
    → processLine("### Day 1: Exploring Palermo")  ← renders <h3>
    lineBuffer = "- Visit"
```

### processLine() — line type detection

Each complete line is classified by its first characters:

```
"&&& Palermo"              → new day card + fire photo/weather AJAX
"### Day 1: ..."           → render <h3>
"- Visit the cathedral"    → render <li>
"Any other text"           → render <p>
```

**Key files:** `v3/templates/itinerary.html` (JS), `v3/routers/api.py` (`stream_itinerary`)

---

## 2. Stream Caching

### Why?

LLM calls take 10–20 seconds and cost money. If someone requests the same trip twice, we serve it instantly from cache.

### How it works

```
User requests "Sicily, 5 days, food+history, English"
        │
        ▼
  Cache key = "stream:sicily:5:food,history:en:detailed"
        │
        ├── Cache HIT?  → Stream cached text line-by-line (instant, no LLM)
        │
        └── Cache MISS? → Stream from LLM chunk-by-chunk
                          │
                          └── Accumulate all chunks into `full_text`
                              │
                              └── When done → save to SQLite (TTL: 24 hours)
```

The cache key includes: country, duration, activities (sorted), language, and prompt version.
Same inputs = same cache key = instant replay.

**Key file:** `v3/routers/api.py` → `stream_itinerary()`

---

## 3. Photo Deduplication for Repeat Cities

### The problem

A 5-day trip might have 2 days in Rome. Without dedup, both days show the same Colosseum photo.

### The solution: page counter

```
Stream text:       "&&& Rome"    (day 1)
                   "&&& Rome"    (day 2)
                   "&&& Florence" (day 3)

cityCount tracks:   Rome → 1      Rome → 2      Florence → 1
                      │              │               │
                      ▼              ▼               ▼
API call:    /api/city-image       /api/city-image   /api/city-image
             ?city=Rome            ?city=Rome         ?city=Florence
             &page=1               &page=2            &page=1
                │                     │                  │
                ▼                     ▼                  ▼
Unsplash:    page 1 results       page 2 results     page 1 results
             (Colosseum)          (Trevi Fountain)   (Duomo)
```

Each day card stores `data-page="N"`, so when the photo loads it updates only the correct card.

Image cache key is `"city:page"` (e.g. `"Rome:1"`, `"Rome:2"`).
Weather cache key is just `"city"` — same city = same weather.

**Key files:** `v3/templates/itinerary.html` (JS `fireCityAjax`), `v3/routers/api.py` (`city_image`)

---

## 4. fullStreamText → Share Button

### The problem

After streaming finishes, the user might want to share the trip. But the streamed text lives in DOM elements, not as a clean string.

### The solution: silent accumulator

```
LLM streams chunks → appendStreamText() writes to TWO places:

  1. lineBuffer   → processed line-by-line → builds visible DOM
  2. fullStreamText → just accumulates silently (a plain string)

                    ... streaming finishes ...

User clicks "Share":
        │
        ▼
  POST /api/share { content: fullStreamText, country: "Sicily", ... }
        │
        ▼
  Server generates UUID, saves to SQLite `shared_trips` table
        │
        ▼
  Returns: { id: "8fe47bcf43e8", url: "/trip/8fe47bcf43e8" }
        │
        ▼
  JS shows shareable URL + social buttons (WhatsApp, X, Email)
```

`fullStreamText` is never displayed — it's a hidden copy of the raw stream, preserved exactly as the LLM produced it (including `&&&` markers). This means the shared trip page can re-render it identically.

**Key files:** `v3/templates/itinerary.html` (JS), `v3/routers/api.py` (`share_itinerary`), `v3/services/cache.py` (`save_shared_trip`)

---

## 5. Why `&&&` Markers?

V2 used JSON mode — the LLM returned structured JSON. This required:
- `response_format: {"type": "json_object"}` (OpenAI-specific)
- Brace-depth counting to detect complete JSON objects mid-stream
- Partial parse recovery when chunks split a JSON key

V3 uses `&&&` markers — the LLM writes plain text with `&&& CityName` on a line by itself before each day's content:

```
&&& Rome
### Day 1: Ancient Rome
- Morning: Visit the Colosseum
- Afternoon: Roman Forum

&&& Florence
### Day 2: Renaissance Art
- Morning: Uffizi Gallery
```

Detection is trivial: `if (line.startsWith('&&&'))`. No parsing library, no depth counting, no recovery logic.

**Trade-off:** Less structured (no guaranteed fields like "morning", "afternoon"). But for streaming text, simplicity wins.

---

## 6. Data Flow Summary

```
User fills form (index.html)
    │
    ▼
GET /plan?country=Sicily&duration=5&...
    │
    ▼
Server renders itinerary.html with stream config
    │
    ▼
Browser JS calls POST /api/stream
    │
    ├── Cache hit? → replay cached text
    └── Cache miss? → stream from LLM → save to cache
            │
            ▼
    SSE chunks arrive → lineBuffer reassembles lines
            │
            ▼
    processLine() detects:
        &&& marker → new day card + AJAX photo + AJAX weather
        ### heading → <h3>
        - bullet   → <li>
        other text → <p>
            │
            ▼
    Stream ends → show map section → Google Maps loads
        → geocode cities → draw route → numbered markers
        → add mini static maps to each day card
            │
            ▼
    User can: Print / Copy / Share
        → Share saves fullStreamText to SQLite
        → Returns /trip/{uuid} shareable link
```
