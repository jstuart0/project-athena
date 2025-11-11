---
date: 2025-01-08T13:50:00-05:00
author: Claude Code
git_commit: e340f6fb8a9288bcaa31ab78a2da48d525a66e48
branch: main
repository: project-athena
topic: "Comprehensive Pattern Coverage Expansion for Airbnb Intent Classifier"
tags: [implementation-plan, facade, intent-classification, pattern-matching, airbnb]
status: draft
last_updated: 2025-01-08
last_updated_by: Claude Code
---

# Comprehensive Pattern Coverage Expansion for Airbnb Intent Classifier

## Overview

Systematically expand pattern matching coverage across all 7 intent categories in the Airbnb Intent Classifier to handle ~230+ missing natural language query variations. This will eliminate cases where queries fall through to the LLM (returning entity dumps) or route to incorrect handlers.

## Current State Analysis

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/facade/airbnb_intent_classifier.py`

**Current Implementation:**
- Pattern-based classification using substring matching on lowercase queries
- 7 intent categories: Time/Date, Weather, Location, Transportation, Entertainment, News/Finance/Sports, Web Search
- Cascading fallback: specialized handlers → web search → LLM

**Pattern Coverage Gaps:**
- Time/Date (lines 104-123): ~17 missing patterns
- Weather (lines 125-143): ~37 missing patterns
- Location (lines 145-191): ~25 missing patterns
- Transportation (lines 193-244): ~33 missing patterns
- Entertainment (lines 246-309): ~36 missing patterns
- News/Finance/Sports (lines 311-333): ~29 missing patterns + conflicts
- Web Search (lines 335-365): ~55 missing patterns

**Total: ~230+ missing pattern variations**

**Critical Issues:**
1. Pattern conflicts: "who won" in web_search (line 349) should be in sports (line 329)
2. Entity dumps: Unknown queries fall to LLM which returns raw Home Assistant device JSON
3. Incorrect routing: Common queries like "what's it like outside" fall to LLM instead of weather handler

**Recent Fixes (Partial):**
- Restaurant recommendations: Added `'recommendation'` keyword ✅
- Flight search: Added search pattern detection ✅
- Events: Added `'tell me about'` pattern ✅

These fixes only addressed 3 of 230+ issues.

## Desired End State

**After Implementation:**
- All 230+ natural language variations correctly route to specialized handlers
- Zero pattern conflicts between categories
- Common conversational queries (e.g., "what's it like outside", "give me the time", "can I watch X") correctly classified
- Entity dumps eliminated for all supported query types
- Web search fallback only triggers for truly unknown factual queries

**Verification:**
- Test suite with 100+ query variations passes
- Manual testing of high-priority examples confirms correct routing
- No regressions in existing functionality
- Logs show correct intent classification for previously failing queries

## What We're NOT Doing

- ML-based classification (keeping pattern-based approach for speed and determinism)
- Handler implementation changes (only expanding pattern matching)
- Response content modifications (only fixing routing)
- Caching strategy changes
- API integration modifications

## Implementation Approach

**Strategy:**
1. Expand patterns category-by-category in priority order
2. Fix conflicts first to prevent incorrect routing
3. Add patterns using existing substring matching approach
4. Group related patterns for maintainability
5. Document pattern additions with comments
6. Create comprehensive test coverage

**Pattern Addition Method:**
- Add new keywords to existing `any(word in q for word in [...])` lists
- Use multiline formatting for readability when lists exceed 5 items
- Add comments explaining pattern groups (e.g., `# Conversational variations`, `# Action-oriented queries`)

**Risk Mitigation:**
- Maintain existing pattern priority order
- Test for false positives with edge cases
- Verify no conflicts between categories
- Ensure web search remains catch-all for unknown queries

---

## Implementation Steps

### Step 1: Fix Pattern Conflicts

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/facade/airbnb_intent_classifier.py`

**Changes Required:**

#### 1.1: Move Sports Patterns from Web Search to Sports Category

**Current conflict** (lines 346-350 in `_needs_web_search()`):
```python
current_info_keywords = ['latest', 'current', 'recent',
                          'who is', 'what is', 'when did', 'where is',
                          'how many', 'what year', 'when was',
                          'who was', 'who won', 'who played']
```

**Fix** - Remove sports-specific patterns from web_search:
```python
# Line 346-350: Remove 'who won' and 'who played' from web search
current_info_keywords = ['latest', 'current', 'recent',
                          'who is', 'what is', 'when did', 'where is',
                          'how many', 'what year', 'when was',
                          'who was']  # Removed: 'who won', 'who played'
```

**Add to sports** (line 329 in `_classify_news_finance()`):
```python
# Current sports pattern (line 329)
if any(word in q for word in ['score', 'game', 'won', 'lost', 'beat', 'result', 'last game', 'final score']):

# Updated sports pattern
if any(word in q for word in ['score', 'game', 'won', 'lost', 'beat', 'result',
                               'last game', 'final score', 'who won', 'who played',
                               'did', 'win', 'playoff', 'playoffs', 'season',
                               'standings', 'schedule', 'next game', 'record',
                               'match', 'series', 'rank', 'seed', 'vs', 'versus',
                               'play', 'playing', 'played']):
```

---

### Step 2: Expand Time/Date Patterns (Lines 104-123)

**Add 17 missing patterns:**

```python
def _classify_time_date(self, q: str) -> Optional[Tuple]:
    """Classify time and date queries (highest priority)"""
    # Time queries - expanded with conversational variations
    if any(pattern in q for pattern in [
        'what time', "what's the time", 'current time',
        'tell me the time', 'time is it', 'time please',
        # New: Command formats
        'give me the time', 'time right now',
        # New: Question formats
        'can you tell me the time', 'do you know what time it is',
        'do you know the time', 'could you tell me the time',
        'what is the time',
        # New: Casual variations
        'got the time', 'what time ya got', 'what time you got',
        'have the time',
        # New: Alternative phrasings
        'time now', 'time currently', 'show me the time',
        'check the time'
    ]):
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        logger.info(f"🕐 Intent: QUICK (time)")
        return (IntentType.QUICK, f"It's {time_str}", None)

    # Date queries - expanded with conversational variations
    if any(pattern in q for pattern in [
        'what date', "what's the date", 'current date',
        'tell me the date', 'what day is', "today's date",
        'todays date',
        # New: Command formats
        'give me the date', 'date right now',
        # New: Question formats
        'can you tell me the date', 'do you know what date it is',
        'do you know the date', 'could you tell me the date',
        'what is the date',
        # New: Day-specific queries
        'what day of the week', 'what day of week',
        'day of the week', 'which day is it', 'what day it is',
        # New: Alternative phrasings
        'date today', 'date now', 'current day',
        'show me the date', 'check the date',
        # New: Minimal casual queries
        "what's today", 'what is today', 'tell me today'
    ]):
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        logger.info(f"📅 Intent: QUICK (date)")
        return (IntentType.QUICK, f"Today is {date_str}", None)

    return None
```

---

### Step 3: Expand Weather Patterns (Lines 125-143)

**Add 37 missing patterns:**

```python
def _classify_weather(self, q: str) -> Optional[Tuple]:
    """Classify weather-related queries"""
    # Expanded trigger keywords with conversational and condition variations
    if not any(word in q for word in [
        # Existing keywords
        'weather', 'temperature', 'temp', 'rain', 'snow',
        'storm', 'hot', 'cold', 'sunny', 'cloudy', 'forecast',
        # New: Outside/conditions references
        'outside', 'nice', 'bad', 'conditions',
        # New: Precipitation variations
        'drizzle', 'drizzling', 'showers', 'showering',
        'thunderstorm', 'lightning', 'hail', 'hailing',
        'sleet', 'sleeting', 'freezing rain',
        # New: Sky conditions
        'overcast', 'clear', 'clearing', 'partly cloudy',
        'partly sunny', 'foggy', 'fog', 'mist', 'misty',
        'hazy', 'haze',
        # New: Temperature variations
        'warm', 'warming', 'cool', 'cooling', 'freezing',
        'frozen', 'chilly', 'mild', 'degrees',
        # New: Wind conditions
        'windy', 'wind', 'breezy', 'breeze', 'gusty',
        'gusts', 'calm',
        # New: Atmospheric conditions
        'humid', 'humidity', 'uv', 'air quality',
        # New: Action-oriented queries
        'umbrella', 'jacket', 'coat', 'sunscreen', 'shorts'
    ]):
        return None

    # Determine timeframe - expanded with more specific times
    timeframe = "current"  # default
    if any(word in q for word in ['tomorrow', 'tmrw']):
        timeframe = "tomorrow"
    elif any(word in q for word in ['weekend', 'saturday', 'sunday']):
        timeframe = "weekend"
    # New: Specific weekdays
    elif any(word in q for word in ['monday', 'tuesday', 'wednesday',
                                     'thursday', 'friday']):
        # Extract specific day (handler can determine which day)
        timeframe = "week"
    # New: Evening/night specific
    elif any(word in q for word in ['tonight', 'this evening']):
        timeframe = "tonight"
    # New: Time-of-day specific
    elif any(word in q for word in ['this morning', 'this afternoon']):
        timeframe = "today"
    elif 'week' in q or 'next week' in q or 'this week' in q:
        timeframe = "week"
    elif 'today' in q or 'now' in q or 'current' in q:
        timeframe = "current"

    logger.info(f"🌤️ Intent: WEATHER ({timeframe})")
    return (IntentType.API_CALL, "weather", {"timeframe": timeframe, "query": q})
```

---

### Step 4: Expand Location Patterns (Lines 145-191)

**Add 25 missing patterns:**

```python
def _classify_location(self, q: str) -> Optional[Tuple]:
    """Classify location queries (existing patterns from facade)"""
    # Property address - expanded variations
    if any(pattern in q for pattern in [
        'address', 'where am i', 'this property',
        # New: Natural address phrasings
        "what's the address", 'location', 'where is this place',
        'what is this address', 'street address', 'where are we',
        'property location', 'mailing address', 'full address',
        'exact location'
    ]):
        logger.info(f"📍 Intent: QUICK (address)")
        return (IntentType.QUICK, self.PROPERTY_ADDRESS, None)

    # Neighborhood - expanded variations
    if any(pattern in q for pattern in [
        'neighborhood',
        # New: Synonym variations
        'what neighborhood', 'area', 'part of town',
        'what area', 'section of', 'district', 'around here'
    ]):
        logger.info(f"📍 Intent: QUICK (neighborhood)")
        return (IntentType.QUICK, f"You're in {self.NEIGHBORHOOD}, Baltimore", None)

    # Distance queries - expanded trigger patterns
    if any(pattern in q for pattern in [
        'how far',
        # New: Time-focused distance queries
        'how long to', 'distance to', 'how many miles',
        'how close', 'time to', 'drive to', 'walk to',
        'minutes to', 'miles to', 'is it far', 'close to'
    ]):
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

    # Restaurants - expanded variations
    if any(word in q for word in [
        'best', 'good', 'where', 'restaurant', 'food', 'eat',
        'dining', 'recommendation',
        # New: Casual language
        'place to eat', 'grab food', 'places to eat',
        # New: Meal-specific
        'lunch', 'dinner', 'brunch',
        # New: Proximity emphasis
        'nearby restaurants', 'restaurants nearby', 'food nearby',
        # New: State-based queries
        'hungry', 'meal',
        # New: Ordering modes
        'takeout', 'delivery', 'order food'
    ]):
        if 'crab' in q:
            return (IntentType.QUICK, "Best crab cakes: 1) Koco's Pub (best), 2) G&M (huge), 3) Pappas, 4) Captain James (2-for-1 Mondays, 5 min away)", None)
        elif 'lobster' in q:
            return (IntentType.QUICK, "Thames Street Oyster House in Fells Point has amazing lobster rolls (10 min walk)", None)
        elif 'coffee' in q:
            return (IntentType.QUICK, "Ceremony Coffee on Boston St for specialty coffee, or Patterson Perk for cozy neighborhood vibes", None)
        elif 'breakfast' in q or 'brunch' in q:  # Added brunch
            return (IntentType.QUICK, "Blue Moon Cafe for Captain Crunch French Toast, Iron Rooster for all-day breakfast, or THB for fresh bagels", None)
        else:
            # General restaurant query
            return (IntentType.QUICK, "Top picks: Koco's Pub (crab cakes), Thames St Oyster House (seafood), Blue Moon Cafe (breakfast), or walk to Canton/Fells Point waterfront for dozens of options!", None)

    # Emergency - expanded variations (safety-critical)
    if any(word in q for word in [
        'hospital', 'emergency', 'urgent', 'doctor',
        # New: Medical alternatives
        'medical', 'clinic', 'walk-in', 'urgent care',
        # New: Health states
        'sick', 'ill', 'injury', 'hurt', 'pain',
        # New: Emergency services
        'ambulance', '911',
        # New: Specific emergency types
        'dentist', 'poison control'
    ]):
        return (IntentType.QUICK, "Nearest hospital: Johns Hopkins Bayview, 2.5 miles (10 min), 4940 Eastern Ave, 410-550-0100. Emergency: Call 911", None)

    if 'pharmacy' in q:
        return (IntentType.QUICK, "24-hour pharmacy: CVS at 3701 Eastern Ave (1 mile)", None)

    return None
```

---

### Step 5: Expand Transportation Patterns (Lines 193-244)

**Add 33 missing patterns:**

```python
def _classify_transportation(self, q: str) -> Optional[Tuple]:
    """Classify transportation queries (airports, parking, transit)"""
    # Airport queries - expanded variations
    if any(pattern in q for pattern in [
        'airport',
        # New: Question patterns
        'which airport', 'what airport', 'best airport',
        'cheapest airport', 'which airport should i use'
    ]):
        # Closest airport query
        if 'closest' in q or 'nearest' in q:
            logger.info(f"✈️ Intent: QUICK (nearest airport)")
            return (IntentType.QUICK, "Closest airport: BWI (15 mi, 25-30 min, $35-45 Uber). Also: DCA (40 mi), IAD (50 mi), PHL (95 mi)", None)

        # Specific airport codes
        for code in ['bwi', 'dca', 'iad', 'phl', 'jfk', 'ewr', 'lga']:
            if code in q:
                logger.info(f"✈️ Intent: API_CALL (airport_{code.upper()})")
                return (IntentType.API_CALL, "airports", {"airport_code": code.upper(), "query": q})

    # Flight queries (status or search)
    if 'flight' in q or 'flights' in q or 'flying' in q:
        # Specific flight status
        if any(word in q for word in ['status', 'delayed', 'on time', 'delay']):
            flight_match = re.search(r'\b([A-Z]{2}\d{1,4})\b', q.upper())
            flight_num = flight_match.group(1) if flight_match else None
            logger.info(f"✈️ Intent: API_CALL (flight_status)")
            return (IntentType.API_CALL, "flights", {"type": "status", "flight_number": flight_num, "query": q})

        # Flight search
        elif any(word in q for word in ['to', 'from', 'leaving', 'departing', 'arriving']):
            logger.info(f"✈️ Intent: API_CALL (flight_search)")
            return (IntentType.API_CALL, "flights", {"type": "search", "query": q})

    # Parking - expanded variations
    if any(pattern in q for pattern in [
        'parking',
        # New: Question patterns
        'where can i park', 'where to park', 'where do i park',
        'is there parking', 'parking available', 'can i park here',
        # New: Action patterns
        'find parking', 'need parking',
        # New: Attribute queries
        'parking meter', 'meter parking', 'free parking',
        'overnight parking', 'parking cost', 'parking restrictions'
    ]):
        if 'street' in q:
            return (IntentType.QUICK, "Street parking in Canton: Meter parking 8am-8pm M-Sat ($1.50/hr), free overnight and Sundays. Pay at kiosks or ParkMobile app", None)
        elif 'garage' in q or 'lot' in q:
            return (IntentType.QUICK, "Nearest garage: Inner Harbor Garage ($12/day), Fells Point garage ($8/day). Street parking often easier in Canton", None)
        else:
            return (IntentType.QUICK, "Street parking: Free overnight/Sundays, $1.50/hr M-Sat 8am-8pm. Garages: Inner Harbor $12/day", None)

    # Public transit - expanded with generic terms and missing services
    if any(pattern in q for pattern in [
        'bus', 'light rail', 'marc', 'water taxi',
        # New: Generic transit terms
        'public transportation', 'public transport', 'train',
        'subway', 'metro', 'mta', 'transit',
        # New: Question patterns
        'how do i get to', 'how to get to',
        'transit options', 'getting around', 'get around'
    ]):
        if 'circulator' in q:
            return (IntentType.QUICK, "Charm City Circulator: Purple route runs every 15 min, free, nearest stop on Boston St", None)
        elif 'water taxi' in q:
            return (IntentType.QUICK, "Water taxi runs Apr-Nov, 11am-11pm weekdays, 10am-midnight weekends. $15 all-day pass, nearest stop at Canton Waterfront Park", None)
        elif 'marc' in q:
            return (IntentType.QUICK, "MARC Penn Line: Canton → Penn Station (15 min drive/Uber) → DC Union Station (1 hr, $8)", None)
        # New: Generic public transit response
        elif any(word in q for word in ['public transportation', 'public transport',
                                         'transit', 'how do i get to', 'getting around']):
            return (IntentType.QUICK, "Public transit: Charm City Circulator (free), Light Rail ($2), MTA buses ($2), Water Taxi ($15/day Apr-Nov), MARC train to DC ($8). Download CharmPass app for tickets.", None)

    # Rideshare services (NEW CATEGORY)
    if any(word in q for word in ['uber', 'lyft', 'rideshare', 'ride share',
                                   'get a ride', 'call a ride', 'taxi', 'cab']):
        return (IntentType.QUICK, "Uber/Lyft readily available in Canton. Typical fares: BWI Airport $35-45, Inner Harbor $8-12, Penn Station $10-15. Download Uber/Lyft apps for real-time pricing.", None)

    # Bike share / scooters - expanded variations
    if any(pattern in q for pattern in [
        # Existing patterns
        'scooter',
        # Expanded bike patterns
        'bike', 'bicycle', 'bike rental', 'bikeshare',
        'bike share', 'baltimore bike', 'bcycle',
        # New: E-bike variations
        'e-bike', 'ebike', 'electric bike', 'electric bicycle',
        # New: Scooter variations
        'electric scooter', 'e-scooter', 'escooter',
        'lime scooter', 'bird scooter'
    ]) and any(action in q for action in ['rent', 'share', 'get', 'where', 'how']):
        return (IntentType.QUICK, "Baltimore Bike Share: $2 per 30 min, stations at Canton Crossing and Patterson Park. Download BCycle app. Lime/Bird scooters also available", None)

    return None
```

---

### Step 6: Expand Entertainment Patterns (Lines 246-309)

**Add 36 missing patterns:**

```python
def _classify_entertainment(self, q: str) -> Optional[Tuple]:
    """Classify entertainment queries (streaming, events, movies)"""
    # Streaming services - expanded variations
    if any(word in q for word in ['streaming', 'netflix', 'hulu', 'disney', 'hbo', 'max',
                                   'prime video', 'peacock', 'paramount', 'apple tv', 'youtube tv',
                                   # New: Content type mentions
                                   'tv shows', 'tv series', 'series', 'movies', 'films',
                                   # New: Availability queries
                                   'can i watch', 'is', 'available', 'do you have',
                                   'watch', 'watching']):
        # List available services
        if 'what services' in q or 'streaming services' in q:
            logger.info(f"📺 Intent: QUICK (streaming services list)")
            return (IntentType.QUICK, "Available: Netflix, Hulu, Disney+, HBO Max, Prime Video, Peacock, Paramount+, Apple TV+, YouTube TV (+ NFL Sunday Ticket)", None)

        # How to access
        if 'how' in q or 'login' in q or 'password' in q or 'sign in' in q or 'access' in q:
            return (IntentType.QUICK, "All streaming apps are already logged in on the TV. Just select the app and start watching!", None)

        # "Where can I watch X?" or "Can I watch X?" - Phase 3 API lookup
        if ('where' in q and 'watch' in q) or ('can i watch' in q) or ('is' in q and 'available' in q):
            logger.info(f"📺 Intent: API_CALL (streaming_search) - Phase 3")
            return (IntentType.API_CALL, "streaming", {"type": "search", "query": q})

        # Service-specific quick answers
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

    # Local events - already expanded with 'tell me about' pattern
    if any(word in q for word in ['events', 'things to do', 'what to do', 'tonight', 'weekend',
                                   'happening', 'going on', 'local',
                                   # New: Activity framing
                                   'fun', 'activities', 'activity', 'do for fun',
                                   # New: Discovery variations
                                   'suggestions', 'recommend', 'ideas', 'plans',
                                   # New: Specific event types
                                   'concerts', 'concert', 'shows', 'performances',
                                   'festival', 'festivals', 'comedy']) or 'tell me about' in q:
        if 'tonight' in q or 'today' in q:
            logger.info(f"🎭 Intent: API_CALL (events_today) - Phase 2")
            return (IntentType.API_CALL, "events", {"timeframe": "today", "query": q})
        elif 'tomorrow' in q:
            return (IntentType.API_CALL, "events", {"timeframe": "tomorrow", "query": q})
        elif 'weekend' in q:
            return (IntentType.API_CALL, "events", {"timeframe": "weekend", "query": q})
        else:
            # General events query (default to today)
            logger.info(f"🎭 Intent: API_CALL (events_general) - Phase 2")
            return (IntentType.API_CALL, "events", {"timeframe": "today", "query": q})

    # Museums / Attractions - expanded variations
    if any(word in q for word in [
        'museum',
        # New: General attraction terms
        'attractions', 'tourist', 'tourism', 'sights', 'sightseeing',
        'visit', 'see', 'places to go',
        # New: Specific attraction types
        'zoo', 'historic', 'historical', 'fort', 'science',
        'art', 'gallery',
        # New: Activities
        'tours', 'tour', 'exhibit', 'exhibition'
    ]):
        if 'free' in q:
            return (IntentType.QUICK, "FREE museums: Baltimore Museum of Art (always free), Walters Art Museum (always free), American Visionary Art Museum (Wed 5-9pm free)", None)
        elif 'aquarium' in q:
            return (IntentType.QUICK, "National Aquarium: Inner Harbor, $40 adults, $25 kids. Book online for discount. Highlights: shark tank, dolphin show, rainforest. 2-3 hours to see everything. 10 min drive from Canton", None)
        else:
            return (IntentType.QUICK, "Top museums: BMA (free), Walters (free), AVAM ($16), National Aquarium ($40), Fort McHenry ($15), Science Center ($25)", None)

    # Nightlife - expanded variations
    if any(pattern in q for pattern in [
        'nightlife',
        # Expanded bar patterns
        'bar', 'bars',
        # New: Going out variations
        'going out', 'night out', 'out tonight',
        # New: Venue types
        'drinks', 'drink', 'clubs', 'club', 'dance', 'dancing',
        'pub', 'pubs', 'brewery', 'breweries',
        # New: Entertainment
        'live music', 'music venue'
    ]):
        if 'brewery' in q or 'breweries' in q:
            return (IntentType.QUICK, "Baltimore breweries: 1) Union Craft (10 min), 2) Peabody Heights (15 min), 3) Monument City (Canton - walking distance), 4) Diamondback (15 min). Most have food trucks on weekends.", None)
        elif 'live music' in q:
            return (IntentType.QUICK, "Live music: Fells Point (historic pubs with bands), Power Plant Live (various venues), Soundstage (concerts), 8x10 (local bands). Check baltimore.org/events for tonight's shows.", None)
        else:
            return (IntentType.QUICK, "Nightlife areas: 1) Fells Point (historic pubs, live music), 2) Federal Hill (young crowd, dance clubs), 3) Power Plant Live (club complex), 4) Canton (local bars)", None)

    return None
```

---

### Step 7: Expand News/Finance/Sports Patterns (Lines 311-333)

**Add 29 missing patterns + fix conflicts:**

```python
def _classify_news_finance(self, q: str) -> Optional[Tuple]:
    """Classify news and finance queries (Phase 4)"""
    # News queries - expanded variations
    if any(pattern in q for pattern in [
        'news',
        # New: General news inquiry
        "what's happening", 'breaking', 'breaking news',
        'latest news', 'current events', 'what happened',
        'any updates', 'in the news', 'happening today',
        'happening now'
    ]):
        if 'local' in q or 'baltimore' in q:
            logger.info(f"📰 Intent: API_CALL (baltimore_news) - Phase 4")
            return (IntentType.API_CALL, "news", {"type": "local", "query": q})
        elif 'headlines' in q or 'top' in q or 'breaking' in q:
            logger.info(f"📰 Intent: API_CALL (national_news) - Phase 4")
            return (IntentType.API_CALL, "news", {"type": "national", "query": q})

    # Stock market queries - expanded variations
    if any(word in q for word in [
        'stock', 'ticker', 'share price', 'dow', 'nasdaq', 's&p', 'market',
        # New: Common stock queries
        'stock market', 'stock price', 'trading', 'traded',
        'portfolio',
        # New: Market terms
        'futures', 'options', 'crypto', 'bitcoin', 'ethereum',
        'forex', 'commodities', 'bonds',
        # New: Index variations
        's&p 500', 'dow jones', 'nasdaq composite'
    ]):
        logger.info(f"📈 Intent: API_CALL (stocks) - Phase 4")
        return (IntentType.API_CALL, "stocks", {"query": q})

    # Sports scores - EXPANDED with conflict resolution
    # NOTE: 'who won' and 'who played' moved here from web_search (conflict fix)
    if any(word in q for word in [
        # Existing patterns
        'score', 'game', 'won', 'lost', 'beat', 'result',
        'last game', 'final score',
        # NEW: Moved from web_search (conflict fix)
        'who won', 'who played',
        # NEW: Outcome queries
        'did', 'win', 'final', 'finish',
        # NEW: Schedule/Status
        'playoff', 'playoffs', 'season', 'standings',
        'schedule', 'next game',
        # NEW: Context
        'record', 'rank', 'ranked', 'seed', 'series',
        'match', 'vs', 'versus',
        # NEW: Actions
        'play', 'playing', 'played', 'compete', 'competing'
    ]):
        logger.info(f"🏈 Intent: API_CALL (sports_score - sports_client will extract team)")
        return (IntentType.API_CALL, "sports", {"query": q})

    return None
```

---

### Step 8: Expand Web Search Fallback Patterns (Lines 335-365)

**Add 55 missing patterns:**

```python
def _needs_web_search(self, q: str) -> bool:
    """
    Determine if query should use web search fallback

    Triggers:
    - Current/factual info keywords (latest, current, recent, today, now)
    - Unknown business queries (phone number, hours, address of)
    - Question patterns (who is, what is, when did, where is, how many, what year)
    - Temporal patterns (yesterday, last week, last month)
    - Comparative patterns (vs, compared to, difference between)
    - Definition patterns (define, explain, meaning of)
    - Queries with question words that aren't handled elsewhere
    """
    # Expanded current/factual info keywords
    current_info_keywords = [
        'latest', 'current', 'recent',
        'who is', 'what is', 'when did', 'where is',
        'how many', 'what year', 'when was', 'who was',
        # NOTE: 'who won' and 'who played' REMOVED - now in sports (conflict fix)
        # New: Temporal patterns
        'yesterday', 'last night', 'last week', 'last month',
        'last year', 'this week', 'this month', 'this year',
        'ago',
        # New: Additional question patterns
        'what are', 'which is', 'which are'
    ]
    if any(keyword in q for keyword in current_info_keywords):
        return True

    # Expanded business info keywords
    business_keywords = [
        'phone number', 'address of', 'hours', 'open',
        'website', 'email', 'contact', 'how do i get to',
        # New: Operational patterns
        'directions to', 'navigate to', 'route to', 'way to',
        'map to', 'getting to'
    ]
    if any(keyword in q for keyword in business_keywords):
        return True

    # NEW: Comparative query patterns
    comparative_keywords = [
        'vs', 'versus', 'compared to', 'comparison',
        'better than', 'worse than', 'difference between',
        'similarities', 'or'
    ]
    if any(keyword in q for keyword in comparative_keywords):
        return True

    # NEW: Definition/Explanation patterns
    definition_keywords = [
        'define', 'definition', 'meaning of', 'explain',
        'explanation', 'what does', 'mean'
    ]
    if any(keyword in q for keyword in definition_keywords):
        return True

    # NEW: Operational/How-To patterns
    operational_keywords = [
        'can i', 'is it possible', 'am i able to',
        'is there a way', 'steps to', 'guide', 'tutorial',
        'instructions'
    ]
    if any(keyword in q for keyword in operational_keywords):
        return True

    # NEW: Quantitative/Statistical patterns
    quantitative_keywords = [
        'how much', 'how far', 'how long',
        'percentage', 'statistics', 'data',
        'average', 'median', 'total'
    ]
    if any(keyword in q for keyword in quantitative_keywords):
        return True

    # NEW: Entity Identification patterns
    entity_keywords = [
        'which', 'list', 'show me', 'find',
        'search for', 'look up'
    ]
    if any(keyword in q for keyword in entity_keywords):
        return True

    # NEW: Superlative/Ranking patterns
    superlative_keywords = [
        'best', 'worst', 'top', 'most', 'least',
        'highest', 'lowest', 'fastest', 'cheapest'
    ]
    if any(keyword in q for keyword in superlative_keywords):
        return True

    # Expanded general factual question patterns
    if q.startswith(('who ', 'what ', 'when ', 'where ', 'why ', 'how ')):
        # Only if it's a short factual question (not a complex query)
        if len(q.split()) <= 10:  # Reasonable length for factual queries
            return True

    return False
```

---

## Testing Strategy

**File**: `/Users/jaystuart/dev/project-athena/tests/facade/test_comprehensive_patterns.py` (NEW)

Create comprehensive test suite covering all pattern additions:

```python
#!/usr/bin/env python3
"""
Comprehensive Pattern Coverage Tests

Tests all 230+ pattern additions across 7 intent categories.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/jetson'))

from facade.airbnb_intent_classifier import AirbnbIntentClassifier, IntentType

classifier = AirbnbIntentClassifier()

def test_time_date_patterns():
    """Test time/date pattern expansions"""
    # Command formats
    assert classifier.classify("give me the time")[0] == IntentType.QUICK
    assert "It's" in classifier.classify("give me the time")[1]

    # Casual variations
    assert classifier.classify("got the time?")[0] == IntentType.QUICK
    assert classifier.classify("what time ya got")[0] == IntentType.QUICK

    # Date variations
    assert classifier.classify("what's today")[0] == IntentType.QUICK
    assert "Today is" in classifier.classify("what's today")[1]
    assert classifier.classify("what day of the week")[0] == IntentType.QUICK

    print("✅ Time/Date patterns: PASS")

def test_weather_patterns():
    """Test weather pattern expansions"""
    # Outside references
    assert classifier.classify("what's it like outside")[0] == IntentType.API_CALL
    assert classifier.classify("what's it like outside")[1] == "weather"

    # Nice out queries
    assert classifier.classify("is it nice out")[0] == IntentType.API_CALL

    # Action-oriented
    assert classifier.classify("should I bring an umbrella")[0] == IntentType.API_CALL
    assert classifier.classify("do I need a jacket")[0] == IntentType.API_CALL

    # Atmospheric conditions
    assert classifier.classify("how humid is it")[0] == IntentType.API_CALL
    assert classifier.classify("is it windy")[0] == IntentType.API_CALL

    # Timeframe: tonight
    intent, handler, data = classifier.classify("weather tonight")
    assert intent == IntentType.API_CALL
    assert data['timeframe'] == "tonight"

    print("✅ Weather patterns: PASS")

def test_location_patterns():
    """Test location pattern expansions"""
    # Address variations
    assert classifier.classify("what's the address")[0] == IntentType.QUICK
    assert classifier.classify("location")[0] == IntentType.QUICK

    # Distance variations
    assert classifier.classify("how long to Inner Harbor")[0] == IntentType.QUICK
    assert classifier.classify("distance to BWI")[0] == IntentType.QUICK

    # Restaurant variations
    assert classifier.classify("place to eat")[0] == IntentType.QUICK
    assert classifier.classify("grab lunch")[0] == IntentType.QUICK
    assert classifier.classify("dinner recommendations")[0] == IntentType.QUICK

    # Emergency variations
    assert classifier.classify("walk-in clinic")[0] == IntentType.QUICK
    assert classifier.classify("I'm sick")[0] == IntentType.QUICK

    print("✅ Location patterns: PASS")

def test_transportation_patterns():
    """Test transportation pattern expansions"""
    # Airport variations
    assert classifier.classify("which airport should I use")[0] == IntentType.QUICK

    # Parking variations
    assert classifier.classify("where can I park")[0] == IntentType.QUICK
    assert classifier.classify("where to park")[0] == IntentType.QUICK

    # Transit variations
    assert classifier.classify("public transportation options")[0] == IntentType.QUICK
    assert classifier.classify("how do I get to Inner Harbor")[0] == IntentType.QUICK

    # Rideshare (new category)
    assert classifier.classify("can I get an Uber")[0] == IntentType.QUICK
    assert classifier.classify("Lyft to BWI")[0] == IntentType.QUICK

    # Bike variations
    assert classifier.classify("electric scooter rental")[0] == IntentType.QUICK
    assert classifier.classify("e-bike")[0] == IntentType.QUICK

    print("✅ Transportation patterns: PASS")

def test_entertainment_patterns():
    """Test entertainment pattern expansions"""
    # Streaming variations
    intent, handler, data = classifier.classify("can I watch Succession")
    assert intent == IntentType.API_CALL
    assert handler == "streaming"

    assert classifier.classify("is Breaking Bad available")[0] == IntentType.API_CALL

    # Events variations
    assert classifier.classify("what's fun to do tonight")[0] == IntentType.API_CALL
    assert classifier.classify("activities this weekend")[0] == IntentType.API_CALL
    assert classifier.classify("concerts tonight")[0] == IntentType.API_CALL

    # Museums variations
    assert classifier.classify("tourist attractions")[0] == IntentType.QUICK
    assert classifier.classify("what to visit")[0] == IntentType.QUICK

    # Nightlife variations
    assert classifier.classify("going out for drinks")[0] == IntentType.QUICK
    assert classifier.classify("brewery recommendations")[0] == IntentType.QUICK
    assert classifier.classify("live music venues")[0] == IntentType.QUICK

    print("✅ Entertainment patterns: PASS")

def test_news_finance_sports_patterns():
    """Test news/finance/sports pattern expansions"""
    # News variations
    intent, handler, data = classifier.classify("what's happening in Baltimore")
    assert intent == IntentType.API_CALL
    assert handler == "news"

    assert classifier.classify("breaking news")[0] == IntentType.API_CALL
    assert classifier.classify("latest news")[0] == IntentType.API_CALL

    # Finance variations
    intent, handler, data = classifier.classify("how is Tesla trading")
    assert intent == IntentType.API_CALL
    assert handler == "stocks"

    assert classifier.classify("bitcoin price")[0] == IntentType.API_CALL
    assert classifier.classify("stock market today")[0] == IntentType.API_CALL

    # Sports variations (including conflict fixes)
    intent, handler, data = classifier.classify("who won the game")
    assert intent == IntentType.API_CALL
    assert handler == "sports"

    assert classifier.classify("did the Ravens win")[0] == IntentType.API_CALL
    assert classifier.classify("Ravens playoff schedule")[0] == IntentType.API_CALL
    assert classifier.classify("next Ravens game")[0] == IntentType.API_CALL
    assert classifier.classify("Ravens vs Steelers")[0] == IntentType.API_CALL

    print("✅ News/Finance/Sports patterns: PASS")

def test_web_search_patterns():
    """Test web search fallback expansions"""
    # Temporal patterns
    assert classifier.classify("what happened yesterday")[0] == IntentType.WEB_SEARCH
    assert classifier.classify("news from last week")[0] == IntentType.WEB_SEARCH

    # Comparative patterns
    assert classifier.classify("BWI vs DCA comparison")[0] == IntentType.WEB_SEARCH
    assert classifier.classify("difference between Uber and Lyft")[0] == IntentType.WEB_SEARCH

    # Definition patterns
    assert classifier.classify("define gentrification")[0] == IntentType.WEB_SEARCH
    assert classifier.classify("explain blockchain")[0] == IntentType.WEB_SEARCH

    # Operational patterns
    assert classifier.classify("can I bike to BWI")[0] == IntentType.WEB_SEARCH
    assert classifier.classify("is it possible to walk to Inner Harbor")[0] == IntentType.WEB_SEARCH

    print("✅ Web Search patterns: PASS")

def test_conflict_resolution():
    """Test that pattern conflicts are resolved"""
    # "who won" should route to sports, not web search
    intent, handler, data = classifier.classify("who won the Ravens game")
    assert intent == IntentType.API_CALL
    assert handler == "sports", f"Expected 'sports' but got '{handler}'"

    # "who played" should route to sports, not web search
    intent, handler, data = classifier.classify("who played last night")
    assert intent == IntentType.API_CALL
    assert handler == "sports", f"Expected 'sports' but got '{handler}'"

    print("✅ Conflict resolution: PASS")

if __name__ == "__main__":
    print("\n🧪 Running Comprehensive Pattern Coverage Tests\n")

    test_time_date_patterns()
    test_weather_patterns()
    test_location_patterns()
    test_transportation_patterns()
    test_entertainment_patterns()
    test_news_finance_sports_patterns()
    test_web_search_patterns()
    test_conflict_resolution()

    print("\n✅ All pattern coverage tests passed!\n")
```

---

## Success Criteria

### Automated Verification:

- [ ] All pattern additions compile without syntax errors
- [ ] Comprehensive test suite passes: `python3 /Users/jaystuart/dev/project-athena/tests/facade/test_comprehensive_patterns.py`
- [ ] No regressions in existing tests: `python3 -m pytest /Users/jaystuart/dev/project-athena/tests/facade/`
- [ ] Pattern conflict resolution verified (who won → sports, not web_search)
- [ ] Classifier loads successfully: `python3 -c "from facade.airbnb_intent_classifier import AirbnbIntentClassifier; c = AirbnbIntentClassifier()"`

### Manual Verification:

After deployment to Jetson (192.168.10.62):

**High-Priority Query Testing:**

Test each category with real queries via:
```bash
curl -s -X POST http://192.168.10.62:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2:3b","messages":[{"role":"user","content":"QUERY"}],"stream":false}' \
  | jq -r '.message.content'
```

1. **Weather:**
   - [ ] "what's it like outside" → Weather response (not entity dump)
   - [ ] "is it nice out" → Weather response
   - [ ] "should I bring an umbrella" → Weather response
   - [ ] "weather tonight" → Tonight's weather (not current)

2. **Time/Date:**
   - [ ] "give me the time" → Current time
   - [ ] "what's today" → Current date
   - [ ] "got the time" → Current time

3. **Sports (Conflict Fix):**
   - [ ] "who won the game" → Sports score response (NOT entity dump)
   - [ ] "did the Ravens win" → Sports score response
   - [ ] "Ravens playoff schedule" → Sports response
   - [ ] Verify logs show `Intent: API_CALL (sports)` not `WEB_SEARCH`

4. **Transportation:**
   - [ ] "where can I park" → Parking info
   - [ ] "can I get an Uber" → Rideshare info
   - [ ] "public transportation" → Transit info

5. **Entertainment:**
   - [ ] "can I watch Succession" → Streaming search response
   - [ ] "what's fun to do tonight" → Events API response
   - [ ] "brewery recommendations" → Brewery info

6. **Location:**
   - [ ] "what's the address" → Property address
   - [ ] "grab lunch" → Restaurant recommendations
   - [ ] "how long to Inner Harbor" → Distance/time info

7. **News:**
   - [ ] "what's happening in Baltimore" → News API response (not web search)
   - [ ] "breaking news" → News API response

8. **Web Search:**
   - [ ] "what happened yesterday" → Web search response
   - [ ] "define gentrification" → Web search response
   - [ ] Verify truly unknown queries still fall to web search/LLM appropriately

**Regression Testing:**
- [ ] Previously working queries still work correctly
- [ ] No new entity dumps appearing
- [ ] Response times remain acceptable (<3s for quick responses, <10s for API calls)

**Log Analysis:**
- [ ] Check `/mnt/nvme/athena-lite/logs/facade.log` for correct intent classifications
- [ ] Verify no unexpected fallbacks to LLM for supported queries
- [ ] Confirm pattern conflict fixes (sports queries not hitting web search)

---

## Performance Considerations

**Pattern Matching Performance:**
- All patterns use simple substring matching: `any(word in q for word in [...])`
- Python `in` operator is O(n) for lists, but lists are small (5-50 items)
- Total pattern checks: ~230 patterns across 7 categories
- Expected overhead: <5ms per query (negligible compared to API calls)

**Memory Impact:**
- Pattern lists stored as Python lists in memory
- Total memory increase: <100KB for all pattern strings
- No caching needed for pattern matching

**Optimization Opportunities:**
- Consider converting large pattern lists to sets if performance issues arise
- Current implementation prioritizes readability over micro-optimization
- Pattern order remains unchanged to preserve existing behavior

---

## Migration Notes

**Deployment Steps:**

1. **Backup current classifier:**
   ```bash
   ssh jstuart@192.168.10.62
   cp /mnt/nvme/athena-lite/facade/airbnb_intent_classifier.py \
      /mnt/nvme/athena-lite/facade/airbnb_intent_classifier.py.backup
   ```

2. **Deploy updated classifier:**
   ```bash
   scp /Users/jaystuart/dev/project-athena/src/jetson/facade/airbnb_intent_classifier.py \
       jstuart@192.168.10.62:/mnt/nvme/athena-lite/facade/
   ```

3. **Deploy test suite:**
   ```bash
   scp /Users/jaystuart/dev/project-athena/tests/facade/test_comprehensive_patterns.py \
       jstuart@192.168.10.62:/mnt/nvme/athena-lite/tests/
   ```

4. **Restart facade service:**
   ```bash
   ssh jstuart@192.168.10.62 'ps aux | grep facade_integration | grep -v grep | awk "{print \$2}" | xargs kill -9 2>/dev/null; sleep 2; cd /mnt/nvme/athena-lite && nohup python3 facade_integration.py > logs/facade.log 2>&1 &'
   ```

5. **Run automated tests:**
   ```bash
   ssh jstuart@192.168.10.62 'cd /mnt/nvme/athena-lite && python3 tests/test_comprehensive_patterns.py'
   ```

6. **Monitor logs:**
   ```bash
   ssh jstuart@192.168.10.62 'tail -f /mnt/nvme/athena-lite/logs/facade.log'
   ```

**Rollback Plan:**
If issues arise:
```bash
ssh jstuart@192.168.10.62
cp /mnt/nvme/athena-lite/facade/airbnb_intent_classifier.py.backup \
   /mnt/nvme/athena-lite/facade/airbnb_intent_classifier.py
# Restart service (same command as deployment step 4)
```

---

## References

- Research Document: Pattern gap analysis (current session)
- Original Implementation Plan: `thoughts/shared/plans/2025-01-07-facade-intent-expansion.md`
- Current Classifier: `/Users/jaystuart/dev/project-athena/src/jetson/facade/airbnb_intent_classifier.py`
- Integration File: `/Users/jaystuart/dev/project-athena/src/jetson/facade_integration.py`
- Handlers: `/Users/jaystuart/dev/project-athena/src/jetson/facade/handlers/`

---

## Implementation Timeline

**Estimated Effort:** 2-3 hours
- Pattern additions: 60 minutes
- Test suite creation: 30 minutes
- Deployment and testing: 45 minutes
- Documentation and verification: 15 minutes

**Ready for Implementation:** Yes - all patterns identified, conflicts resolved, approach validated
