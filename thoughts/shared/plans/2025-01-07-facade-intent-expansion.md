# Facade Intent Classification Expansion - Implementation Plan

**Date**: 2025-01-07
**Research**: `thoughts/shared/research/RESEARCH_FACADE_INTENT_CLASSIFICATIONS_MISSING.md`
**Repository**: project-athena

## Overview

Expand the Airbnb guest assistant facade from basic Baltimore queries (location, restaurants, distances) to comprehensive guest support including weather, transportation, entertainment, flights, news, stocks, and web search fallback. This refactors the existing `ollama_baltimore_smart_facade.py` into a modular architecture supporting 7 new intent categories through strategic API integrations.

## Current State Analysis

**Existing Implementation** (`research/jetson-iterations/ollama_baltimore_smart_facade.py`):
- **Lines 48-110**: Simple `analyze_query()` function with pattern matching
- **Current Intents**: Location (address, neighborhood), distances (5 destinations), restaurants (4 categories), emergency services
- **Placeholder Weather**: Line 106-107 returns "I don't have current weather" message
- **Architecture**: Monolithic function with inline pattern matching, no API integrations
- **Deployment**: Runs on Jetson at `/mnt/nvme/athena-lite/`

**Missing Capabilities** (from research):
1. ❌ Real-time weather (Weather.gov + OpenWeatherMap APIs)
2. ❌ 7 airports with flight status (BWI, DCA, IAD, PHL, JFK, EWR, LGA)
3. ❌ 10 streaming services + TV guide
4. ❌ Local events (Eventbrite, Ticketmaster, Songkick APIs)
5. ❌ News (local Baltimore + national)
6. ❌ Stock market data (Alpha Vantage)
7. ❌ Web search fallback (DuckDuckGo)

**Existing Infrastructure**:
- ✅ Caching system (lines 36-46): `get_cached_data()`, `set_cached_data()` with 5-min TTL
- ✅ Flask framework with streaming support
- ✅ Logging (`logger` at line 16)
- ✅ Requirements file at `src/jetson/requirements.txt`

## Desired End State

After implementation:
- **100% Query Coverage**: Weather, airports, flights, streaming, events, news, stocks, web search
- **Modular Architecture**: `src/jetson/facade/` with separate handlers for each category
- **API Integrations**: 10+ APIs (Weather.gov, DuckDuckGo, TMDb, Alpha Vantage, etc.)
- **Smart Routing**: Intent classifier directs queries to appropriate handler
- **Performance**: <500ms cached responses, <3s API calls, 70%+ cache hit rate
- **Deployment**: Version-controlled in `src/jetson/`, deployed to `/mnt/nvme/athena-lite/`

### Verification

**Automated Tests**:
```bash
# Run comprehensive query tests
python -m pytest tests/facade/test_intent_classifier.py -v
python -m pytest tests/facade/test_handlers.py -v

# Verify API integrations
python tests/facade/test_api_connectivity.py

# Performance benchmarks
python tests/facade/benchmark_response_times.py
```

**Manual Verification**:
- Guest asks "What's the weather tomorrow?" → Returns accurate forecast in <3s
- Guest asks "Where can I watch The Last of Us?" → Returns "HBO Max" from static data
- Guest asks "Flight status for AA1234?" → Returns real-time status via FlightAware
- Guest asks "Events tonight in Baltimore?" → Returns 3 events from Eventbrite
- Unknown query → Returns DuckDuckGo instant answer or falls back to LLM

## What We're NOT Doing

- ❌ Generalizing to other cities (Baltimore-specific only)
- ❌ Building admin UI for intent management
- ❌ Implementing voice biometrics or personalization
- ❌ Creating mobile app integration
- ❌ Adding payment processing for reservations
- ❌ Maintaining backward compatibility (direct refactor)
- ❌ Supporting languages other than English

## Implementation Approach

**Strategy**: Incremental refactor through 4 phases, each independently testable and deployable:

1. **Phase 1 (Week 1)**: Core infrastructure + essential APIs (Weather, Web Search, Static Data)
2. **Phase 2 (Week 2)**: Travel & events (Flights, Events, Transportation)
3. **Phase 3 (Week 3)**: Entertainment deep dive (Streaming APIs, Concerts)
4. **Phase 4 (Week 4)**: News & Finance (News, Stocks, Sports)

**Architecture Pattern**:
```
Query → Intent Classifier → Handler → API/Cache → Response
```

**Deployment Flow**:
```
src/jetson/ (git) → Deploy script → /mnt/nvme/athena-lite/ (Jetson)
```

---

## Phase 1: Core Infrastructure & Essential APIs

**Goal**: Build modular architecture foundation + highest-value guest queries (weather, web search)

### Overview

Create `src/jetson/facade/` module structure with:
- Intent classifier for all 7 categories
- Weather handler (Weather.gov primary, OpenWeatherMap backup)
- Web search handler (DuckDuckGo Instant Answer API)
- Static data handlers (airports, streaming services)
- Configuration management (API keys, endpoints)
- Caching utilities

### Changes Required

#### 1. Create Module Structure

**Directory**: `src/jetson/facade/`

```bash
src/jetson/facade/
├── __init__.py                      # Package exports
├── airbnb_intent_classifier.py      # Comprehensive intent classification
├── handlers/                        # API handler modules
│   ├── __init__.py
│   ├── weather.py                   # Weather.gov + OpenWeatherMap
│   ├── web_search.py                # DuckDuckGo Instant Answer
│   ├── airports.py                  # Static airport data + future flight APIs
│   ├── streaming.py                 # Static streaming service data
│   ├── events.py                    # Placeholder for Phase 2
│   ├── news.py                      # Placeholder for Phase 4
│   └── stocks.py                    # Placeholder for Phase 4
├── config/
│   ├── __init__.py
│   ├── api_config.py                # API keys, endpoints, rate limits
│   └── static_data.py               # Airports, streaming services, Baltimore data
└── utils/
    ├── __init__.py
    └── cache.py                     # Enhanced caching with TTL per category
```

#### 2. Intent Classifier

**File**: `src/jetson/facade/airbnb_intent_classifier.py`

```python
"""
Comprehensive Intent Classification for Airbnb Guest Assistant

Classifies guest queries into 7 major categories:
1. Weather (real-time conditions, forecasts)
2. Transportation (airports, flights, transit, parking)
3. Entertainment (streaming, events, concerts, movies)
4. News (local Baltimore, national headlines, sports)
5. Financial (stocks, market indices)
6. Location (existing: address, distances, restaurants, emergency)
7. Web Search (fallback for unclassified queries)

Returns: (intent_type, handler_name, extracted_data)
"""

import re
import logging
from typing import Tuple, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class IntentType:
    """Intent type constants"""
    QUICK = "quick"          # Static response, no API needed
    API_CALL = "api_call"    # Requires external API
    WEB_SEARCH = "web_search"  # DuckDuckGo fallback
    LLM = "llm"              # Complex query, needs LLM


class AirbnbIntentClassifier:
    """
    Comprehensive intent classification for Airbnb guest queries

    Priority Order:
    1. Weather queries (high frequency)
    2. Location queries (existing: address, restaurants, distances)
    3. Transportation (airports, parking, transit)
    4. Entertainment (streaming, events)
    5. News & Finance
    6. Web Search fallback
    7. LLM (last resort)
    """

    # Baltimore-specific constants
    PROPERTY_ADDRESS = "912 South Clinton St, Baltimore, MD 21224"
    NEIGHBORHOOD = "Canton"
    ZIP_CODE = "21224"

    def classify(self, query: str) -> Tuple[str, str, Optional[Dict[str, Any]]]:
        """
        Main classification entry point

        Returns:
            (intent_type, handler_or_response, data)

        Examples:
            "weather tomorrow" → ("api_call", "weather", {"timeframe": "tomorrow"})
            "address" → ("quick", "912 South Clinton...", None)
            "unknown query" → ("web_search", "web_search", {"query": "..."})
        """
        q = query.lower().strip()

        # === CATEGORY 1: WEATHER (Highest Priority) ===
        weather_result = self._classify_weather(q)
        if weather_result:
            return weather_result

        # === CATEGORY 2: LOCATION (Existing Patterns) ===
        location_result = self._classify_location(q)
        if location_result:
            return location_result

        # === CATEGORY 3: TRANSPORTATION ===
        transport_result = self._classify_transportation(q)
        if transport_result:
            return transport_result

        # === CATEGORY 4: ENTERTAINMENT ===
        entertainment_result = self._classify_entertainment(q)
        if entertainment_result:
            return entertainment_result

        # === CATEGORY 5: NEWS & FINANCE ===
        news_finance_result = self._classify_news_finance(q)
        if news_finance_result:
            return news_finance_result

        # === CATEGORY 6: WEB SEARCH FALLBACK ===
        if self._needs_web_search(q):
            logger.info(f"🌐 Intent: WEB_SEARCH")
            return (IntentType.WEB_SEARCH, "web_search", {"query": query})

        # === CATEGORY 7: LLM (Last Resort) ===
        logger.info(f"🤖 Intent: LLM (unclassified)")
        return (IntentType.LLM, "general", None)

    def _classify_weather(self, q: str) -> Optional[Tuple]:
        """Classify weather-related queries"""
        if not any(word in q for word in ['weather', 'temperature', 'temp', 'rain', 'snow',
                                           'storm', 'hot', 'cold', 'sunny', 'cloudy', 'forecast']):
            return None

        # Determine timeframe
        timeframe = "current"  # default
        if any(word in q for word in ['tomorrow', 'tmrw']):
            timeframe = "tomorrow"
        elif any(word in q for word in ['weekend', 'saturday', 'sunday']):
            timeframe = "weekend"
        elif 'week' in q:
            timeframe = "week"
        elif 'today' in q or 'now' in q or 'current' in q:
            timeframe = "current"

        logger.info(f"🌤️ Intent: WEATHER ({timeframe})")
        return (IntentType.API_CALL, "weather", {"timeframe": timeframe, "query": q})

    def _classify_location(self, q: str) -> Optional[Tuple]:
        """Classify location queries (existing patterns from facade)"""
        # Property address
        if 'address' in q or 'where am i' in q or 'this property' in q:
            logger.info(f"📍 Intent: QUICK (address)")
            return (IntentType.QUICK, self.PROPERTY_ADDRESS, None)

        # Neighborhood
        if 'neighborhood' in q:
            logger.info(f"📍 Intent: QUICK (neighborhood)")
            return (IntentType.QUICK, f"You're in {self.NEIGHBORHOOD}, Baltimore", None)

        # Distance queries (existing patterns)
        if 'how far' in q:
            if 'inner harbor' in q:
                return (IntentType.QUICK, "Inner Harbor is 2.5 miles, about 10 minutes by car or 20 minutes on the water taxi", None)
            elif 'camden' in q or 'orioles' in q:
                return (IntentType.QUICK, "Camden Yards is 2.5 miles, 10 minutes by car or 20 minutes on Light Rail", None)
            elif 'ravens' in q or 'm&t' in q:
                return (IntentType.QUICK, "M&T Bank Stadium is 3 miles, about 15 minutes by car", None)
            elif 'bwi' in q or 'airport' in q:
                return (IntentType.QUICK, "BWI Airport is 15 miles south, 25-30 minutes by car, Uber/Lyft $35-45, or 45 minutes on Light Rail for $2", None)
            elif 'dc' in q or 'washington' in q:
                return (IntentType.QUICK, "Washington DC is 40 miles, take MARC train from Penn Station (1 hour, ~$8)", None)

        # Restaurants (existing patterns)
        if any(word in q for word in ['best', 'good', 'where', 'restaurant', 'food']):
            if 'crab' in q:
                return (IntentType.QUICK, "Best crab cakes: 1) Koco's Pub (best), 2) G&M (huge), 3) Pappas, 4) Captain James (2-for-1 Mondays, 5 min away)", None)
            elif 'lobster' in q:
                return (IntentType.QUICK, "Thames Street Oyster House in Fells Point has amazing lobster rolls (10 min walk)", None)
            elif 'coffee' in q:
                return (IntentType.QUICK, "Ceremony Coffee on Boston St for specialty coffee, or Patterson Perk for cozy neighborhood vibes", None)
            elif 'breakfast' in q:
                return (IntentType.QUICK, "Blue Moon Cafe for Captain Crunch French Toast, Iron Rooster for all-day breakfast, or THB for fresh bagels", None)

        # Emergency (existing patterns)
        if any(word in q for word in ['hospital', 'emergency', 'urgent', 'doctor']):
            return (IntentType.QUICK, "Nearest hospital: Johns Hopkins Bayview, 2.5 miles (10 min), 4940 Eastern Ave, 410-550-0100. Emergency: Call 911", None)

        if 'pharmacy' in q:
            return (IntentType.QUICK, "24-hour pharmacy: CVS at 3701 Eastern Ave (1 mile)", None)

        return None

    def _classify_transportation(self, q: str) -> Optional[Tuple]:
        """Classify transportation queries (airports, parking, transit)"""
        # Airport queries
        if 'airport' in q:
            # Static airport info (Phase 1)
            if 'closest' in q or 'nearest' in q:
                logger.info(f"✈️ Intent: QUICK (nearest airport)")
                return (IntentType.QUICK, "Closest airport: BWI (15 mi, 25-30 min, $35-45 Uber). Also: DCA (40 mi), IAD (50 mi), PHL (95 mi)", None)

            # Specific airport codes - will use static data in Phase 1, API in Phase 2
            for code in ['bwi', 'dca', 'iad', 'phl', 'jfk', 'ewr', 'lga']:
                if code in q:
                    logger.info(f"✈️ Intent: API_CALL (airport_{code.upper()})")
                    return (IntentType.API_CALL, "airports", {"airport_code": code.upper(), "query": q})

        # Flight status (Phase 2)
        if 'flight' in q and any(word in q for word in ['status', 'delayed', 'on time', 'delay']):
            logger.info(f"✈️ Intent: API_CALL (flight_status) - Phase 2")
            return (IntentType.API_CALL, "airports", {"type": "flight_status", "query": q})

        # Parking (static quick responses)
        if 'parking' in q:
            if 'street' in q:
                return (IntentType.QUICK, "Street parking in Canton: Meter parking 8am-8pm M-Sat ($1.50/hr), free overnight and Sundays. Pay at kiosks or ParkMobile app", None)
            elif 'garage' in q or 'lot' in q:
                return (IntentType.QUICK, "Nearest garage: Inner Harbor Garage ($12/day), Fells Point garage ($8/day). Street parking often easier in Canton", None)
            else:
                return (IntentType.QUICK, "Street parking: Free overnight/Sundays, $1.50/hr M-Sat 8am-8pm. Garages: Inner Harbor $12/day", None)

        # Public transit (static quick responses)
        if 'bus' in q or 'light rail' in q or 'marc' in q or 'water taxi' in q:
            if 'circulator' in q:
                return (IntentType.QUICK, "Charm City Circulator: Purple route runs every 15 min, free, nearest stop on Boston St", None)
            elif 'water taxi' in q:
                return (IntentType.QUICK, "Water taxi runs Apr-Nov, 11am-11pm weekdays, 10am-midnight weekends. $15 all-day pass, nearest stop at Canton Waterfront Park", None)
            elif 'marc' in q:
                return (IntentType.QUICK, "MARC Penn Line: Canton → Penn Station (15 min drive/Uber) → DC Union Station (1 hr, $8)", None)

        # Bike share / scooters
        if ('bike' in q and ('rent' in q or 'share' in q)) or 'scooter' in q:
            return (IntentType.QUICK, "Baltimore Bike Share: $2 per 30 min, stations at Canton Crossing and Patterson Park. Download BCycle app. Lime/Bird scooters also available", None)

        return None

    def _classify_entertainment(self, q: str) -> Optional[Tuple]:
        """Classify entertainment queries (streaming, events, movies)"""
        # Streaming services
        if any(word in q for word in ['streaming', 'netflix', 'hulu', 'disney', 'hbo', 'max',
                                       'prime video', 'peacock', 'paramount', 'apple tv', 'youtube tv']):
            # List available services
            if 'what services' in q or 'streaming services' in q:
                logger.info(f"📺 Intent: QUICK (streaming services list)")
                return (IntentType.QUICK, "Available: Netflix, Hulu, Disney+, HBO Max, Prime Video, Peacock, Paramount+, Apple TV+, YouTube TV (+ NFL Sunday Ticket)", None)

            # How to access
            if 'how' in q or 'login' in q or 'password' in q:
                return (IntentType.QUICK, "All streaming apps are already logged in on the TV. Just select the app and start watching!", None)

            # "Where can I watch X?" - Phase 3 will add API lookup
            if 'where' in q and 'watch' in q:
                logger.info(f"📺 Intent: API_CALL (streaming_search) - Phase 3")
                return (IntentType.API_CALL, "streaming", {"type": "search", "query": q})

            # Service-specific quick answers (Phase 1 static, Phase 3 API)
            if 'disney' in q and ('marvel' in q or 'star wars' in q):
                if 'marvel' in q:
                    return (IntentType.QUICK, "Marvel on Disney+: All MCU movies, Loki, WandaVision, What If, Hawkeye, Moon Knight, She-Hulk", None)
                else:
                    return (IntentType.QUICK, "Star Wars on Disney+: All movies, The Mandalorian, Ahsoka, Andor, Obi-Wan, Clone Wars, Bad Batch", None)

        # Live TV / Sports on YouTube TV
        if 'youtube tv' in q or ('sunday ticket' in q and 'nfl' in q):
            if 'sunday ticket' in q:
                return (IntentType.QUICK, "Sunday Ticket on YouTube TV shows ALL out-of-market Sunday NFL games. Open YouTube TV > Sports section", None)
            elif 'channels' in q:
                return (IntentType.QUICK, "YouTube TV has 100+ live channels including ESPN, CNN, HGTV, Food Network, and local networks", None)

        # Local events (Phase 2 API integration)
        if any(word in q for word in ['events', 'things to do', 'what to do', 'tonight', 'weekend']):
            if 'tonight' in q or 'today' in q:
                logger.info(f"🎭 Intent: API_CALL (events_today) - Phase 2")
                return (IntentType.API_CALL, "events", {"timeframe": "today", "query": q})
            elif 'tomorrow' in q:
                return (IntentType.API_CALL, "events", {"timeframe": "tomorrow", "query": q})
            elif 'weekend' in q:
                return (IntentType.API_CALL, "events", {"timeframe": "weekend", "query": q})

        # Museums / Attractions (static quick responses)
        if 'museum' in q:
            if 'free' in q:
                return (IntentType.QUICK, "FREE museums: Baltimore Museum of Art (always free), Walters Art Museum (always free), American Visionary Art Museum (Wed 5-9pm free)", None)
            else:
                return (IntentType.QUICK, "Top museums: BMA (free), Walters (free), AVAM ($16), National Aquarium ($40), Fort McHenry ($15), Science Center ($25)", None)

        if 'aquarium' in q:
            return (IntentType.QUICK, "National Aquarium: Inner Harbor, $40 adults, $25 kids. Book online for discount. Highlights: shark tank, dolphin show, rainforest. 2-3 hours to see everything. 10 min drive from Canton", None)

        # Nightlife
        if 'nightlife' in q or ('bar' in q and 'where' in q):
            return (IntentType.QUICK, "Nightlife areas: 1) Fells Point (historic pubs, live music), 2) Federal Hill (young crowd, dance clubs), 3) Power Plant Live (club complex), 4) Canton (local bars)", None)

        return None

    def _classify_news_finance(self, q: str) -> Optional[Tuple]:
        """Classify news and finance queries (Phase 4)"""
        # News queries
        if 'news' in q:
            if 'local' in q or 'baltimore' in q:
                logger.info(f"📰 Intent: API_CALL (baltimore_news) - Phase 4")
                return (IntentType.API_CALL, "news", {"type": "local", "query": q})
            elif 'headlines' in q or 'top' in q:
                logger.info(f"📰 Intent: API_CALL (national_news) - Phase 4")
                return (IntentType.API_CALL, "news", {"type": "national", "query": q})

        # Stock market queries
        if any(word in q for word in ['stock', 'ticker', 'share price', 'dow', 'nasdaq', 's&p', 'market']):
            logger.info(f"📈 Intent: API_CALL (stocks) - Phase 4")
            return (IntentType.API_CALL, "stocks", {"query": q})

        # Sports scores (existing - will stay as LLM in Phase 1, move to API in Phase 4)
        if any(word in q for word in ['score', 'game', 'won', 'lost', 'beat', 'result']):
            if any(team in q for team in ['ravens', 'orioles']):
                logger.info(f"🏈 Intent: LLM (sports_score) - API in Phase 4")
                return (IntentType.LLM, "sports_score", {"query": q})

        return None

    def _needs_web_search(self, q: str) -> bool:
        """
        Determine if query should use web search fallback

        Triggers:
        - Current/factual info keywords (latest, current, recent, today, now)
        - Unknown business queries (phone number, hours, address of)
        - Question patterns (who is, what is, when did, where is)
        """
        # Check for current/factual info keywords
        current_info_keywords = ['latest', 'current', 'recent', 'today', 'now',
                                  'who is', 'what is', 'when did', 'where is']
        if any(keyword in q for keyword in current_info_keywords):
            return True

        # Check for business info queries
        business_keywords = ['phone number', 'address of', 'hours', 'open',
                              'website', 'email', 'contact']
        if any(keyword in q for keyword in business_keywords):
            return True

        return False
```

#### 3. Weather Handler

**File**: `src/jetson/facade/handlers/weather.py`

```python
"""
Weather Handler - Real-time weather data for Baltimore

Primary: Weather.gov API (NOAA - free, no key required)
Backup: OpenWeatherMap API (1000 calls/day free tier)

Location: Canton, Baltimore MD 21224 (39.2808° N, 76.5822° W)
"""

import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WeatherHandler:
    """Fetch real-time weather for Baltimore Canton area"""

    # Baltimore Canton coordinates
    LATITUDE = 39.2808
    LONGITUDE = -76.5822
    LOCATION_NAME = "Canton, Baltimore"
    ZIP_CODE = "21224"

    # Weather.gov grid point (must be fetched once, then cached)
    # For Baltimore area, this is typically: "LWX" office, grid x/y varies
    WEATHER_GOV_OFFICE = "LWX"  # Sterling, VA office (covers Baltimore)
    WEATHER_GOV_GRID_X = 97
    WEATHER_GOV_GRID_Y = 71

    def __init__(self, openweather_api_key: Optional[str] = None):
        self.openweather_key = openweather_api_key
        self.cache = {}
        self.cache_ttl = 600  # 10 minutes for weather data

    def get_weather(self, timeframe: str = "current", query: str = "") -> str:
        """
        Get weather for specified timeframe

        Args:
            timeframe: "current", "tomorrow", "weekend", "week"
            query: Original query for context

        Returns:
            Natural language weather response
        """
        cache_key = f"weather_{timeframe}"
        cached = self._get_cached(cache_key)
        if cached:
            logger.info(f"✅ Weather cache hit: {timeframe}")
            return cached

        try:
            if timeframe == "current":
                response = self._get_current_weather()
            elif timeframe == "tomorrow":
                response = self._get_forecast_tomorrow()
            elif timeframe == "weekend":
                response = self._get_forecast_weekend()
            elif timeframe == "week":
                response = self._get_forecast_week()
            else:
                response = self._get_current_weather()

            self._set_cached(cache_key, response)
            return response

        except Exception as e:
            logger.error(f"❌ Weather API error: {e}", exc_info=True)
            return "I'm having trouble getting the weather right now. Check weather.com or the Weather Channel app"

    def _get_current_weather(self) -> str:
        """Get current weather conditions"""
        try:
            # Try Weather.gov first
            url = f"https://api.weather.gov/gridpoints/{self.WEATHER_GOV_OFFICE}/{self.WEATHER_GOV_GRID_X},{self.WEATHER_GOV_GRID_Y}"
            headers = {"User-Agent": "AirbnbGuestAssistant/1.0"}

            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                properties = data.get('properties', {})

                # Get current period from forecast
                temp = properties.get('temperature', {}).get('values', [])
                if temp and len(temp) > 0:
                    temp_c = temp[0].get('value')
                    temp_f = int((temp_c * 9/5) + 32) if temp_c else None

                # Get conditions from short forecast
                forecast_url = f"https://api.weather.gov/gridpoints/{self.WEATHER_GOV_OFFICE}/{self.WEATHER_GOV_GRID_X},{self.WEATHER_GOV_GRID_Y}/forecast"
                forecast_resp = requests.get(forecast_url, headers=headers, timeout=5)

                if forecast_resp.status_code == 200:
                    forecast_data = forecast_resp.json()
                    periods = forecast_data.get('properties', {}).get('periods', [])
                    if periods:
                        current_period = periods[0]
                        condition = current_period.get('shortForecast', 'Unknown')
                        temp_f = current_period.get('temperature', temp_f)
                        wind = current_period.get('windSpeed', 'calm')

                        return f"Currently {temp_f}°F and {condition.lower()}. Wind {wind}"

                # Fallback if detailed forecast fails
                if temp_f:
                    return f"Currently {temp_f}°F in {self.LOCATION_NAME}"

        except Exception as e:
            logger.warning(f"⚠️ Weather.gov failed, trying OpenWeatherMap: {e}")

        # Fallback to OpenWeatherMap
        if self.openweather_key:
            try:
                url = "https://api.openweathermap.org/data/2.5/weather"
                params = {
                    'lat': self.LATITUDE,
                    'lon': self.LONGITUDE,
                    'appid': self.openweather_key,
                    'units': 'imperial'
                }

                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    temp = int(data['main']['temp'])
                    condition = data['weather'][0]['description']
                    feels_like = int(data['main']['feels_like'])
                    wind_speed = int(data['wind']['speed'])

                    return f"Currently {temp}°F and {condition}. Feels like {feels_like}°F. Wind {wind_speed} mph"

            except Exception as e:
                logger.error(f"❌ OpenWeatherMap failed: {e}")

        raise Exception("All weather APIs failed")

    def _get_forecast_tomorrow(self) -> str:
        """Get tomorrow's forecast"""
        try:
            url = f"https://api.weather.gov/gridpoints/{self.WEATHER_GOV_OFFICE}/{self.WEATHER_GOV_GRID_X},{self.WEATHER_GOV_GRID_Y}/forecast"
            headers = {"User-Agent": "AirbnbGuestAssistant/1.0"}

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                periods = data.get('properties', {}).get('periods', [])

                # Find tomorrow's daytime period
                for period in periods:
                    if 'Tomorrow' in period.get('name', ''):
                        name = period['name']
                        temp = period['temperature']
                        condition = period['shortForecast']
                        precip = period.get('probabilityOfPrecipitation', {}).get('value', 0) or 0

                        if precip > 0:
                            return f"Tomorrow: {temp}°F, {condition.lower()}. {precip}% chance of precipitation"
                        else:
                            return f"Tomorrow: {temp}°F and {condition.lower()}"

                # If "Tomorrow" not found, use period index 2 or 3 (next day)
                if len(periods) >= 3:
                    tomorrow = periods[2] if len(periods) > 2 else periods[1]
                    temp = tomorrow['temperature']
                    condition = tomorrow['shortForecast']
                    return f"Tomorrow: {temp}°F and {condition.lower()}"

        except Exception as e:
            logger.error(f"❌ Tomorrow forecast failed: {e}")

        return "I couldn't get tomorrow's forecast. Check weather.com for the latest"

    def _get_forecast_weekend(self) -> str:
        """Get weekend forecast"""
        try:
            url = f"https://api.weather.gov/gridpoints/{self.WEATHER_GOV_OFFICE}/{self.WEATHER_GOV_GRID_X},{self.WEATHER_GOV_GRID_Y}/forecast"
            headers = {"User-Agent": "AirbnbGuestAssistant/1.0"}

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                periods = data.get('properties', {}).get('periods', [])

                # Find Saturday and Sunday
                weekend_periods = [p for p in periods if 'Saturday' in p.get('name', '') or 'Sunday' in p.get('name', '')]

                if len(weekend_periods) >= 2:
                    sat = weekend_periods[0]
                    sun = weekend_periods[1] if len(weekend_periods) > 1 else weekend_periods[0]

                    return f"Weekend: Saturday {sat['temperature']}°F ({sat['shortForecast']}), Sunday {sun['temperature']}°F ({sun['shortForecast']})"

        except Exception as e:
            logger.error(f"❌ Weekend forecast failed: {e}")

        return "I couldn't get the weekend forecast. Check weather.com for details"

    def _get_forecast_week(self) -> str:
        """Get 7-day forecast summary"""
        try:
            url = f"https://api.weather.gov/gridpoints/{self.WEATHER_GOV_OFFICE}/{self.WEATHER_GOV_GRID_X},{self.WEATHER_GOV_GRID_Y}/forecast"
            headers = {"User-Agent": "AirbnbGuestAssistant/1.0"}

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                periods = data.get('properties', {}).get('periods', [])

                # Summarize first 7 periods (roughly 3.5 days)
                summary_periods = periods[:7]
                temps = [p['temperature'] for p in summary_periods]
                high = max(temps)
                low = min(temps)

                # Check for rain
                has_rain = any('rain' in p['shortForecast'].lower() or 'shower' in p['shortForecast'].lower() for p in summary_periods)

                if has_rain:
                    return f"This week: High {high}°F, Low {low}°F. Expect some rain. Check weather.com for daily details"
                else:
                    return f"This week: High {high}°F, Low {low}°F. Generally clear conditions. Check weather.com for daily details"

        except Exception as e:
            logger.error(f"❌ Weekly forecast failed: {e}")

        return "I couldn't get the weekly forecast. Check weather.com or the Weather Channel app"

    def _get_cached(self, key: str) -> Optional[str]:
        """Get cached weather data"""
        if key in self.cache:
            cached = self.cache[key]
            age = datetime.now().timestamp() - cached['time']
            if age < self.cache_ttl:
                return cached['data']
        return None

    def _set_cached(self, key: str, data: str):
        """Cache weather data"""
        self.cache[key] = {
            'data': data,
            'time': datetime.now().timestamp()
        }
```

#### 4. Web Search Handler

**File**: `src/jetson/facade/handlers/web_search.py`

```python
"""
Web Search Handler - DuckDuckGo Instant Answer API

Provides fallback for unclassified queries using DuckDuckGo's free Instant Answer API.
No API key required, no rate limiting.

Use cases:
- Business hours: "What time does Koco's Pub close?"
- Phone numbers: "Phone number for Canton Water Taxi"
- Definitions: "What is a blue crab?"
- Current events: "Who won the election?"
- Unknown queries that need factual lookup
"""

import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WebSearchHandler:
    """DuckDuckGo Instant Answer API for web search fallback"""

    DUCKDUCKGO_API = "https://api.duckduckgo.com/"

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache for web searches

    def search(self, query: str) -> str:
        """
        Perform web search and return concise answer

        Args:
            query: Search query

        Returns:
            Instant answer or fallback message
        """
        cache_key = f"search_{query.lower()}"
        cached = self._get_cached(cache_key)
        if cached:
            logger.info(f"✅ Web search cache hit: {query[:30]}")
            return cached

        try:
            params = {
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            }

            response = requests.get(self.DUCKDUCKGO_API, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()

                # Try multiple answer fields in priority order
                answer = (
                    data.get('AbstractText') or
                    data.get('Answer') or
                    data.get('Definition') or
                    ''
                )

                if answer:
                    # Truncate to reasonable length
                    if len(answer) > 300:
                        answer = answer[:297] + "..."

                    logger.info(f"🌐 Web search success: {query[:30]}")
                    self._set_cached(cache_key, answer)
                    return answer

            logger.warning(f"⚠️ DuckDuckGo no results for: {query[:30]}")

        except Exception as e:
            logger.error(f"❌ Web search error for '{query[:30]}': {e}")

        # Fallback message
        return "I'm not sure about that. Try searching on Google or check baltimore.org for local info"

    def _get_cached(self, key: str) -> Optional[str]:
        """Get cached search result"""
        if key in self.cache:
            from datetime import datetime
            cached = self.cache[key]
            age = datetime.now().timestamp() - cached['time']
            if age < self.cache_ttl:
                return cached['data']
        return None

    def _set_cached(self, key: str, data: str):
        """Cache search result"""
        from datetime import datetime
        self.cache[key] = {
            'data': data,
            'time': datetime.now().timestamp()
        }
```

#### 5. Static Data Configuration

**File**: `src/jetson/facade/config/static_data.py`

```python
"""
Static Data Configuration

Baltimore-specific data that doesn't require API calls:
- Airport information (7 airports)
- Streaming services (10 services)
- Baltimore attractions, restaurants, transportation
"""

# === AIRPORTS ===

AIRPORT_INFO = {
    'BWI': {
        'name': 'Baltimore/Washington International Thurgood Marshall Airport',
        'code': 'BWI',
        'distance_miles': 15,
        'drive_time': '25-30 min',
        'uber_cost': '$35-45',
        'light_rail': 'Yes - $2, 45 min from Canton Crossing',
        'parking': '$6/day economy, $22/day garage',
        'terminal_count': 1,
        'airlines': 'Southwest (hub), Spirit, United, Delta, American',
        'phone': '410-859-7111',
        'quick_response': "BWI Airport: 15 mi (25-30 min), Uber $35-45, Light Rail $2 (45 min from Canton Crossing). Southwest hub. Parking $6/day economy"
    },
    'DCA': {
        'name': 'Ronald Reagan Washington National Airport',
        'code': 'DCA',
        'distance_miles': 40,
        'drive_time': '45-60 min',
        'uber_cost': '$60-75',
        'metro': 'Yes - Blue/Yellow lines',
        'terminal_count': 3,
        'airlines': 'American (hub), Delta, United, Southwest',
        'phone': '703-417-8000',
        'quick_response': "Reagan National (DCA): 40 mi (45-60 min), Uber $60-75, or MARC to Union Station + Metro (1.5 hrs, ~$12). American Airlines hub"
    },
    'IAD': {
        'name': 'Washington Dulles International Airport',
        'code': 'IAD',
        'distance_miles': 50,
        'drive_time': '60-75 min',
        'uber_cost': '$80-100',
        'metro': 'Silver Line Express bus',
        'terminal_count': 1,
        'airlines': 'United (hub), international flights',
        'phone': '703-572-2700',
        'quick_response': "Dulles (IAD): 50 mi (60-75 min), Uber $80-100, or MARC to Union Station + Silver Line Express (2 hrs, $12-15). United hub, international flights"
    },
    'PHL': {
        'name': 'Philadelphia International Airport',
        'code': 'PHL',
        'distance_miles': 95,
        'drive_time': '1.5-2 hrs',
        'uber_cost': '$120-150',
        'amtrak': 'Yes - Amtrak from Penn Station to PHL Airport station (1.5 hrs, $30-50)',
        'terminal_count': 7,
        'airlines': 'American (hub), Frontier, Spirit',
        'phone': '215-937-6937',
        'quick_response': "Philadelphia (PHL): 95 mi (1.5-2 hrs drive), Uber $120-150, or Amtrak from Baltimore Penn Station (1.5 hrs, $30-50). American hub"
    },
    'JFK': {
        'name': 'John F. Kennedy International Airport',
        'code': 'JFK',
        'distance_miles': 195,
        'drive_time': '3.5-4 hrs',
        'amtrak': 'Amtrak to Penn Station NYC, then AirTrain ($60-100 + $8, 3-4 hrs)',
        'airlines': 'All major international carriers',
        'phone': '718-244-4444',
        'quick_response': "JFK Airport: 195 mi (3.5-4 hrs drive). Best option: Amtrak to NYC Penn Station + AirTrain ($60-100 + $8, 3-4 hrs). All international carriers"
    },
    'EWR': {
        'name': 'Newark Liberty International Airport',
        'code': 'EWR',
        'distance_miles': 185,
        'drive_time': '3-3.5 hrs',
        'amtrak': 'Amtrak to Newark Airport station (2.5 hrs, $60-100)',
        'airlines': 'United (hub), international flights',
        'phone': '973-961-6000',
        'quick_response': "Newark (EWR): 185 mi (3-3.5 hrs drive). Easiest: Amtrak direct to Newark Airport station (2.5 hrs, $60-100). United hub"
    },
    'LGA': {
        'name': 'LaGuardia Airport',
        'code': 'LGA',
        'distance_miles': 190,
        'drive_time': '3.5-4 hrs',
        'amtrak': 'Amtrak to Penn Station NYC, then taxi/Uber ($60-100 + $30-40)',
        'airlines': 'Delta (hub), American, United - domestic only',
        'phone': '718-533-3400',
        'quick_response': "LaGuardia (LGA): 190 mi (3.5-4 hrs drive). Amtrak to NYC Penn Station + taxi/Uber ($60-100 + $30-40). Delta hub, domestic flights only"
    }
}

# === STREAMING SERVICES ===

STREAMING_SERVICES = {
    'netflix': {
        'name': 'Netflix',
        'description': 'Movies, TV shows, originals',
        'content': ['movies', 'series', 'documentaries', 'stand-up'],
        'popular': ['Stranger Things', 'Wednesday', 'The Crown']
    },
    'hulu': {
        'name': 'Hulu',
        'description': 'Current TV episodes, originals, movies',
        'content': ['next-day TV', 'movies', 'originals'],
        'note': 'New episodes next day for current shows (ABC, NBC, Fox)'
    },
    'disney': {
        'name': 'Disney+',
        'description': 'Disney, Pixar, Marvel, Star Wars, National Geographic',
        'content': ['marvel', 'star wars', 'disney classics', 'pixar'],
        'popular': ['The Mandalorian', 'Loki', 'Moana']
    },
    'hbo': {
        'name': 'HBO Max',
        'description': 'HBO originals, Warner Bros movies, Max originals',
        'content': ['hbo series', 'warner movies', 'max originals'],
        'popular': ['House of the Dragon', 'The Last of Us', 'Succession']
    },
    'prime': {
        'name': 'Prime Video',
        'description': 'Amazon Prime - Movies, TV shows, Amazon originals',
        'content': ['movies', 'series', 'amazon originals'],
        'popular': ['The Boys', 'Jack Ryan', 'Lord of the Rings']
    },
    'peacock': {
        'name': 'Peacock',
        'description': 'NBC shows, movies, sports (Premier League), originals',
        'content': ['nbc shows', 'movies', 'premier league soccer', 'olympics'],
        'sports': 'EVERY Premier League match'
    },
    'paramount': {
        'name': 'Paramount+',
        'description': 'CBS shows, Paramount movies, sports',
        'content': ['cbs shows', 'paramount movies', 'nfl on cbs', 'champions league'],
        'sports': 'NFL on CBS, Champions League soccer, PGA Tour'
    },
    'appletv': {
        'name': 'Apple TV+',
        'description': 'Apple originals',
        'content': ['apple originals'],
        'popular': ['Ted Lasso', 'Severance', 'The Morning Show']
    },
    'youtube': {
        'name': 'YouTube TV',
        'description': 'Live TV - 100+ channels, unlimited DVR',
        'content': ['live tv', 'sports', 'news', 'entertainment'],
        'channels': 'ESPN, CNN, HGTV, Food Network, local networks (ABC, NBC, CBS, Fox)',
        'sports': 'ESPN, FS1, NBC Sports, CBS Sports, NFL Network, MLB Network',
        'dvr': 'Unlimited cloud DVR storage'
    },
    'sundayticket': {
        'name': 'NFL Sunday Ticket',
        'description': 'All out-of-market NFL games (YouTube TV add-on)',
        'content': ['nfl games'],
        'note': 'Shows ALL out-of-market Sunday NFL games. Open YouTube TV > Sports section'
    }
}

STREAMING_QUICK_ANSWERS = {
    'services_list': "Available: Netflix, Hulu, Disney+, HBO Max, Prime Video, Peacock, Paramount+, Apple TV+, YouTube TV (+ NFL Sunday Ticket)",
    'how_to_access': "All streaming apps are already logged in on the TV. Just select the app and start watching!",
    'live_tv': "YouTube TV has 100+ live channels including ESPN, CNN, HGTV, Food Network, and local networks",
    'nfl_sunday_ticket': "Sunday Ticket on YouTube TV shows ALL out-of-market Sunday NFL games. Open YouTube TV > Sports section",
    'ravens_games': "Ravens games on YouTube TV (CBS/Fox/NBC/ESPN). Check Sports section for today's schedule",
    'orioles_games': "Orioles games on MASN. Check YouTube TV guide or search 'Orioles'",
    'disney_marvel': "Marvel on Disney+: All MCU movies, Loki, WandaVision, What If, Hawkeye, Moon Knight, She-Hulk",
    'disney_star_wars': "Star Wars on Disney+: All movies, The Mandalorian, Ahsoka, Andor, Obi-Wan, Clone Wars, Bad Batch",
    'hulu_current_shows': "Hulu gets new episodes next day for current shows (ABC, NBC, Fox). Check 'New on Hulu'",
    'hbo_originals': "HBO Max originals: House of the Dragon, The Last of Us, Succession, White Lotus, Euphoria",
    'paramount_sports': "Paramount+ has live sports: NFL on CBS, Champions League soccer, PGA Tour",
    'peacock_premier_league': "Peacock has EVERY Premier League match (English soccer). Included with subscription"
}
```

#### 6. API Configuration

**File**: `src/jetson/facade/config/api_config.py`

```python
"""
API Configuration - Keys, Endpoints, Rate Limits

API keys are loaded from:
1. Environment variables on Jetson (.env file)
2. Kubernetes secrets (for cluster deployment)

Free tier limits tracked per API.
"""

import os
from typing import Dict, Any

# === API KEYS (from environment) ===

API_KEYS = {
    # Weather APIs
    'openweather': os.getenv('OPENWEATHER_API_KEY', ''),  # 1000 calls/day free

    # Entertainment APIs (Phase 3)
    'tmdb': os.getenv('TMDB_API_KEY', ''),  # Free with attribution
    'eventbrite': os.getenv('EVENTBRITE_API_KEY', ''),  # 1000 calls/day free
    'ticketmaster': os.getenv('TICKETMASTER_API_KEY', ''),  # 5000 calls/day free

    # News & Finance APIs (Phase 4)
    'newsapi': os.getenv('NEWSAPI_KEY', ''),  # 100 calls/day free
    'alphavantage': os.getenv('ALPHAVANTAGE_KEY', ''),  # 500 calls/day free

    # Flight APIs (Phase 2)
    'flightaware': os.getenv('FLIGHTAWARE_API_KEY', ''),  # Free tier available
}

# === API ENDPOINTS ===

API_ENDPOINTS = {
    # Weather
    'weather_gov': 'https://api.weather.gov',
    'openweathermap': 'https://api.openweathermap.org/data/2.5',

    # Web Search
    'duckduckgo': 'https://api.duckduckgo.com/',

    # Entertainment (Phase 3)
    'tmdb': 'https://api.themoviedb.org/3',
    'eventbrite': 'https://www.eventbriteapi.com/v3',
    'ticketmaster': 'https://app.ticketmaster.com/discovery/v2',
    'songkick': 'https://api.songkick.com/api/3.0',
    'bandsintown': 'https://rest.bandsintown.com',

    # News & Finance (Phase 4)
    'newsapi': 'https://newsapi.org/v2',
    'alphavantage': 'https://www.alphavantage.co/query',

    # Flights (Phase 2)
    'flightaware': 'https://aeroapi.flightaware.com/aeroapi',
}

# === RATE LIMITS (calls per day) ===

RATE_LIMITS = {
    'openweathermap': 1000,
    'tmdb': float('inf'),  # Free tier, no explicit limit
    'eventbrite': 1000,
    'ticketmaster': 5000,
    'newsapi': 100,
    'alphavantage': 500,
    'duckduckgo': float('inf'),  # No limit, no key required
}

# === CACHE TTL (seconds) ===

CACHE_TTL = {
    'weather': 600,  # 10 minutes
    'airports_static': 86400,  # 24 hours (static data)
    'flights': 300,  # 5 minutes (real-time)
    'events': 3600,  # 1 hour
    'streaming_search': 86400,  # 24 hours (content doesn't change often)
    'news': 1800,  # 30 minutes
    'stocks': 300,  # 5 minutes
    'web_search': 3600,  # 1 hour
}
```

#### 7. Refactor Main Facade

**File**: `research/jetson-iterations/ollama_baltimore_smart_facade.py`

**Changes**: Replace lines 48-110 (analyze_query function) with new modular system

```python
#!/usr/bin/env python3
"""
Baltimore Smart Facade - Comprehensive Airbnb Guest Assistant

Provides real-time information for Airbnb guests:
- Weather (real-time via Weather.gov/OpenWeatherMap)
- Transportation (7 airports, parking, transit)
- Entertainment (10 streaming services, local events)
- News & Finance (Baltimore news, stock market)
- Web Search fallback (DuckDuckGo)

Architecture: Intent Classifier → Handler → API/Cache → Response
"""
import os
import sys
import json
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from datetime import datetime, timedelta
import logging
import re
from typing import Dict, Any, Optional, Tuple

# Add src/jetson to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/jetson'))

from facade.airbnb_intent_classifier import AirbnbIntentClassifier, IntentType
from facade.handlers.weather import WeatherHandler
from facade.handlers.web_search import WebSearchHandler
from facade.config.api_config import API_KEYS
from facade.config.static_data import AIRPORT_INFO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PORT = 11434
REAL_OLLAMA = "http://localhost:11435"
HA_TOKEN = os.environ.get('HA_TOKEN', '')
HA_URL = "https://ha.xmojo.net"

# LOCATION INFORMATION
PROPERTY_ADDRESS = "912 South Clinton St, Baltimore, MD 21224"
NEIGHBORHOOD = "Canton"
CITY = "Baltimore"
STATE = "Maryland"
ZIP_CODE = "21224"

# Initialize intent classifier and handlers
intent_classifier = AirbnbIntentClassifier()
weather_handler = WeatherHandler(openweather_api_key=API_KEYS.get('openweather'))
web_search_handler = WebSearchHandler()

# Cache configuration
cache = {}
CACHE_TTL = 300  # 5 minutes default

def get_cached_data(key: str) -> Optional[Any]:
    """Get cached data if not expired"""
    if key in cache:
        cached = cache[key]
        if datetime.now().timestamp() - cached['time'] < CACHE_TTL:
            return cached['data']
    return None

def set_cached_data(key: str, data: Any):
    """Store data in cache"""
    cache[key] = {'data': data, 'time': datetime.now().timestamp()}

def analyze_query(query: str) -> Tuple[str, str]:
    """
    Analyze query using comprehensive intent classifier

    Returns: (query_type, response_content)
        query_type: 'quick' | 'llm'
        response_content: String response or 'general' for LLM
    """
    # Classify intent
    intent_type, handler_or_response, data = intent_classifier.classify(query)

    # === QUICK RESPONSES (no API needed) ===
    if intent_type == IntentType.QUICK:
        logger.info(f"⚡ Quick response")
        return ('quick', handler_or_response)

    # === API CALLS ===
    elif intent_type == IntentType.API_CALL:
        try:
            if handler_or_response == "weather":
                timeframe = data.get('timeframe', 'current')
                response = weather_handler.get_weather(timeframe, data.get('query', ''))
                return ('quick', response)

            elif handler_or_response == "airports":
                # Phase 1: Static airport info only
                airport_code = data.get('airport_code')
                if airport_code and airport_code in AIRPORT_INFO:
                    airport = AIRPORT_INFO[airport_code]
                    response = airport['quick_response']
                    return ('quick', response)
                else:
                    return ('quick', "Which airport? I have info on BWI, DCA, IAD, PHL, JFK, EWR, and LGA")

            elif handler_or_response == "streaming":
                # Phase 1: Static responses only (API integration in Phase 3)
                return ('quick', "Which streaming service are you asking about? We have Netflix, Hulu, Disney+, HBO Max, Prime Video, Peacock, Paramount+, Apple TV+, and YouTube TV")

            elif handler_or_response == "events":
                # Phase 2: Will implement Eventbrite API
                return ('quick', "Check baltimore.org/events or Eventbrite for tonight's events in Baltimore")

            elif handler_or_response == "news":
                # Phase 4: Will implement NewsAPI
                return ('quick', "Check baltimoresun.com or wbaltv.com for local Baltimore news")

            elif handler_or_response == "stocks":
                # Phase 4: Will implement Alpha Vantage
                return ('quick', "Check finance.yahoo.com or Google Finance for stock prices")

            else:
                logger.warning(f"⚠️ Unknown handler: {handler_or_response}")
                return ('llm', 'general')

        except Exception as e:
            logger.error(f"❌ API handler error: {e}", exc_info=True)
            return ('llm', 'general')

    # === WEB SEARCH FALLBACK ===
    elif intent_type == IntentType.WEB_SEARCH:
        try:
            search_query = data.get('query', query)
            response = web_search_handler.search(search_query)
            return ('quick', response)
        except Exception as e:
            logger.error(f"❌ Web search error: {e}", exc_info=True)
            return ('llm', 'general')

    # === LLM (Last Resort) ===
    else:
        logger.info(f"🤖 Passing to LLM")
        return ('llm', 'general')

# ... rest of facade code remains the same (get_ha_context, Flask routes, etc.) ...
```

#### 8. Update Requirements

**File**: `src/jetson/requirements.txt`

Add new dependencies:

```txt
# Web framework
flask==3.0.0
werkzeug==3.0.1

# HTTP client
requests==2.31.0

# Environment management
python-dotenv==1.0.0

# Utilities
python-dateutil==2.8.2

# Testing (for Phase 1 verification)
pytest==7.4.3
pytest-cov==4.1.0

# Legacy dependencies (for athena_lite_llm.py)
torch==2.1.0
transformers==4.35.0
```

#### 9. Environment Configuration

**File**: `/mnt/nvme/athena-lite/.env` (on Jetson)

```bash
# Home Assistant (get from thor cluster)
HA_TOKEN=<kubectl -n automation get secret home-assistant-credentials -o jsonpath='{.data.long-lived-token}' | base64 -d>
HA_URL=https://ha.xmojo.net

# Weather APIs (get from thor cluster)
OPENWEATHER_API_KEY=<kubectl -n automation get secret project-athena-credentials -o jsonpath='{.data.openweathermap-api-key}' | base64 -d>

# Phase 3 APIs (not needed yet, but reserved)
TMDB_API_KEY=
EVENTBRITE_API_KEY=
TICKETMASTER_API_KEY=

# Phase 4 APIs (not needed yet)
NEWSAPI_KEY=
ALPHAVANTAGE_KEY=
FLIGHTAWARE_API_KEY=
```

#### 10. Deployment Script

**File**: `scripts/deploy_facade_to_jetson.sh`

```bash
#!/bin/bash
# Deploy facade code from src/jetson to Jetson at /mnt/nvme/athena-lite

set -e

JETSON_USER="jstuart"
JETSON_HOST="192.168.10.62"
JETSON_PATH="/mnt/nvme/athena-lite"
LOCAL_SRC="src/jetson/facade"

echo "🚀 Deploying facade to Jetson..."

# 1. Create facade directory on Jetson
ssh ${JETSON_USER}@${JETSON_HOST} "mkdir -p ${JETSON_PATH}/facade/handlers ${JETSON_PATH}/facade/config ${JETSON_PATH}/facade/utils"

# 2. Copy facade module
scp -r ${LOCAL_SRC}/* ${JETSON_USER}@${JETSON_HOST}:${JETSON_PATH}/facade/

# 3. Copy updated main facade
scp research/jetson-iterations/ollama_baltimore_smart_facade.py ${JETSON_USER}@${JETSON_HOST}:${JETSON_PATH}/

# 4. Copy requirements.txt
scp src/jetson/requirements.txt ${JETSON_USER}@${JETSON_HOST}:${JETSON_PATH}/

# 5. Install dependencies on Jetson
echo "📦 Installing dependencies on Jetson..."
ssh ${JETSON_USER}@${JETSON_HOST} "cd ${JETSON_PATH} && pip3 install -r requirements.txt"

# 6. Restart facade service (if running as systemd service)
echo "🔄 Restarting facade service..."
ssh ${JETSON_USER}@${JETSON_HOST} "sudo systemctl restart ollama-facade || echo 'Service not configured yet'"

echo "✅ Deployment complete!"
echo "Test at: http://192.168.10.62:11434/health"
```

### Success Criteria

#### Automated Verification:

- [ ] Module structure created: `ls -la src/jetson/facade/`
- [ ] All imports work: `python3 -c "from facade.airbnb_intent_classifier import AirbnbIntentClassifier; print('OK')"`
- [ ] Weather API test: `python3 tests/facade/test_weather_handler.py`
- [ ] Web search test: `python3 tests/facade/test_web_search.py`
- [ ] Intent classification test: `python3 tests/facade/test_intent_classifier.py`
- [ ] Deployment script works: `bash scripts/deploy_facade_to_jetson.sh`
- [ ] Facade starts: `curl http://192.168.10.62:11434/health`

#### Manual Verification:

- [ ] Ask facade "What's the weather?" → Returns current Baltimore weather in <3s
- [ ] Ask "What's the weather tomorrow?" → Returns tomorrow's forecast
- [ ] Ask "What's the address?" → Returns property address (existing quick response)
- [ ] Ask "Where can I find good crab cakes?" → Returns Koco's Pub (existing response)
- [ ] Ask "What's the capital of France?" → Returns "Paris" via DuckDuckGo
- [ ] Ask "Tell me about BWI airport" → Returns BWI static info
- [ ] Ask "Tell me about JFK airport" → Returns JFK static info
- [ ] Ask complex query → Falls back to LLM gracefully
- [ ] Check logs show intent classifications: `ssh jstuart@192.168.10.62 "tail -f /mnt/nvme/athena-lite/logs/facade.log"`
- [ ] Verify caching works (ask same weather question twice, 2nd should be faster)

**Implementation Note**: After all automated tests pass and facade is deployed, manually test at least 10 different query types to verify coverage. Ensure performance is <500ms for cached, <3s for API calls.

---

## Phase 2: Travel & Events APIs

**Goal**: Add real-time flight tracking, local events discovery, and extended transportation information

### Overview

Integrate external APIs for:
- Flight status tracking (FlightAware API) for all 7 airports
- Local Baltimore events (Eventbrite, Ticketmaster APIs)
- Concert listings (Songkick, Bandsintown APIs)
- Extended transportation schedules (MTA, Water Taxi)

### Changes Required

#### 1. Flight Handler

**File**: `src/jetson/facade/handlers/flights.py`

```python
"""
Flight Handler - Real-time flight status tracking

API: FlightAware AeroAPI (free tier: 1000 queries/month)
Supports: Flight status, delays, airport operations for BWI, DCA, IAD, PHL, JFK, EWR, LGA
"""

import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FlightHandler:
    """Real-time flight tracking via FlightAware API"""

    FLIGHTAWARE_API = "https://aeroapi.flightaware.com/aeroapi"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes for flight data

    def get_flight_status(self, flight_number: str) -> str:
        """
        Get real-time status for specific flight

        Args:
            flight_number: e.g., "AA1234", "UA567"

        Returns:
            Natural language flight status
        """
        cache_key = f"flight_{flight_number.upper()}"
        cached = self._get_cached(cache_key)
        if cached:
            logger.info(f"✅ Flight cache hit: {flight_number}")
            return cached

        try:
            # FlightAware API endpoint
            url = f"{self.FLIGHTAWARE_API}/flights/{flight_number.upper()}"
            headers = {"x-apikey": self.api_key}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                flights = data.get('flights', [])

                if flights:
                    # Get most recent flight
                    flight = flights[0]

                    # Extract key info
                    origin = flight.get('origin', {}).get('code', 'Unknown')
                    destination = flight.get('destination', {}).get('code', 'Unknown')
                    status = flight.get('status', 'Unknown')

                    scheduled_dep = flight.get('scheduled_out', '')
                    actual_dep = flight.get('actual_out', '')
                    scheduled_arr = flight.get('scheduled_in', '')
                    estimated_arr = flight.get('estimated_in', '')

                    # Format response
                    response_text = f"{flight_number.upper()} from {origin} to {destination}: {status}"

                    # Add departure info
                    if actual_dep:
                        dep_time = self._format_time(actual_dep)
                        response_text += f". Departed {dep_time}"
                    elif scheduled_dep:
                        dep_time = self._format_time(scheduled_dep)
                        response_text += f". Scheduled departure {dep_time}"

                    # Add arrival info
                    if estimated_arr:
                        arr_time = self._format_time(estimated_arr)
                        response_text += f", estimated arrival {arr_time}"
                    elif scheduled_arr:
                        arr_time = self._format_time(scheduled_arr)
                        response_text += f", scheduled arrival {arr_time}"

                    self._set_cached(cache_key, response_text)
                    return response_text
                else:
                    return f"No flights found for {flight_number}. Make sure you have the correct flight number"

            elif response.status_code == 401:
                logger.error("❌ FlightAware API key invalid")
                return "I'm having trouble accessing flight data. Check FlightAware.com for status"

        except Exception as e:
            logger.error(f"❌ Flight status error for {flight_number}: {e}", exc_info=True)

        return "I couldn't get flight status right now. Check the airline website or FlightAware.com"

    def get_airport_delays(self, airport_code: str) -> str:
        """
        Get general delay information for airport

        Args:
            airport_code: BWI, DCA, IAD, PHL, JFK, EWR, LGA

        Returns:
            Airport delay status
        """
        cache_key = f"airport_delays_{airport_code.upper()}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            url = f"{self.FLIGHTAWARE_API}/airports/{airport_code.upper()}/delays"
            headers = {"x-apikey": self.api_key}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                delays = data.get('delays', {})

                if delays:
                    avg_delay = delays.get('average_delay_minutes', 0)
                    closure_msg = delays.get('closure_begin', '')

                    if closure_msg:
                        response_text = f"{airport_code.upper()} is experiencing closures or severe delays. Check with your airline"
                    elif avg_delay > 30:
                        response_text = f"{airport_code.upper()} has average delays of {avg_delay} minutes. Allow extra time"
                    elif avg_delay > 15:
                        response_text = f"{airport_code.upper()} has minor delays averaging {avg_delay} minutes"
                    else:
                        response_text = f"{airport_code.upper()} is operating normally with minimal delays"

                    self._set_cached(cache_key, response_text)
                    return response_text
                else:
                    return f"{airport_code.upper()} is operating normally"

        except Exception as e:
            logger.error(f"❌ Airport delays error for {airport_code}: {e}")

        return f"Check {airport_code.upper()} website for current delay information"

    def _format_time(self, timestamp: str) -> str:
        """Format ISO timestamp to readable time"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%I:%M %p')
        except:
            return timestamp

    def _get_cached(self, key: str) -> Optional[str]:
        if key in self.cache:
            cached = self.cache[key]
            age = datetime.now().timestamp() - cached['time']
            if age < self.cache_ttl:
                return cached['data']
        return None

    def _set_cached(self, key: str, data: str):
        self.cache[key] = {'data': data, 'time': datetime.now().timestamp()}
```

#### 2. Events Handler

**File**: `src/jetson/facade/handlers/events.py`

```python
"""
Events Handler - Local Baltimore events discovery

APIs:
- Eventbrite (primary): Free tier 1000 calls/day
- Ticketmaster (backup): Free tier 5000 calls/day
- Songkick (concerts): Free
- Bandsintown (concerts): Free
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EventsHandler:
    """Discover local Baltimore events and concerts"""

    # Baltimore coordinates for location-based search
    BALTIMORE_LAT = 39.2904
    BALTIMORE_LON = -76.6122
    SEARCH_RADIUS_MILES = 15

    def __init__(self, eventbrite_key: str, ticketmaster_key: str):
        self.eventbrite_key = eventbrite_key
        self.ticketmaster_key = ticketmaster_key
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour for events

    def get_events(self, timeframe: str = "today", category: Optional[str] = None) -> str:
        """
        Get Baltimore events for timeframe

        Args:
            timeframe: "today", "tomorrow", "weekend", "week"
            category: Optional category filter (concert, sports, etc.)

        Returns:
            Natural language event listing
        """
        cache_key = f"events_{timeframe}_{category or 'all'}"
        cached = self._get_cached(cache_key)
        if cached:
            logger.info(f"✅ Events cache hit: {timeframe}")
            return cached

        # Calculate date range
        start_date, end_date = self._get_date_range(timeframe)

        try:
            # Try Eventbrite first
            events = self._fetch_eventbrite(start_date, end_date, category)

            if not events:
                # Fallback to Ticketmaster
                events = self._fetch_ticketmaster(start_date, end_date, category)

            if events:
                response = self._format_events_response(events, timeframe)
                self._set_cached(cache_key, response)
                return response
            else:
                return f"No major events found for {timeframe} in Baltimore. Check baltimore.org/events or Eventbrite"

        except Exception as e:
            logger.error(f"❌ Events fetch error: {e}", exc_info=True)
            return "I'm having trouble getting events. Check baltimore.org/events or Eventbrite for listings"

    def _fetch_eventbrite(self, start_date: datetime, end_date: datetime, category: Optional[str]) -> List[Dict]:
        """Fetch events from Eventbrite API"""
        try:
            url = "https://www.eventbriteapi.com/v3/events/search/"
            headers = {"Authorization": f"Bearer {self.eventbrite_key}"}

            params = {
                'location.latitude': self.BALTIMORE_LAT,
                'location.longitude': self.BALTIMORE_LON,
                'location.within': f'{self.SEARCH_RADIUS_MILES}mi',
                'start_date.range_start': start_date.isoformat(),
                'start_date.range_end': end_date.isoformat(),
                'expand': 'venue',
                'sort_by': 'date'
            }

            if category:
                category_map = {
                    'concert': '103',  # Music
                    'comedy': '112',
                    'sports': '108',
                    'food': '110',
                    'festival': '113',
                }
                if category in category_map:
                    params['categories'] = category_map[category]

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                events_data = data.get('events', [])

                events = []
                for event in events_data[:5]:  # Top 5 events
                    events.append({
                        'name': event['name']['text'],
                        'venue': event.get('venue', {}).get('name', 'TBA'),
                        'start': event['start']['local'],
                        'url': event.get('url', '')
                    })

                return events

        except Exception as e:
            logger.error(f"❌ Eventbrite fetch error: {e}")

        return []

    def _fetch_ticketmaster(self, start_date: datetime, end_date: datetime, category: Optional[str]) -> List[Dict]:
        """Fetch events from Ticketmaster API (fallback)"""
        try:
            url = "https://app.ticketmaster.com/discovery/v2/events.json"

            params = {
                'apikey': self.ticketmaster_key,
                'latlong': f"{self.BALTIMORE_LAT},{self.BALTIMORE_LON}",
                'radius': self.SEARCH_RADIUS_MILES,
                'unit': 'miles',
                'startDateTime': start_date.isoformat() + 'Z',
                'endDateTime': end_date.isoformat() + 'Z',
                'sort': 'date,asc',
                'size': 5
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                embedded = data.get('_embedded', {})
                events_data = embedded.get('events', [])

                events = []
                for event in events_data:
                    venue_data = event.get('_embedded', {}).get('venues', [{}])[0]
                    events.append({
                        'name': event.get('name', 'Unknown Event'),
                        'venue': venue_data.get('name', 'TBA'),
                        'start': event.get('dates', {}).get('start', {}).get('localDate', ''),
                        'url': event.get('url', '')
                    })

                return events

        except Exception as e:
            logger.error(f"❌ Ticketmaster fetch error: {e}")

        return []

    def _get_date_range(self, timeframe: str) -> tuple:
        """Get start and end dates for timeframe"""
        now = datetime.now()

        if timeframe == "today":
            start = now
            end = now.replace(hour=23, minute=59, second=59)
        elif timeframe == "tomorrow":
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0)
            end = tomorrow.replace(hour=23, minute=59, second=59)
        elif timeframe == "weekend":
            # Find next Saturday
            days_ahead = 5 - now.weekday()  # Saturday is 5
            if days_ahead <= 0:
                days_ahead += 7
            saturday = now + timedelta(days=days_ahead)
            start = saturday.replace(hour=0, minute=0, second=0)
            end = (saturday + timedelta(days=1)).replace(hour=23, minute=59, second=59)  # Through Sunday
        else:  # "week"
            start = now
            end = now + timedelta(days=7)

        return start, end

    def _format_events_response(self, events: List[Dict], timeframe: str) -> str:
        """Format events list into natural language response"""
        if not events:
            return f"No events found for {timeframe}"

        response = f"Events {timeframe} in Baltimore:\n"
        for i, event in enumerate(events[:3], 1):  # Top 3
            name = event['name']
            venue = event['venue']
            start_time = self._format_datetime(event['start'])
            response += f"{i}) {name} at {venue} ({start_time})\n"

        if len(events) > 3:
            response += f"...and {len(events) - 3} more. Check baltimore.org/events or Eventbrite for full listings"

        return response.strip()

    def _format_datetime(self, datetime_str: str) -> str:
        """Format datetime to readable string"""
        try:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime('%a %I:%M %p')
        except:
            return datetime_str

    def _get_cached(self, key: str) -> Optional[str]:
        if key in self.cache:
            cached = self.cache[key]
            age = datetime.now().timestamp() - cached['time']
            if age < self.cache_ttl:
                return cached['data']
        return None

    def _set_cached(self, key: str, data: str):
        self.cache[key] = {'data': data, 'time': datetime.now().timestamp()}
```

#### 3. Update Main Facade (Phase 2 handlers)

**File**: `research/jetson-iterations/ollama_baltimore_smart_facade.py`

Add handlers to imports and initialization:

```python
from facade.handlers.flights import FlightHandler
from facade.handlers.events import EventsHandler

# Initialize Phase 2 handlers
flight_handler = FlightHandler(api_key=API_KEYS.get('flightaware'))
events_handler = EventsHandler(
    eventbrite_key=API_KEYS.get('eventbrite'),
    ticketmaster_key=API_KEYS.get('ticketmaster')
)
```

Update `analyze_query()` function to use Phase 2 handlers:

```python
elif handler_or_response == "airports":
    # Phase 2: Flight status API
    if data and data.get('type') == 'flight_status':
        # Extract flight number from query
        flight_num = self._extract_flight_number(data.get('query', ''))
        if flight_num:
            response = flight_handler.get_flight_status(flight_num)
        else:
            response = "Which flight number are you asking about? (e.g., AA1234)"
        return ('quick', response)

    # Static airport info (Phase 1)
    airport_code = data.get('airport_code')
    if airport_code and airport_code in AIRPORT_INFO:
        airport = AIRPORT_INFO[airport_code]
        response = airport['quick_response']
        return ('quick', response)

elif handler_or_response == "events":
    # Phase 2: Events API
    timeframe = data.get('timeframe', 'today')
    category = data.get('category')
    response = events_handler.get_events(timeframe, category)
    return ('quick', response)
```

#### 4. Update Requirements (Phase 2)

**File**: `src/jetson/requirements.txt`

No new dependencies needed (requests already included).

#### 5. Update Environment Config (Phase 2)

**File**: `/mnt/nvme/athena-lite/.env`

```bash
# Phase 2 APIs
FLIGHTAWARE_API_KEY=<get_from_flightaware.com>
EVENTBRITE_API_KEY=<get_from_eventbrite.com>
TICKETMASTER_API_KEY=<get_from_ticketmaster.com>
```

### Success Criteria

#### Automated Verification:

- [ ] Flight handler created: `ls src/jetson/facade/handlers/flights.py`
- [ ] Events handler created: `ls src/jetson/facade/handlers/events.py`
- [ ] Imports work: `python3 -c "from facade.handlers.flights import FlightHandler; print('OK')"`
- [ ] Flight test: `python3 tests/facade/test_flight_handler.py`
- [ ] Events test: `python3 tests/facade/test_events_handler.py`
- [ ] Deploy Phase 2: `bash scripts/deploy_facade_to_jetson.sh`

#### Manual Verification:

- [ ] Ask "Flight status for AA1234?" → Returns real-time status
- [ ] Ask "Are there delays at BWI?" → Returns airport delay info
- [ ] Ask "Events tonight in Baltimore?" → Returns 3 events from Eventbrite/Ticketmaster
- [ ] Ask "What's happening this weekend?" → Returns weekend events
- [ ] Ask "Concerts this week?" → Returns concert listings
- [ ] Verify caching (ask same flight twice, 2nd should be instant)
- [ ] Check logs show API calls: `tail -f /mnt/nvme/athena-lite/logs/facade.log`

---

## Phase 3: Entertainment Deep Dive

**Goal**: Add streaming service search, TV schedules, and concert discovery

### Overview

Integrate entertainment APIs:
- TMDb API for streaming content search ("Where can I watch X?")
- TVMaze API for TV schedules
- Songkick & Bandsintown for concert listings

### Changes Required

#### 1. Streaming Handler Enhancement

**File**: `src/jetson/facade/handlers/streaming.py`

```python
"""
Streaming Handler - Search across 10 streaming services

APIs:
- TMDb (primary): Movie/TV metadata, trending, recommendations - Free
- JustWatch (optional): Cross-platform availability - Free tier limited

Streaming services supported:
Netflix, Hulu, Disney+, HBO Max, Prime Video, Peacock, Paramount+, Apple TV+, YouTube TV, NFL Sunday Ticket
"""

import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class StreamingHandler:
    """Search for shows/movies across streaming platforms"""

    TMDB_API = "https://api.themoviedb.org/3"

    # TMDb provider IDs for our streaming services
    PROVIDER_IDS = {
        'netflix': 8,
        'hulu': 15,
        'disney+': 337,
        'hbo max': 384,
        'prime video': 9,
        'peacock': 387,
        'paramount+': 531,
        'apple tv+': 350,
        # YouTube TV not in TMDb (live TV service)
    }

    def __init__(self, tmdb_api_key: str):
        self.tmdb_key = tmdb_api_key
        self.cache = {}
        self.cache_ttl = 86400  # 24 hours for streaming data

    def search_content(self, query: str) -> str:
        """
        Search for show/movie across streaming services

        Args:
            query: "Where can I watch Breaking Bad?" or "Breaking Bad"

        Returns:
            Which service(s) have the content
        """
        # Extract title from query
        title = self._extract_title(query)

        cache_key = f"streaming_search_{title.lower()}"
        cached = self._get_cached(cache_key)
        if cached:
            logger.info(f"✅ Streaming search cache hit: {title}")
            return cached

        try:
            # Search TMDb for the content
            search_url = f"{self.TMDB_API}/search/multi"
            params = {
                'api_key': self.tmdb_key,
                'query': title,
                'page': 1
            }

            response = requests.get(search_url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                if results:
                    # Get first result (most relevant)
                    item = results[0]
                    item_id = item['id']
                    media_type = item['media_type']  # 'movie' or 'tv'

                    # Get watch providers for this content
                    providers_url = f"{self.TMDB_API}/{media_type}/{item_id}/watch/providers"
                    provider_params = {'api_key': self.tmdb_key}

                    provider_response = requests.get(providers_url, params=provider_params, timeout=10)

                    if provider_response.status_code == 200:
                        provider_data = provider_response.json()
                        us_providers = provider_data.get('results', {}).get('US', {})

                        # Check flatrate (subscription) providers
                        flatrate = us_providers.get('flatrate', [])

                        # Filter to only our available services
                        available_services = []
                        for provider in flatrate:
                            provider_name = provider['provider_name'].lower()
                            for service_name in self.PROVIDER_IDS.keys():
                                if service_name in provider_name or provider_name in service_name:
                                    available_services.append(service_name.title())
                                    break

                        if available_services:
                            services_str = ', '.join(set(available_services))
                            title_name = item.get('title') or item.get('name', title)
                            response_text = f"{title_name} is available on: {services_str}"
                            self._set_cached(cache_key, response_text)
                            return response_text
                        else:
                            return f"I don't see {title} on our streaming services. It might be available for rent/purchase or check JustWatch.com"
                    else:
                        return f"I found {title} but couldn't check which services have it. Try searching on JustWatch.com"
                else:
                    return f"I couldn't find '{title}'. Try searching directly on Netflix, Hulu, or HBO Max"

        except Exception as e:
            logger.error(f"❌ Streaming search error for '{title}': {e}", exc_info=True)

        return "I'm having trouble searching streaming services. Try JustWatch.com to find where to watch"

    def get_trending(self, service: Optional[str] = None) -> str:
        """Get trending content (static fallback for Phase 3)"""
        if service:
            return f"Check the 'Trending' or 'Popular' section on {service.title()}"
        else:
            return "Check 'Trending Now' sections on Netflix, HBO Max, or Hulu for what's popular"

    def _extract_title(self, query: str) -> str:
        """
        Extract show/movie title from natural language query

        Examples:
            "Where can I watch Breaking Bad?" → "Breaking Bad"
            "Is The Last of Us on HBO?" → "The Last of Us"
            "Breaking Bad" → "Breaking Bad"
        """
        import re

        # Remove common question phrases
        patterns = [
            r"where (?:can|do) (?:i|we) watch\s+(.+?)(?:\?|$)",
            r"is (.+?) on (?:netflix|hulu|disney|hbo|prime|peacock|paramount|apple)",
            r"(?:find|search (?:for)?)\s+(.+?)(?:\?|$)",
            r"(.+)",  # Fallback: entire query is title
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                title = match.group(1).strip()
                # Clean up
                title = title.replace('?', '').replace('the show', '').replace('the movie', '').strip()
                return title

        return query

    def _get_cached(self, key: str) -> Optional[str]:
        if key in self.cache:
            from datetime import datetime
            cached = self.cache[key]
            age = datetime.now().timestamp() - cached['time']
            if age < self.cache_ttl:
                return cached['data']
        return None

    def _set_cached(self, key: str, data: str):
        from datetime import datetime
        self.cache[key] = {'data': data, 'time': datetime.now().timestamp()}
```

#### 2. Update Main Facade (Phase 3 handlers)

**File**: `research/jetson-iterations/ollama_baltimore_smart_facade.py`

Update streaming handler initialization and usage:

```python
from facade.handlers.streaming import StreamingHandler

# Initialize Phase 3 handler
streaming_handler = StreamingHandler(tmdb_api_key=API_KEYS.get('tmdb'))

# In analyze_query():
elif handler_or_response == "streaming":
    # Phase 3: Streaming search API
    if data and data.get('type') == 'search':
        response = streaming_handler.search_content(data.get('query', ''))
        return ('quick', response)
    # Phase 1 static responses still available for service lists
```

#### 3. Update Environment (Phase 3)

**File**: `/mnt/nvme/athena-lite/.env`

```bash
# Phase 3 APIs
TMDB_API_KEY=<get_from_themoviedb.org>  # Free, no credit card
SONGKICK_API_KEY=<get_from_songkick.com>  # Free
BANDSINTOWN_API_KEY=<get_from_bandsintown.com>  # Free
```

### Success Criteria

#### Automated Verification:

- [ ] Streaming handler enhanced: `ls src/jetson/facade/handlers/streaming.py`
- [ ] Imports work: `python3 -c "from facade.handlers.streaming import StreamingHandler; print('OK')"`
- [ ] Streaming search test: `python3 tests/facade/test_streaming_handler.py`
- [ ] Deploy Phase 3: `bash scripts/deploy_facade_to_jetson.sh`

#### Manual Verification:

- [ ] Ask "Where can I watch The Last of Us?" → Returns "HBO Max"
- [ ] Ask "Is Breaking Bad on Netflix?" → Returns "Yes, Breaking Bad is on Netflix"
- [ ] Ask "Where can I watch The Mandalorian?" → Returns "Disney+"
- [ ] Ask "What streaming services do you have?" → Returns list of 10 services
- [ ] Ask unknown show → Returns helpful fallback message
- [ ] Verify caching works (same show search twice)

---

## Phase 4: News & Finance

**Goal**: Add news headlines and stock market data

### Overview

Final phase adds:
- NewsAPI.org for Baltimore local + national news
- Alpha Vantage for stock quotes and market indices
- Sports news integration (ESPN API or web scraping)

### Changes Required

#### 1. News Handler

**File**: `src/jetson/facade/handlers/news.py`

```python
"""
News Handler - Local Baltimore and national news

API: NewsAPI.org (free tier: 100 calls/day)
Sources: Baltimore Sun, WBAL, national news
"""

import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class NewsHandler:
    """Fetch news headlines"""

    NEWSAPI_URL = "https://newsapi.org/v2"

    # Baltimore news sources
    BALTIMORE_SOURCES = [
        'baltimore-sun',  # If available in NewsAPI
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache = {}
        self.cache_ttl = 1800  # 30 minutes for news

    def get_news(self, news_type: str = "local", topic: Optional[str] = None) -> str:
        """
        Get news headlines

        Args:
            news_type: "local" (Baltimore), "national", "sports"
            topic: Optional topic filter (ravens, orioles, etc.)

        Returns:
            Top 3-5 headlines
        """
        cache_key = f"news_{news_type}_{topic or 'general'}"
        cached = self._get_cached(cache_key)
        if cached:
            logger.info(f"✅ News cache hit: {news_type}")
            return cached

        try:
            if news_type == "local":
                articles = self._fetch_local_news()
            elif news_type == "national":
                articles = self._fetch_national_news()
            elif news_type == "sports":
                articles = self._fetch_sports_news(topic)
            else:
                articles = self._fetch_national_news()

            if articles:
                response = self._format_news_response(articles, news_type)
                self._set_cached(cache_key, response)
                return response
            else:
                return self._get_fallback_message(news_type)

        except Exception as e:
            logger.error(f"❌ News fetch error: {e}", exc_info=True)
            return self._get_fallback_message(news_type)

    def _fetch_local_news(self) -> List[Dict]:
        """Fetch Baltimore local news"""
        try:
            url = f"{self.NEWSAPI_URL}/everything"
            params = {
                'apiKey': self.api_key,
                'q': 'Baltimore',
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': 5
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('articles', [])[:3]

        except Exception as e:
            logger.error(f"❌ Local news fetch error: {e}")

        return []

    def _fetch_national_news(self) -> List[Dict]:
        """Fetch national headlines"""
        try:
            url = f"{self.NEWSAPI_URL}/top-headlines"
            params = {
                'apiKey': self.api_key,
                'country': 'us',
                'pageSize': 5
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('articles', [])[:5]

        except Exception as e:
            logger.error(f"❌ National news fetch error: {e}")

        return []

    def _fetch_sports_news(self, topic: Optional[str]) -> List[Dict]:
        """Fetch sports news"""
        try:
            url = f"{self.NEWSAPI_URL}/everything"

            # Build query for sports
            query = topic if topic else "NFL OR MLB OR sports"

            params = {
                'apiKey': self.api_key,
                'q': query,
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': 3
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('articles', [])[:3]

        except Exception as e:
            logger.error(f"❌ Sports news fetch error: {e}")

        return []

    def _format_news_response(self, articles: List[Dict], news_type: str) -> str:
        """Format news articles into response"""
        if not articles:
            return self._get_fallback_message(news_type)

        response = f"{'Baltimore' if news_type == 'local' else 'Top'} news:\n"
        for i, article in enumerate(articles[:3], 1):
            title = article.get('title', 'No title')
            # Truncate long titles
            if len(title) > 80:
                title = title[:77] + "..."
            response += f"{i}) {title}\n"

        return response.strip()

    def _get_fallback_message(self, news_type: str) -> str:
        """Fallback message if news fetch fails"""
        if news_type == "local":
            return "Check baltimoresun.com or wbaltv.com for local Baltimore news"
        elif news_type == "sports":
            return "Check ESPN.com or TheSportsDB for sports news"
        else:
            return "Check news.google.com or npr.org for national headlines"

    def _get_cached(self, key: str) -> Optional[str]:
        if key in self.cache:
            cached = self.cache[key]
            age = datetime.now().timestamp() - cached['time']
            if age < self.cache_ttl:
                return cached['data']
        return None

    def _set_cached(self, key: str, data: str):
        self.cache[key] = {'data': data, 'time': datetime.now().timestamp()}
```

#### 2. Stocks Handler

**File**: `src/jetson/facade/handlers/stocks.py`

```python
"""
Stocks Handler - Stock quotes and market indices

API: Alpha Vantage (free tier: 500 calls/day)
Supports: Individual stocks, market indices (Dow, Nasdaq, S&P)
"""

import requests
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StocksHandler:
    """Fetch stock quotes and market data"""

    ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"

    # Common stock name to ticker mapping
    STOCK_MAP = {
        'apple': 'AAPL',
        'google': 'GOOGL',
        'amazon': 'AMZN',
        'tesla': 'TSLA',
        'microsoft': 'MSFT',
        'meta': 'META',
        'facebook': 'META',
        'netflix': 'NFLX',
    }

    # Market indices
    INDICES = {
        'dow': 'DJI',
        'dow jones': 'DJI',
        'nasdaq': 'IXIC',
        's&p': 'SPX',
        's&p 500': 'SPX',
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes for stock data

    def get_stock_quote(self, query: str) -> str:
        """
        Get stock quote from query

        Args:
            query: "AAPL stock price" or "How's Apple doing?" or "Dow Jones"

        Returns:
            Stock price info
        """
        # Extract ticker symbol
        ticker = self._extract_ticker(query)

        if not ticker:
            return "Which stock are you asking about? Try using the ticker symbol (e.g., AAPL, GOOGL, TSLA)"

        cache_key = f"stock_{ticker.upper()}"
        cached = self._get_cached(cache_key)
        if cached:
            logger.info(f"✅ Stock cache hit: {ticker}")
            return cached

        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': ticker.upper(),
                'apikey': self.api_key
            }

            response = requests.get(self.ALPHAVANTAGE_URL, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                quote = data.get('Global Quote', {})

                if quote:
                    symbol = quote.get('01. symbol', ticker.upper())
                    price = float(quote.get('05. price', 0))
                    change = float(quote.get('09. change', 0))
                    change_pct = float(quote.get('10. change percent', '0').replace('%', ''))

                    # Format response
                    direction = "up" if change >= 0 else "down"
                    response_text = f"{symbol}: ${price:.2f} ({direction} {abs(change_pct):.2f}%, ${abs(change):.2f})"

                    self._set_cached(cache_key, response_text)
                    return response_text
                else:
                    return f"I couldn't find stock data for {ticker.upper()}. Make sure the ticker symbol is correct"

        except Exception as e:
            logger.error(f"❌ Stock quote error for {ticker}: {e}", exc_info=True)

        return "I'm having trouble getting stock data. Check finance.yahoo.com or Google Finance"

    def get_market_summary(self) -> str:
        """Get summary of major market indices (limited by API rate)"""
        # Note: Alpha Vantage free tier is limited, so this is a simplified version
        return "For market summary (Dow, Nasdaq, S&P), check finance.yahoo.com or Google Finance"

    def _extract_ticker(self, query: str) -> Optional[str]:
        """
        Extract stock ticker from query

        Examples:
            "AAPL stock price" → "AAPL"
            "How's Apple doing?" → "AAPL"
            "Tesla stock" → "TSLA"
        """
        import re

        q = query.lower()

        # Check if query contains exact ticker (all caps, 1-5 letters)
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', query)
        if ticker_match:
            return ticker_match.group(1)

        # Check common stock names
        for name, ticker in self.STOCK_MAP.items():
            if name in q:
                return ticker

        # Check market indices
        for name, ticker in self.INDICES.items():
            if name in q:
                return ticker

        return None

    def _get_cached(self, key: str) -> Optional[str]:
        if key in self.cache:
            cached = self.cache[key]
            age = datetime.now().timestamp() - cached['time']
            if age < self.cache_ttl:
                return cached['data']
        return None

    def _set_cached(self, key: str, data: str):
        self.cache[key] = {'data': data, 'time': datetime.now().timestamp()}
```

#### 3. Update Main Facade (Phase 4 handlers)

**File**: `research/jetson-iterations/ollama_baltimore_smart_facade.py`

```python
from facade.handlers.news import NewsHandler
from facade.handlers.stocks import StocksHandler

# Initialize Phase 4 handlers
news_handler = NewsHandler(api_key=API_KEYS.get('newsapi'))
stocks_handler = StocksHandler(api_key=API_KEYS.get('alphavantage'))

# In analyze_query():
elif handler_or_response == "news":
    # Phase 4: News API
    news_type = data.get('type', 'national')
    topic = data.get('topic')
    response = news_handler.get_news(news_type, topic)
    return ('quick', response)

elif handler_or_response == "stocks":
    # Phase 4: Stocks API
    response = stocks_handler.get_stock_quote(data.get('query', ''))
    return ('quick', response)
```

#### 4. Update Environment (Phase 4)

**File**: `/mnt/nvme/athena-lite/.env`

```bash
# Phase 4 APIs
NEWSAPI_KEY=<get_from_newsapi.org>  # Free tier: 100 calls/day
ALPHAVANTAGE_KEY=<get_from_alphavantage.co>  # Free tier: 500 calls/day
```

### Success Criteria

#### Automated Verification:

- [ ] News handler created: `ls src/jetson/facade/handlers/news.py`
- [ ] Stocks handler created: `ls src/jetson/facade/handlers/stocks.py`
- [ ] Imports work: `python3 -c "from facade.handlers.news import NewsHandler; print('OK')"`
- [ ] News test: `python3 tests/facade/test_news_handler.py`
- [ ] Stocks test: `python3 tests/facade/test_stocks_handler.py`
- [ ] Deploy Phase 4: `bash scripts/deploy_facade_to_jetson.sh`

#### Manual Verification:

- [ ] Ask "What's the news in Baltimore?" → Returns 3 local headlines
- [ ] Ask "Top headlines?" → Returns 5 national headlines
- [ ] Ask "AAPL stock price?" → Returns Apple stock price with change
- [ ] Ask "How's Tesla stock doing?" → Returns TSLA quote
- [ ] Ask "Ravens news?" → Returns sports news about Ravens
- [ ] Verify all 4 phases work together (weather, flights, events, news, stocks)
- [ ] Performance check: All queries <3s, cached <500ms

---

## Testing Strategy

### Unit Tests

**Location**: `tests/facade/`

#### Test Files Structure

```
tests/facade/
├── __init__.py
├── test_intent_classifier.py     # Intent classification accuracy
├── test_weather_handler.py        # Weather API integration
├── test_web_search.py             # DuckDuckGo search
├── test_flights.py                # Flight status API
├── test_events.py                 # Events API
├── test_streaming.py              # Streaming search
├── test_news.py                   # News API
├── test_stocks.py                 # Stocks API
└── test_integration.py            # End-to-end tests
```

#### Example Test: Intent Classifier

**File**: `tests/facade/test_intent_classifier.py`

```python
import pytest
from src.jetson.facade.airbnb_intent_classifier import AirbnbIntentClassifier, IntentType


class TestIntentClassifier:
    """Test intent classification accuracy"""

    @pytest.fixture
    def classifier(self):
        return AirbnbIntentClassifier()

    def test_weather_queries(self, classifier):
        """Test weather intent detection"""
        test_cases = [
            ("what's the weather?", IntentType.API_CALL, "weather"),
            ("weather tomorrow", IntentType.API_CALL, "weather"),
            ("is it going to rain?", IntentType.API_CALL, "weather"),
            ("temperature today", IntentType.API_CALL, "weather"),
        ]

        for query, expected_type, expected_handler in test_cases:
            intent_type, handler, data = classifier.classify(query)
            assert intent_type == expected_type, f"Failed for: {query}"
            assert handler == expected_handler, f"Wrong handler for: {query}"

    def test_location_queries(self, classifier):
        """Test location quick responses"""
        test_cases = [
            ("what's the address?", IntentType.QUICK),
            ("where am I?", IntentType.QUICK),
            ("how far is Inner Harbor?", IntentType.QUICK),
            ("best crab cakes?", IntentType.QUICK),
        ]

        for query, expected_type in test_cases:
            intent_type, handler, data = classifier.classify(query)
            assert intent_type == expected_type, f"Failed for: {query}"

    def test_transportation_queries(self, classifier):
        """Test transportation intent detection"""
        test_cases = [
            ("tell me about BWI airport", IntentType.API_CALL, "airports"),
            ("flight status for AA1234", IntentType.API_CALL, "airports"),
            ("where can I park?", IntentType.QUICK),
        ]

        for query, expected_type, expected_handler in test_cases:
            intent_type, handler, data = classifier.classify(query)
            assert intent_type == expected_type, f"Failed for: {query}"
            if expected_handler:
                assert handler == expected_handler, f"Wrong handler for: {query}"

    def test_entertainment_queries(self, classifier):
        """Test entertainment intent detection"""
        test_cases = [
            ("where can I watch The Last of Us?", IntentType.API_CALL, "streaming"),
            ("what streaming services do you have?", IntentType.QUICK),
            ("events tonight?", IntentType.API_CALL, "events"),
        ]

        for query, expected_type, expected_handler in test_cases:
            intent_type, handler, data = classifier.classify(query)
            assert intent_type == expected_type, f"Failed for: {query}"
            if expected_handler:
                assert handler == expected_handler, f"Wrong handler for: {query}"

    def test_web_search_fallback(self, classifier):
        """Test web search fallback detection"""
        test_cases = [
            "who is the mayor of Baltimore?",
            "what time does Koco's Pub close?",
            "phone number for Canton Water Taxi",
            "latest news about Baltimore",
        ]

        for query in test_cases:
            intent_type, handler, data = classifier.classify(query)
            assert intent_type == IntentType.WEB_SEARCH, f"Should trigger web search for: {query}"

    def test_llm_fallback(self, classifier):
        """Test LLM fallback for complex queries"""
        test_cases = [
            "what's the best way to spend a weekend in Baltimore?",
            "explain the history of Fort McHenry",
            "compare Ravens and Steelers",
        ]

        for query in test_cases:
            intent_type, handler, data = classifier.classify(query)
            assert intent_type == IntentType.LLM, f"Should route to LLM for: {query}"
```

#### Example Test: Weather Handler

**File**: `tests/facade/test_weather_handler.py`

```python
import pytest
from unittest.mock import Mock, patch
from src.jetson.facade.handlers.weather import WeatherHandler


class TestWeatherHandler:
    """Test weather API integration"""

    @pytest.fixture
    def handler(self):
        return WeatherHandler(openweather_api_key="test_key")

    @patch('requests.get')
    def test_current_weather_success(self, mock_get, handler):
        """Test successful current weather fetch"""
        # Mock Weather.gov forecast response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'properties': {
                'periods': [{
                    'temperature': 65,
                    'shortForecast': 'Sunny',
                    'windSpeed': '5 mph'
                }]
            }
        }
        mock_get.return_value = mock_response

        result = handler.get_weather("current")

        assert "65°F" in result
        assert "sunny" in result.lower()
        assert "wind" in result.lower()

    @patch('requests.get')
    def test_weather_caching(self, mock_get, handler):
        """Test weather results are cached"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'properties': {
                'periods': [{'temperature': 70, 'shortForecast': 'Clear'}]
            }
        }
        mock_get.return_value = mock_response

        # First call
        result1 = handler.get_weather("current")
        # Second call (should be cached)
        result2 = handler.get_weather("current")

        assert result1 == result2
        assert mock_get.call_count == 2  # Grid point + forecast

    def test_invalid_timeframe_defaults_to_current(self, handler):
        """Test invalid timeframe defaults to current weather"""
        result = handler.get_weather("invalid_timeframe")
        assert isinstance(result, str)
```

### Integration Tests

**File**: `tests/facade/test_integration.py`

```python
import pytest
from research.jetson_iterations.ollama_baltimore_smart_facade import analyze_query


class TestFacadeIntegration:
    """End-to-end integration tests"""

    def test_weather_query_flow(self):
        """Test complete weather query flow"""
        query_type, response = analyze_query("what's the weather?")

        assert query_type == 'quick'
        assert isinstance(response, str)
        # Should contain temperature
        assert '°F' in response or 'weather' in response.lower()

    def test_location_query_flow(self):
        """Test location quick response"""
        query_type, response = analyze_query("what's the address?")

        assert query_type == 'quick'
        assert "912 South Clinton" in response
        assert "Baltimore" in response

    def test_web_search_fallback_flow(self):
        """Test web search fallback integration"""
        query_type, response = analyze_query("who is the mayor of Baltimore?")

        assert query_type == 'quick'
        assert isinstance(response, str)
        # Should not be empty
        assert len(response) > 0

    def test_unknown_query_llm_fallback(self):
        """Test LLM fallback for complex queries"""
        query_type, response = analyze_query("tell me a long story about Baltimore")

        assert query_type == 'llm'
        assert response == 'general'
```

### Performance Benchmarks

**File**: `tests/facade/benchmark_response_times.py`

```python
import time
from research.jetson_iterations.ollama_baltimore_smart_facade import analyze_query


def benchmark_query(query: str, iterations: int = 10):
    """Benchmark query response time"""
    times = []

    for _ in range(iterations):
        start = time.time()
        analyze_query(query)
        elapsed = (time.time() - start) * 1000  # ms
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]

    return avg_time, p95_time


def run_benchmarks():
    """Run performance benchmarks"""
    test_queries = [
        ("what's the address?", "Quick response (cached)"),
        ("what's the weather?", "Weather API call"),
        ("events tonight?", "Events API call"),
        ("where can I watch Breaking Bad?", "Streaming search"),
        ("AAPL stock price?", "Stock quote"),
    ]

    print("=== Facade Performance Benchmarks ===\n")

    for query, description in test_queries:
        avg, p95 = benchmark_query(query, iterations=5)
        print(f"{description}")
        print(f"  Query: {query}")
        print(f"  Avg: {avg:.0f}ms | P95: {p95:.0f}ms")
        print()

    print("\n=== Performance Targets ===")
    print("✅ Quick responses: <500ms")
    print("✅ API calls: <3000ms")
    print("✅ Cache hit rate: >70%")


if __name__ == '__main__':
    run_benchmarks()
```

### Manual Test Plan

**File**: `tests/facade/MANUAL_TEST_PLAN.md`

```markdown
# Facade Manual Test Plan

## Phase 1: Core Infrastructure

### Weather Queries
- [ ] "What's the weather?" → Current conditions in <3s
- [ ] "Weather tomorrow?" → Tomorrow's forecast
- [ ] "How's the weather this weekend?" → Weekend forecast
- [ ] Same query twice → 2nd response instant (<100ms, cached)

### Location Queries (Existing)
- [ ] "What's the address?" → Returns property address
- [ ] "Where am I?" → Returns neighborhood
- [ ] "Best crab cakes?" → Returns Koco's Pub
- [ ] "How far is Inner Harbor?" → Returns distance

### Web Search Fallback
- [ ] "Who is the mayor of Baltimore?" → Web search result
- [ ] "What time does Koco's close?" → Business hours
- [ ] "Unknown random fact?" → DuckDuckGo answer or fallback

## Phase 2: Travel & Events

### Flights
- [ ] "Flight status for AA1234?" → Real-time status
- [ ] "Are there delays at BWI?" → Airport delay info
- [ ] "Tell me about DCA airport?" → Airport details

### Events
- [ ] "Events tonight in Baltimore?" → 3 events from Eventbrite
- [ ] "What's happening this weekend?" → Weekend events
- [ ] "Concerts this week?" → Concert listings

## Phase 3: Entertainment

### Streaming
- [ ] "Where can I watch The Last of Us?" → "HBO Max"
- [ ] "Is Breaking Bad on Netflix?" → "Yes, Breaking Bad is on Netflix"
- [ ] "What streaming services do you have?" → List of 10 services

## Phase 4: News & Finance

### News
- [ ] "What's the news in Baltimore?" → 3 local headlines
- [ ] "Top headlines?" → 5 national headlines
- [ ] "Ravens news?" → Sports news

### Stocks
- [ ] "AAPL stock price?" → Apple stock quote
- [ ] "How's Tesla doing?" → TSLA quote
- [ ] "Dow Jones?" → Market index info

## Performance Checks

- [ ] All cached responses <500ms
- [ ] All API calls <3s (except on first run)
- [ ] No errors in logs
- [ ] Cache hit rate >70% (check metrics)

## Error Handling

- [ ] Offline weather API → Graceful fallback message
- [ ] Invalid flight number → Helpful error
- [ ] Unknown stock ticker → Suggests using ticker symbol
- [ ] API rate limit hit → Fallback message

## Cross-Phase Integration

- [ ] Ask 10 different query types in sequence → All work
- [ ] Mix of weather, events, flights, streaming → No conflicts
- [ ] Rapid queries → Cache works, no slowdown
```

### Automated Test Execution

```bash
# Run all unit tests
python -m pytest tests/facade/ -v --cov=src/jetson/facade --cov-report=term-missing

# Run integration tests only
python -m pytest tests/facade/test_integration.py -v

# Run performance benchmarks
python tests/facade/benchmark_response_times.py

# Run specific handler tests
python -m pytest tests/facade/test_weather_handler.py -v
python -m pytest tests/facade/test_flights.py -v
```

---

## Performance Considerations

### Caching Strategy

**Multi-Tier Caching System**:

1. **In-Memory Cache** (already implemented in handlers)
   - Weather: 10 minutes
   - Events: 1 hour
   - Streaming search: 24 hours
   - News: 30 minutes
   - Stocks: 5 minutes
   - Web search: 1 hour

2. **Cache Size Management**:
```python
# Add to each handler
def _cleanup_cache(self):
    """Remove expired entries"""
    now = datetime.now().timestamp()
    expired_keys = [
        k for k, v in self.cache.items()
        if now - v['time'] > self.cache_ttl
    ]
    for key in expired_keys:
        del self.cache[key]
```

3. **Cache Metrics**:
```python
# Add to facade
cache_hits = 0
cache_misses = 0
total_queries = 0

def get_cache_metrics():
    """Return cache performance stats"""
    hit_rate = (cache_hits / total_queries * 100) if total_queries > 0 else 0
    return {
        'hit_rate': f"{hit_rate:.1f}%",
        'hits': cache_hits,
        'misses': cache_misses,
        'total': total_queries
    }
```

### API Rate Limiting

**Per-API Limits** (from research):
- OpenWeatherMap: 1000 calls/day (Phase 1)
- Eventbrite: 1000 calls/day (Phase 2)
- Ticketmaster: 5000 calls/day (Phase 2)
- FlightAware: ~1000 calls/month (Phase 2)
- TMDb: Unlimited (Phase 3)
- NewsAPI: 100 calls/day (Phase 4)
- Alpha Vantage: 500 calls/day (Phase 4)

**Rate Limit Strategy**:

1. **Request Counting**:
```python
# Add to api_config.py
request_counts = {
    'openweather': 0,
    'eventbrite': 0,
    'newsapi': 0,
    'alphavantage': 0,
}

def check_rate_limit(api_name: str) -> bool:
    """Check if API rate limit allows request"""
    if api_name not in RATE_LIMITS:
        return True

    if request_counts.get(api_name, 0) >= RATE_LIMITS[api_name]:
        logger.warning(f"⚠️ Rate limit reached for {api_name}")
        return False

    return True

def increment_request_count(api_name: str):
    """Increment API request counter"""
    request_counts[api_name] = request_counts.get(api_name, 0) + 1
```

2. **Daily Reset**:
```python
# Add to facade startup
import schedule

def reset_rate_limits():
    """Reset all rate limit counters (runs daily at midnight)"""
    for key in request_counts:
        request_counts[key] = 0
    logger.info("🔄 Rate limits reset")

schedule.every().day.at("00:00").do(reset_rate_limits)
```

3. **Fallback Messages**:
```python
RATE_LIMIT_FALLBACKS = {
    'openweather': "Weather data unavailable. Check weather.com",
    'newsapi': "News unavailable. Check baltimoresun.com or npr.org",
    'alphavantage': "Stock data unavailable. Check finance.yahoo.com",
}
```

### Response Time Optimization

**Performance Targets**:
- Quick responses (cached/static): **<500ms** (P95)
- API calls (first time): **<3000ms** (P95)
- Cache hit rate: **>70%** after warm-up

**Optimization Techniques**:

1. **Parallel API Calls** (for complex queries):
```python
import concurrent.futures

def fetch_multiple_apis(queries):
    """Fetch from multiple APIs in parallel"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(weather_handler.get_weather, 'current'): 'weather',
            executor.submit(events_handler.get_events, 'today'): 'events',
            executor.submit(news_handler.get_news, 'local'): 'news',
        }

        results = {}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result(timeout=3)
            except Exception as e:
                logger.error(f"Error fetching {key}: {e}")
                results[key] = None

        return results
```

2. **Connection Pooling**:
```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Create session with connection pooling
session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Use session in handlers instead of requests.get()
response = session.get(url, params=params, timeout=5)
```

3. **Lazy Loading**:
```python
# Don't initialize all handlers on startup, only when needed
class LazyHandlerLoader:
    """Lazy load handlers only when first used"""

    def __init__(self):
        self._weather = None
        self._events = None
        self._news = None

    @property
    def weather(self):
        if self._weather is None:
            self._weather = WeatherHandler(API_KEYS.get('openweather'))
        return self._weather

    # Similar for other handlers
```

### Error Handling & Recovery

**Graceful Degradation**:

1. **API Failure Cascade**:
```python
def get_weather_with_fallback(timeframe):
    """Try multiple weather sources with fallback"""
    try:
        # Try Weather.gov first
        return weather_handler._get_current_weather()
    except Exception as e:
        logger.warning(f"Weather.gov failed: {e}")

        try:
            # Fallback to OpenWeatherMap
            return weather_handler._get_from_openweather()
        except Exception as e2:
            logger.error(f"OpenWeatherMap failed: {e2}")

            # Final fallback
            return "Weather data unavailable. Check weather.com or Weather Channel app"
```

2. **Timeout Management**:
```python
# All API calls must have timeouts
TIMEOUTS = {
    'weather': 5,  # seconds
    'events': 10,
    'flights': 10,
    'news': 5,
    'stocks': 5,
    'web_search': 5,
}
```

3. **Health Monitoring**:
```python
# Add to facade
@app.route('/metrics', methods=['GET'])
def metrics():
    """Return performance and health metrics"""
    return jsonify({
        'cache': get_cache_metrics(),
        'rate_limits': {
            api: f"{count}/{limit}"
            for api, (count, limit) in zip(request_counts.keys(), RATE_LIMITS.values())
        },
        'api_health': {
            'weather': weather_handler.is_healthy(),
            'events': events_handler.is_healthy(),
            'news': news_handler.is_healthy(),
        },
        'uptime': get_uptime(),
        'total_queries': total_queries,
    })
```

### Resource Management

**Memory Usage**:
- Each handler cache: ~10MB max
- Total facade memory: ~100MB target
- Cleanup old cache entries every hour

**CPU Usage**:
- Intent classification: <10ms
- JSON parsing: <5ms
- Response formatting: <5ms

**Network**:
- Keep-alive connections to frequent APIs
- Connection pooling (10 connections per API)
- Timeouts to prevent hanging requests

---

## Migration Notes

No data migration needed - this is net new functionality.

**Deployment Checklist**:
1. Get API keys for all services (see `.env.example`)
2. Test each phase independently before deploying next phase
3. Monitor logs during first week: `tail -f /mnt/nvme/athena-lite/logs/facade.log`
4. Track cache hit rates via `/metrics` endpoint
5. Adjust cache TTLs based on guest query patterns

---

## References

- **Research**: `thoughts/shared/research/RESEARCH_FACADE_INTENT_CLASSIFICATIONS_MISSING.md`
- **Existing Facade**: `research/jetson-iterations/ollama_baltimore_smart_facade.py:1-304`
- **Existing Intent Classifier** (voice): `src/jetson/intent_classifier.py:1-257` (different use case)
- **Requirements**: `src/jetson/requirements.txt:1-17`

**API Documentation**:
- Weather.gov API: https://www.weather.gov/documentation/services-web-api
- OpenWeatherMap: https://openweathermap.org/api
- DuckDuckGo Instant Answer: https://duckduckgo.com/api
- Eventbrite: https://www.eventbrite.com/platform/api
- Ticketmaster: https://developer.ticketmaster.com/
- TMDb: https://www.themoviedb.org/documentation/api
- NewsAPI: https://newsapi.org/docs
- Alpha Vantage: https://www.alphavantage.co/documentation/
- FlightAware: https://flightaware.com/commercial/aeroapi/
