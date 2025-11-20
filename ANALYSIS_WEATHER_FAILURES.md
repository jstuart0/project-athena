# Weather Query Failure Analysis
**Date:** 2025-11-19
**Test Run:** test_results_1000_20251119_100950.json
**Weather Failure Rate:** 11/29 (37.9%)

## Summary

Weather queries had the highest failure rate (37.9%) in the 1000-question test. Analysis reveals three distinct root causes that need to be addressed.

## Issue 1: Wrong City Extraction ✅ FIXED

**Problem:** Weather queries for specific cities returned Baltimore weather instead.

**Examples:**
- "What's the weather in Chicago?" → Baltimore weather
- "What's the weather in Seattle?" → Baltimore weather
- "What's the weather in Denver?" → Baltimore weather
- "What's the weather in San Francisco?" → Baltimore weather
- "What's the weather in Dallas?" → Baltimore weather

**Root Cause:** Entity extraction regex in `intent_classifier.py` required capital letters (`r'in\s+([A-Z][a-z]+...)'`), but queries are lowercased before extraction.

**Fix Applied:**
- Updated regex to work with lowercase: `r'in\s+([a-z]+(?:\s+[a-z]+)?(?:\s+[a-z]+)?)'`
- Added title-casing to capitalize extracted city names
- Added entity extraction to simplified LLM mode and JSON parsing fallback
- Deployed to Mac Studio and verified working for Chicago, Seattle, Denver, Los Angeles

**Status:** ✅ FIXED - Verified working 2025-11-19

**Files Modified:**
- `src/orchestrator/intent_classifier.py` (lines 417-424)
- `src/orchestrator/main.py` (lines 384-413, 476, 535, 548)

---

## Issue 2: Wrong Intent Classification ⚠️ NEEDS FIX

**Problem:** Non-weather questions classified as "weather" because they contain weather-related words.

**Examples:**
- "How does the brain work?" → classified as weather (should be general_info)
- "How do you unclog a drain?" → classified as weather (should be how-to)
- "How do you snowboard?" → classified as weather (should be how-to/sports)

**Root Cause:** Pattern matching in intent classification is too aggressive. Keywords like "snow" trigger weather classification even when the question is not about weather.

**Analysis:**
- "snowboard" contains "snow" → triggers weather pattern
- Need context-aware classification
- Need to check if question is asking "how to" vs "what is the weather"

**Proposed Fix:**

### Option A: Improve Pattern Matching (Quick Fix)
```python
# In intent_classifier.py - make weather patterns more specific
weather_patterns = [
    r'\b(weather|temperature|forecast|rain|snow)\b.*\b(today|tomorrow|this week|now|currently)\b',
    r'\b(what|how|is)\b.*\b(weather|temperature|rain|snow|forecast)\b',
    r'\bweather in\b',
    r'\bis it (going to )?(rain|snow|storm)\b'
]

# Exclude "how to" questions
if re.search(r'\bhow (to|do (I|you))\b', query, re.IGNORECASE):
    # Not weather - it's a how-to question
    continue
```

### Option B: Improve LLM Classification (Better Long-term)
- Add negative examples to LLM classification prompt
- Train on disambiguating "weather words" in non-weather contexts
- Examples:
  - "How do you snowboard?" → sports/how-to, not weather
  - "What is a snowflake?" → science, not weather
  - "When will the snow start?" → weather ✓

**Recommendation:** Implement both - Option A as quick fix, Option B for long-term improvement

**Status:** ⚠️ NEEDS FIX

**Priority:** HIGH (causing 3/11 weather failures)

---

## Issue 3: Forecast vs Current Weather ⚠️ NEEDS FIX

**Problem:** Users asking about future weather receive current weather data.

**Examples:**
- "Is it going to snow this week?" → got current conditions (light drizzle)
- "When will the rain stop?" → got current conditions, no forecast
- "When will the snow start?" → got current conditions, no forecast

**Root Cause:** Weather RAG service (`src/rag/weather/main.py`) only has `/weather/current` endpoint. No forecast capability.

**Analysis:**
- OpenWeatherMap API supports forecast: `https://api.openweathermap.org/data/2.5/forecast`
- Need to detect timeframe entities: "tomorrow", "this week", "next week"
- Need to route to forecast endpoint vs current endpoint
- Need to format forecast data for LLM synthesis

**Proposed Fix:**

### 1. Add Forecast Endpoint to Weather RAG
```python
# src/rag/weather/main.py

@app.get("/weather/forecast")
async def get_weather_forecast(
    location: str = "Baltimore, MD",
    days: int = 5  # OpenWeatherMap provides 5-day forecast
):
    """Get weather forecast for a location."""

    # Geocode location
    coords = await geocode_location(location)

    # Call forecast API
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": coords["lat"],
        "lon": coords["lon"],
        "appid": OPENWEATHER_API_KEY,
        "units": "imperial"
    }

    response = await http_client.get(url, params=params)
    forecast_data = response.json()

    # Format forecast data for LLM
    return format_forecast_data(forecast_data, coords["name"])
```

### 2. Extract Timeframe Entities
```python
# src/orchestrator/intent_classifier.py - enhance weather entity extraction

elif category == IntentCategory.WEATHER:
    # Extract timeframe
    timeframes = {
        r'\btoday\b': 'today',
        r'\btonight\b': 'tonight',
        r'\btomorrow\b': 'tomorrow',
        r'\bthis week\b': 'this_week',
        r'\bnext week\b': 'next_week',
        r'\bweekend\b': 'weekend'
    }

    for pattern, value in timeframes.items():
        if re.search(pattern, query, re.IGNORECASE):
            entities['timeframe'] = value
            break

    # If timeframe is future, mark as forecast
    if entities.get('timeframe') in ['tomorrow', 'this_week', 'next_week', 'weekend']:
        entities['forecast'] = True
```

### 3. Route to Forecast Endpoint
```python
# src/orchestrator/main.py - retrieve_node

if state.intent == IntentCategory.WEATHER:
    location = state.entities.get("location", "Baltimore, MD")

    # Check if forecast is needed
    if state.entities.get('forecast', False):
        # Call forecast endpoint
        response = await client.get(
            "/weather/forecast",
            params={"location": location}
        )
    else:
        # Call current weather endpoint
        response = await client.get(
            "/weather/current",
            params={"location": location}
        )
```

**Status:** ⚠️ NEEDS FIX

**Priority:** HIGH (causing 3/11 weather failures)

**Complexity:** MEDIUM (requires new endpoint, entity extraction, routing logic)

---

## Action Plan

### Immediate (Next Steps)
1. ✅ Fix city extraction (COMPLETED 2025-11-19)
2. ⚠️ Fix wrong intent classification (Option A - pattern matching)
3. ⚠️ Add forecast capability (all 3 sub-tasks)
4. 🔄 Re-run test to verify fixes

### Short-term (This Week)
5. Improve LLM classification with negative examples (Option B)
6. Add more forecast timeframes (hourly, 3-day, 7-day)
7. Handle edge cases (precipitation type, severe weather)

### Success Criteria
- Weather failure rate < 10% (currently 37.9%)
- All city-specific queries return correct city
- Forecast queries return future weather, not current
- "How to" questions not classified as weather

---

## Related Files

**Modified (Weather City Fix):**
- `src/orchestrator/intent_classifier.py`
- `src/orchestrator/main.py`

**Needs Modification (Remaining Fixes):**
- `src/orchestrator/intent_classifier.py` (pattern matching, timeframe extraction)
- `src/orchestrator/main.py` (forecast routing)
- `src/rag/weather/main.py` (forecast endpoint)

**Test Files:**
- `test_1000_questions.py`
- `test_results_1000_20251119_100950.json`

---

**Next Task:** Implement wrong intent classification fix (Option A)
