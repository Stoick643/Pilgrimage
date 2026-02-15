"""LLM prompt templates for itinerary generation."""

# Concise prompt — faster, shorter output
PROMPT_CONCISE = """Generate a {duration}-day itinerary for {country}. Include {activities}. Be concise: 3-4 bullet points per day.

If not a real place, respond with: Error: [reason]

Format EXACTLY like this for each day:
&&& CityName
### Day 1: Title
- Morning: activity
- Afternoon: activity
- Evening: activity
{language_instruction}"""

SYSTEM_CONCISE = "You are a concise travel planner. Give practical, brief recommendations."

# Detailed prompt — richer output, takes longer
PROMPT_DETAILED = """1. Generate a detailed {duration}-day day-by-day itinerary for visiting {country}. The itinerary should include a mix of popular landmarks and {activities}. The itinerary should balance exploration and relaxation each day.

2. If the destination is clearly not a real place, return an error message beginning with Error. Accept reasonable variations of place names (e.g. misspellings, lowercase).

3. Format each day's details using the special text `&&&` in a dedicated line before the header, as shown below. After special text add the main city (or geographic location) for that day, ensuring only one city is used. If no city is available, use an appropriate geographic location. Example if Paris is in that day's itinerary:
&&& Paris
### Day X: [Title]
{language_instruction}"""

SYSTEM_DETAILED = "You are a helpful travel assistant."

# Active prompt — change this to switch
ACTIVE_PROMPT = "concise"  # "concise" or "detailed"
