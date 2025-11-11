# Research: Missing Intent Classifications & Data Sources for Facade

**Date**: 2025-11-07
**Researcher**: Claude Code
**Repository**: project-athena
**Topic**: Comprehensive intent classification system and data sources for Airbnb guest assistant facade
**Status**: Identified gaps in current implementation

## Research Question

What intent classifications and data sources are missing from the current facade implementation to provide comprehensive Airbnb guest assistance?

## Summary

The current facade implementation (ollama_baltimore_smart_facade.py) has basic intent classification for location, distances, restaurants, and sports. However, it's missing **extensive categories** of information that Airbnb guests commonly need:

1. **Transportation**: Comprehensive transit options beyond basic distances
2. **Entertainment**: TV shows, movies, streaming services, local events
3. **Weather**: Current conditions and forecasts
4. **Airport/Flight Information**: Real-time flight status for 7 airports (BWI, DCA, IAD, PHL, JFK, EWR, LGA)
5. **News**: Local and national news stories
6. **Financial**: Stock market data and ticker information
7. **Web Search Fallback**: General web search for unclassified queries

## Current Implementation Analysis

### What EXISTS in ollama_baltimore_smart_facade.py

**File**: `/mnt/nvme/athena-lite/ollama_baltimore_smart_facade.py`

**Current Intent Classifications** (lines 48-110):
- ✅ Sports scores (routed to LLM)
- ✅ Property address
- ✅ Neighborhood information
- ✅ Distance queries (Inner Harbor, Camden Yards, M&T Stadium, BWI, DC)
- ✅ Transportation how-to (basic Uber/Light Rail directions)
- ✅ Restaurant recommendations (crab cakes, lobster, coffee, breakfast)
- ✅ Emergency information (hospital, pharmacy)
- ⚠️ Weather (placeholder only - returns "I don't have current weather")

**Quick Response Categories**:
1. Location information
2. Distance calculations
3. Transportation directions (limited)
4. Restaurant recommendations (limited)
5. Emergency services

### What is MISSING

Based on user requirements, the following categories are completely absent or incomplete:

---

## Missing Category 1: Comprehensive Transportation Information

### Current State
- Basic distances to major destinations
- Simple Uber/Light Rail directions
- MARC train to DC

### What's Missing

#### Public Transportation
- **Bus Routes**: Charm City Circulator, MTA buses
- **Water Taxi**: Full schedule, routes, seasonal hours
- **Light Rail**: Detailed schedules, frequency, exact stations
- **MARC Train**: Complete schedule BWI ↔ Penn Station ↔ Union Station
- **Amtrak**: Northeast Corridor service from Penn Station
- **Metro Subway**: Blue/Orange lines (if relevant)

#### Rideshare & Alternatives
- **Uber/Lyft**: Estimated fares to popular destinations
- **Taxis**: Phone numbers, dispatch services
- **Bike Share**: Baltimore Bike Share locations, pricing
- **Scooters**: Lime/Bird availability in Canton
- **Car Rentals**: Nearby Enterprise, Hertz, Budget locations

#### Parking Information
- Street parking rules in Canton
- Paid parking garages (Inner Harbor, Fells Point)
- Parking for stadium events (Ravens/Orioles games)

#### Example Intent Patterns to Add
```python
# Bus routes
if 'bus' in q and 'circulator' in q:
    return ('quick', "Charm City Circulator: Purple route runs every 15 min, free, nearest stop on Boston St")

# Water taxi schedule
if 'water taxi' in q and ('schedule' in q or 'hours' in q):
    return ('quick', "Water taxi runs Apr-Nov, 11am-11pm weekdays, 10am-midnight weekends. $15 all-day pass, nearest stop at Canton Waterfront Park")

# Bike share
if 'bike' in q and ('rent' in q or 'share' in q):
    return ('quick', "Baltimore Bike Share: $2 per 30 min, stations at Canton Crossing and Patterson Park. Download BCycle app")

# Parking
if 'parking' in q:
    if 'street' in q:
        return ('quick', "Street parking in Canton: Meter parking 8am-8pm M-Sat ($1.50/hr), free overnight and Sundays. Pay at kiosks or ParkMobile app")
    elif 'garage' in q or 'lot' in q:
        return ('quick', "Nearest garage: Inner Harbor Garage ($12/day), Fells Point garage ($8/day). Street parking often easier in Canton")
```

#### Data Sources Needed
- **MTA Maryland**: Bus/Light Rail schedules API
- **Water Taxi**: Harbor Connector schedule
- **MARC**: Real-time train schedules
- **Parking**: ParkMobile API or static rules

---

## Missing Category 2: Entertainment (TV Shows, Movies, Events)

### Current State
- None implemented

### What's Missing

#### Streaming Services Available to Guests

**Complete list of streaming services available at 912 S Clinton St:**
1. **Netflix** - Movies, TV shows, originals
2. **Hulu** - Current TV episodes, originals, movies
3. **Disney+** - Disney, Pixar, Marvel, Star Wars, National Geographic
4. **HBO Max** - HBO originals, Warner Bros movies, Max originals
5. **Prime Video** (Amazon) - Movies, TV shows, Amazon originals
6. **Peacock** - NBC shows, movies, sports, originals
7. **Paramount+** - CBS shows, Paramount movies, sports
8. **Apple TV+** - Apple originals
9. **YouTube TV** - Live TV, 100+ channels, unlimited DVR
10. **NFL Sunday Ticket** - All out-of-market NFL games (YouTube TV add-on)

#### TV Show Queries
```python
# List available services
if 'streaming' in q or 'what services' in q:
    return ('quick', "Available streaming services: Netflix, Hulu, Disney+, HBO Max, Prime Video, Peacock, Paramount+, Apple TV+, YouTube TV (live TV + NFL Sunday Ticket)")

# What's on tonight / live TV
if 'what' in q and 'on' in q and ('tonight' in q or 'tv' in q or 'now' in q):
    if 'live' in q or 'channels' in q:
        return ('quick', "YouTube TV has 100+ live channels. Check the guide on TV. Popular: ESPN, CNN, HGTV, Food Network, local networks")
    else:
        return ('quick', "Which service? We have Netflix, Hulu, Disney+, HBO Max, Prime Video, Peacock, Paramount+, Apple TV+, YouTube TV")

# Specific show searches - "Where can I watch X?"
if 'where' in q and 'watch' in q:
    # Extract show/movie name, search across all services
    return ('api_call', 'streaming_search')

# Service-specific queries
if 'netflix' in q:
    if 'new' in q or 'trending' in q:
        return ('api_call', 'netflix_trending')
    elif 'recommend' in q:
        return ('api_call', 'netflix_recommendations')

if 'hulu' in q:
    if 'new episodes' in q or 'latest' in q:
        return ('quick', "Hulu gets new episodes next day for most current shows. Check 'New on Hulu' section")

if 'disney' in q or 'disney+' in q:
    if 'marvel' in q:
        return ('quick', "Marvel on Disney+: All MCU movies, shows like Loki, WandaVision, What If")
    elif 'star wars' in q:
        return ('quick', "Star Wars on Disney+: All movies, The Mandalorian, Ahsoka, Andor, Clone Wars")

if 'hbo' in q or 'max' in q:
    if 'new' in q:
        return ('api_call', 'hbo_new_releases')

# Sports
if 'game' in q or 'sports' in q:
    if 'nfl' in q or 'football' in q:
        if 'sunday ticket' in q:
            return ('quick', "Sunday Ticket on YouTube TV shows ALL out-of-market Sunday NFL games. Open YouTube TV app, go to Sports")
        else:
            return ('quick', "NFL games: Local games on YouTube TV, Sunday Ticket for out-of-market games. Ravens games usually on CBS/Fox")
    elif 'ravens' in q:
        return ('quick', "Ravens games on YouTube TV (CBS/Fox/NBC/ESPN). Check Sports section for schedule")
    elif 'orioles' in q:
        return ('quick', "Orioles games on MASN (channel varies). Check YouTube TV guide or use search")
    else:
        return ('quick', "Sports on YouTube TV: ESPN, ESPN2, FS1, FS2, NBC Sports, CBS Sports, NFL Network, MLB Network. Also Peacock has Premier League")

# New releases across all platforms
if 'new' in q and ('movies' in q or 'shows' in q or 'releases' in q):
    if 'this week' in q or 'tonight' in q:
        return ('api_call', 'streaming_new_this_week')
    else:
        return ('api_call', 'streaming_new_releases')

# Movie searches
if 'movie' in q:
    if 'action' in q or 'comedy' in q or 'horror' in q or 'drama' in q:
        # Extract genre, search across services
        return ('api_call', 'streaming_search_by_genre')
    elif 'where' in q:
        # "Where can I watch [movie]?"
        return ('api_call', 'streaming_search')
    elif 'recommend' in q:
        return ('api_call', 'streaming_movie_recommendations')

# How to access services
if 'how' in q and any(service in q for service in ['netflix', 'hulu', 'disney', 'hbo', 'prime', 'peacock', 'paramount', 'apple tv', 'youtube tv']):
    return ('quick', "All streaming apps are already logged in on the TV. Just select the app from the home screen and start watching!")

# Login/password questions
if 'password' in q or 'login' in q or 'account' in q:
    return ('quick', "All services are already logged in. No passwords needed! Just open any app and start watching")
```

#### Local Events & Activities

**Comprehensive Baltimore Events Coverage:**

```python
# General events by timeframe
if 'events' in q or 'things to do' in q or 'what to do' in q:
    if 'tonight' in q or 'today' in q:
        return ('api_call', 'baltimore_events_today')
    elif 'tomorrow' in q:
        return ('api_call', 'baltimore_events_tomorrow')
    elif 'weekend' in q or 'this weekend' in q:
        return ('api_call', 'baltimore_events_weekend')
    elif 'week' in q or 'this week' in q:
        return ('api_call', 'baltimore_events_week')
    else:
        return ('api_call', 'baltimore_events_today')  # Default to today

# Specific event categories
EVENT_CATEGORIES = {
    # Music & Entertainment
    'concert': ['concert', 'live music', 'band', 'show'],
    'comedy': ['comedy', 'stand up', 'comedian'],
    'theater': ['theater', 'theatre', 'play', 'musical', 'broadway'],
    'opera': ['opera', 'symphony', 'orchestra', 'bso'],  # Baltimore Symphony

    # Sports & Recreation
    'sports': ['game', 'match', 'ravens', 'orioles', 'lacrosse'],
    'ravens': ['ravens', 'nfl football'],
    'orioles': ['orioles', 'baseball'],

    # Arts & Culture
    'museum': ['museum', 'art gallery', 'exhibit'],
    'festival': ['festival', 'fair', 'celebration'],
    'market': ['farmers market', 'flea market', 'craft market'],

    # Food & Drink
    'food': ['food festival', 'restaurant week', 'food tour'],
    'beer': ['brewery', 'beer festival', 'craft beer'],
    'wine': ['wine tasting', 'wine festival'],

    # Outdoor & Active
    'outdoor': ['outdoor', 'park', 'hiking', 'harbor'],
    'running': ['run', '5k', '10k', 'marathon', 'race'],
    'biking': ['bike', 'cycling'],

    # Family & Kids
    'kids': ['kids', 'children', 'family friendly'],
    'zoo': ['zoo', 'aquarium']
}

# Route to specific event handlers
for category, keywords in EVENT_CATEGORIES.items():
    if any(keyword in q for keyword in keywords):
        return ('api_call', f'events_{category}')

# Live music venues (static info)
if 'live music' in q and ('where' in q or 'venue' in q):
    return ('quick', "Popular live music: 1) Rams Head Live (Power Plant), 2) Soundstage (concert hall), 3) The 8x10 (indie), 4) Cat's Eye Pub (local bands), 5) Peabody Conservatory (classical)")

# Museums (expanded detail)
if 'museum' in q:
    if 'free' in q:
        return ('quick', "FREE museums: Baltimore Museum of Art (always free), Walters Art Museum (always free), American Visionary Art Museum (Wed 5-9pm free)")
    elif 'art' in q:
        return ('quick', "Art museums: 1) BMA (free, world-class), 2) Walters (free, ancient-modern), 3) AVAM ($16, outsider art), 4) Contemporary Museum ($10)")
    elif 'history' in q:
        return ('quick', "History: 1) Fort McHenry ($15, Star-Spangled Banner), 2) B&O Railroad Museum ($20), 3) Maryland Historical Society ($9), 4) Star-Spangled Banner Flag House ($10)")
    elif 'science' in q:
        return ('quick', "Science: Maryland Science Center at Inner Harbor ($25 adults, IMAX + planetarium)")
    else:
        return ('quick', "Top museums: BMA (free), Walters (free), AVAM ($16), National Aquarium ($40), Fort McHenry ($15), Science Center ($25)")

# Aquarium (popular attraction)
if 'aquarium' in q:
    return ('quick', "National Aquarium: Inner Harbor, $40 adults, $25 kids. Book online for discount. Highlights: shark tank, dolphin show, rainforest. 2-3 hours to see everything. 10 min drive from Canton")

# Zoo
if 'zoo' in q:
    return ('quick', "Maryland Zoo: 20 min drive, $20 adults/$15 kids. Open 10am-4pm daily. Highlights: African Journey, penguin coast, polar bears. Get there early!")

# Festivals (seasonal)
if 'festival' in q:
    # Could check current date and suggest seasonal festivals
    return ('api_call', 'baltimore_festivals')

# Harbor events (cruises, water activities)
if 'harbor' in q or 'cruise' in q:
    if 'cruise' in q:
        return ('quick', "Harbor cruises: 1) Spirit Cruises (dinner cruise $80), 2) Baltimore Boat Works (2-hr tour $40), 3) Seadog speedboat ($30). Book online for discount")
    elif 'kayak' in q or 'paddle' in q:
        return ('quick', "Kayak/paddleboard: Canton Kayak Club ($20/hr rentals), Baltimore Boating Center ($25/hr), or bring your own to Canton Waterfront Park")
    else:
        return ('quick', "Inner Harbor: Free to walk, street performers, boats to watch. Visit USS Constellation ($15), Science Center ($25), or take water taxi to Fells Point ($15)")

# Markets
if 'market' in q:
    if 'farmers' in q or 'farm' in q:
        return ('quick', "Farmers markets: 1) Baltimore Farmers Market (Sun 7am-12pm, under JFX), 2) Waverly (Sat 7am-12pm), 3) Fells Point (Sat 8am-12pm). Fresh produce, local vendors")
    elif 'flea' in q or 'antique' in q:
        return ('quick', "Flea/antique markets: 1) Baltimore Antique Row (Howard St), 2) Highlandtown Flea (monthly), 3) Antique Man Cave (Hampden)")
    elif 'lexington' in q:
        return ('quick', "Lexington Market: Downtown, oldest market in US (1782). Open 8am-6pm M-Sat. Famous for Faidley's crab cakes!")
    else:
        return ('api_call', 'baltimore_markets')

# Nightlife
if 'nightlife' in q or 'bar' in q or 'club' in q or 'dance' in q:
    if 'fells point' in q:
        return ('quick', "Fells Point nightlife: 10+ bars, live music everywhere. Try The Horse You Came In On (oldest bar), Cat's Eye Pub (live music), Admirals Cup (nautical theme)")
    elif 'federal hill' in q:
        return ('quick', "Federal Hill: 20+ bars/clubs, young crowd. Cross Street area packed Thu-Sat nights. Good for bar hopping")
    elif 'canton' in q:
        return ('quick', "Canton (you're here!): Koco's Pub, Hudson Street Stackhouse, Looney's, White Marsh Brewing. More laid-back than Fells Point")
    else:
        return ('quick', "Nightlife areas: 1) Fells Point (historic pubs, live music), 2) Federal Hill (young crowd, dance clubs), 3) Power Plant Live (club complex), 4) Canton (local bars)")

# Breweries
if 'brewery' in q or 'craft beer' in q:
    return ('quick', "Local breweries: 1) Union Craft (best tours), 2) Heavy Seas (Canton, 5 min!), 3) Peabody Heights, 4) Guinness Open Gate (experimental), 5) Monument City. Most do tours Sat, tastings daily")

# Tours
if 'tour' in q:
    if 'ghost' in q or 'haunted' in q:
        return ('quick', "Ghost tours: Fells Point Ghost Tour ($20, nightly 7pm & 9pm), Baltimore Ghost Tour ($25, downtown), Annapolis Ghost Tours ($18, 30 min drive)")
    elif 'food' in q or 'eating' in q:
        return ('quick', "Food tours: Charm City Food Tours ($59, 3 hrs, samples from 5-7 restaurants), Fells Point Food Tour ($55), Lexington Market tour ($45)")
    elif 'segway' in q:
        return ('quick', "Segway tours: Inner Harbor Segway ($65, 2 hrs, reservations required), Baltimore Bike & Segway ($60)")
    elif 'bike' in q or 'bicycle' in q:
        return ('quick', "Bike tours: Baltimore Bike Tours ($45, 3 hrs), Bike Party (monthly group ride, free!), or rent bikes at Canton Crossing and explore yourself")
    elif 'water' in q or 'boat' in q:
        return ('quick', "Boat tours: Spirit Cruises ($40-80), Baltimore Water Taxi (hop on/off $15), Seadog speedboat ($30), Urban Pirates (family pirate adventure $28)")
    else:
        return ('api_call', 'baltimore_tours')

# Specific attractions
if 'fort mchenry' in q:
    return ('quick', "Fort McHenry: $15, open 9am-5pm. Where Star-Spangled Banner was written (1814). 15 min drive. Flag ceremony at sunset (check times). Very cool!")

if 'edgar allan poe' in q or 'poe house' in q:
    return ('quick', "Edgar Allan Poe: Poe House ($8, West Baltimore), Poe's grave (Westminster Cemetery, free), Poe statue (UB Law School). Halloween events if visiting in Oct!")

# Day trips
if 'day trip' in q or 'near baltimore' in q:
    return ('quick', "Day trips: 1) Annapolis (30 min, Naval Academy, waterfront), 2) DC (40 min train), 3) Ellicott City (historic town, 30 min), 4) Havre de Grace (waterfront, 45 min), 5) Ocean City (beach, 3 hrs)")

# Seasonal events
if 'christmas' in q or 'holiday' in q:
    return ('quick', "Holiday events: Miracle on 34th Street (Hampden lights), Christmas Village (Inner Harbor), Ice Skating (Inner Harbor), ZooLights (Maryland Zoo), BWI Airport light display")

if 'halloween' in q:
    return ('quick', "Halloween: Poe events (readings, cemetery tours), haunted houses (Bennett's Curse in Parkville), Federal Hill Pumpkin Walk, Fells Point ghost tours")

if 'new year' in q or 'nye' in q:
    return ('quick', "New Year's Eve: Fireworks at Inner Harbor (midnight), NYE cruises (Spirit, $150+), Fells Point bar hopping, Power Plant Live party")
```

#### Event Data Sources & APIs

**Primary Sources:**
```python
EVENT_APIS = {
    'eventbrite': {
        'url': 'https://www.eventbriteapi.com/v3',
        'coverage': 'Concerts, festivals, community events',
        'cost': 'Free tier available',
        'rate_limit': '1000 calls/day'
    },
    'ticketmaster': {
        'url': 'https://app.ticketmaster.com/discovery/v2',
        'coverage': 'Major concerts, sports, theater',
        'cost': 'Free tier: 5000 calls/day',
        'rate_limit': 'Good for professional events'
    },
    'songkick': {
        'url': 'https://api.songkick.com/api/3.0',
        'coverage': 'Live music, concerts only',
        'cost': 'Free with API key',
        'rate_limit': 'Best for music-specific queries'
    },
    'bandsintown': {
        'url': 'https://rest.bandsintown.com',
        'coverage': 'Concert listings',
        'cost': 'Free',
        'rate_limit': 'Excellent concert coverage'
    },
    'meetup': {
        'url': 'https://api.meetup.com',
        'coverage': 'Community events, groups',
        'cost': 'Free with API key',
        'rate_limit': 'Good for local/niche events'
    }
}

# Secondary sources (web scraping if needed)
BALTIMORE_EVENT_SOURCES = {
    'visit_baltimore': 'https://baltimore.org/events',  # Official tourism
    'baltimore_events': 'https://www.baltimoreevents.org',
    'city_paper': 'https://www.citypaper.com/events',  # Local alt-weekly
    'bmore_around_town': 'https://bmorearound.town',
    'baltimore_magazine': 'https://www.baltimoremagazine.com/events'
}

# Venue-specific APIs/feeds
VENUE_SOURCES = {
    'rams_head_live': 'RSS or calendar scraping',
    'soundstage': 'Website calendar',
    'orioles': 'MLB API for game schedule',
    'ravens': 'NFL API for game schedule',
    'hippodrome': 'Broadway shows schedule',
    'lyric_opera': 'BSO calendar'
}
```

**Implementation Example:**
```python
class EventsHandler:
    """Handle local Baltimore events queries"""

    def __init__(self):
        self.eventbrite_key = os.getenv('EVENTBRITE_API_KEY')
        self.ticketmaster_key = os.getenv('TICKETMASTER_API_KEY')
        self.cache_ttl = 3600  # 1 hour cache for events

    def get_events_today(self, category: str = None) -> str:
        """Get events happening today in Baltimore"""

        # Check cache first
        cache_key = f"events_today_{category or 'all'}"
        cached = get_cached_data(cache_key)
        if cached:
            return cached

        # Query Eventbrite for Baltimore events today
        params = {
            'location.address': 'Baltimore, MD',
            'location.within': '15mi',
            'start_date.range_start': datetime.now().isoformat(),
            'start_date.range_end': (datetime.now() + timedelta(days=1)).isoformat(),
            'expand': 'venue',
            'sort_by': 'date'
        }

        if category:
            params['categories'] = self._get_category_id(category)

        response = requests.get(
            'https://www.eventbriteapi.com/v3/events/search/',
            headers={'Authorization': f'Bearer {self.eventbrite_key}'},
            params=params,
            timeout=5
        )

        if response.status_code == 200:
            events = response.json().get('events', [])

            if not events:
                return "No major events tonight in Baltimore. Check local bars for live music!"

            # Format top 3 events
            result = "Events tonight in Baltimore:\n"
            for i, event in enumerate(events[:3], 1):
                name = event['name']['text']
                venue = event['venue']['name'] if 'venue' in event else 'TBA'
                time = datetime.fromisoformat(event['start']['local']).strftime('%I:%M %p')
                result += f"{i}) {name} at {venue} ({time})\n"

            # Cache result
            set_cached_data(cache_key, result)
            return result

        # Fallback to static suggestions
        return "Check baltimore.org/events or Eventbrite for tonight's events"

    def get_concerts(self, timeframe: str = 'today') -> str:
        """Get concert listings"""

        # Use Songkick or Bandsintown API
        # Return formatted list of concerts

    def get_sports_events(self, team: str = None) -> str:
        """Get Ravens/Orioles game schedules"""

        # Use MLB API for Orioles
        # Use NFL API or ESPN for Ravens

    def _get_category_id(self, category: str) -> str:
        """Map category to Eventbrite category ID"""
        category_map = {
            'concert': '103',  # Music
            'comedy': '112',   # Performing Arts
            'sports': '108',   # Sports & Fitness
            'food': '110',     # Food & Drink
            'festival': '113', # Festivals
        }
        return category_map.get(category, '')
```

#### Streaming API Integration

**Data Sources for Streaming Queries:**
```python
STREAMING_APIS = {
    'justwatch': {
        'url': 'https://apis.justwatch.com/content',
        'coverage': 'Search across all streaming platforms',
        'cost': 'Free API available',
        'use_case': 'Where to watch specific shows/movies'
    },
    'tmdb': {
        'url': 'https://api.themoviedb.org/3',
        'coverage': 'Movie/TV metadata, trending, recommendations',
        'cost': 'Free with API key',
        'use_case': 'New releases, trending, recommendations'
    },
    'tvmaze': {
        'url': 'https://api.tvmaze.com',
        'coverage': 'TV show schedules and episodes',
        'cost': 'Free, no API key',
        'use_case': 'When do new episodes air'
    }
}

class StreamingHandler:
    """Handle streaming service queries"""

    # Mapping of streaming service names to provider IDs
    PROVIDER_IDS = {
        'netflix': 8,
        'hulu': 15,
        'disney+': 337,
        'hbo max': 384,
        'prime video': 9,
        'peacock': 387,
        'paramount+': 531,
        'apple tv+': 350,
        'youtube tv': None  # Live TV, not in JustWatch
    }

    def __init__(self):
        self.tmdb_key = os.getenv('TMDB_API_KEY')
        self.cache_ttl = 86400  # 24 hours for streaming data

    def search_where_to_watch(self, query: str) -> str:
        """
        Find which streaming service has a specific show/movie

        Example: "Where can I watch Breaking Bad?"
        Returns: "Breaking Bad is on Netflix"
        """
        # Extract title from query
        title = self._extract_title(query)

        # Search using JustWatch or TMDb
        # Return which of our available services has it

        available_services = []
        for service_name, provider_id in self.PROVIDER_IDS.items():
            if self._title_on_service(title, provider_id):
                available_services.append(service_name.title())

        if available_services:
            services_str = ', '.join(available_services)
            return f"{title} is available on: {services_str}"
        else:
            return f"I don't see {title} on our streaming services. It might be available for rent/purchase"

    def get_new_releases(self, timeframe: str = 'week') -> str:
        """
        Get new movies/shows added this week

        Returns: List of new content across all services
        """
        # Use TMDb API to get new releases
        # Filter to only our available services

        new_content = []
        # Query TMDb for recent additions
        # Format: "New this week: 1) Movie X (Netflix), 2) Show Y (Hulu), 3) Movie Z (Disney+)"

        return "New this week: Check the 'Continue Watching' section on each app for latest additions"

    def get_trending(self, service: str = None) -> str:
        """
        Get trending content on specific service or across all
        """
        # Use TMDb trending endpoint
        # Filter by provider if service specified

        return "Trending now: Check 'Trending' section on Netflix, Hulu, or HBO Max"

    def search_by_genre(self, genre: str) -> str:
        """
        Recommend content by genre across all services

        Example: "Show me action movies"
        """
        # Search TMDb by genre
        # Return recommendations across available services

        return f"For {genre}: Check the {genre.title()} category on Netflix, HBO Max, or Hulu"

    def get_sports_schedule(self, sport: str = None, team: str = None) -> str:
        """
        Get sports viewing info for YouTube TV / Sunday Ticket
        """
        if sport == 'nfl' or team in ['ravens']:
            return "NFL games on YouTube TV. Ravens games on CBS/Fox. Sunday Ticket for out-of-market games"
        elif sport == 'mlb' or team == 'orioles':
            return "Orioles games on MASN (channel varies). Check YouTube TV guide"
        else:
            return "YouTube TV has ESPN, FS1, NBC Sports, CBS Sports. Check the Sports tab"

    def _extract_title(self, query: str) -> str:
        """Extract show/movie title from natural language query"""
        # Remove common question words
        # "Where can I watch Breaking Bad" -> "Breaking Bad"
        pass

    def _title_on_service(self, title: str, provider_id: int) -> bool:
        """Check if title is available on specific provider"""
        # Use JustWatch or TMDb to check availability
        pass
```

**Static Responses for Common Queries:**
```python
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

    'peacock_premier_league': "Peacock has EVERY Premier League match (English soccer). $6/month included"
}
```

#### Movie Theaters
```python
if 'movie theater' in q or 'cinema' in q:
    return ('quick', "Nearest theaters: 1) AMC Towson 8 min drive, 2) Landmark Harbor East 10 min walk, 3) Senator Theatre (historic) 15 min")
```

#### Data Sources Needed
- **Streaming**: JustWatch API, TV Guide API, or TMDb API
- **Local Events**: Eventbrite API, Baltimore events calendar
- **Concerts**: Songkick API, Bandsintown API
- **Movies**: Fandango API or Google Movies

---

## Missing Category 3: Weather Information

### Current State
```python
if 'weather' in q or 'temperature' in q:
    return ('quick', f"I don't have current weather, but typical for {datetime.now().strftime('%B')} in Baltimore. Check weather.com or ask Alexa/Google")
```

### What's Missing

#### Current Weather
```python
if 'weather' in q:
    if 'now' in q or 'current' in q or 'today' in q:
        return ('api_call', 'weather_current')
    elif 'tomorrow' in q:
        return ('api_call', 'weather_tomorrow')
    elif 'weekend' in q or 'saturday' in q or 'sunday' in q:
        return ('api_call', 'weather_weekend')
    elif 'week' in q:
        return ('api_call', 'weather_7day')

# Temperature
if 'temperature' in q or 'temp' in q or 'hot' in q or 'cold' in q:
    return ('api_call', 'weather_temperature')

# Precipitation
if 'rain' in q or 'snow' in q or 'storm' in q:
    return ('api_call', 'weather_precipitation')

# Clothing advice
if 'what to wear' in q or 'jacket' in q:
    return ('api_call', 'weather_clothing_advice')
```

#### Weather API Integration
```python
def get_weather(query_type: str) -> str:
    """Get weather data from API"""
    BALTIMORE_ZIP = "21224"

    # Use Weather.gov API (free, no key required)
    # Or OpenWeatherMap, WeatherAPI.com, etc.

    if query_type == 'weather_current':
        # Fetch current conditions
        # Return: "Currently 65°F and sunny. Winds 5 mph from NW. Feels like 65°F"
        pass

    elif query_type == 'weather_tomorrow':
        # Fetch tomorrow's forecast
        # Return: "Tomorrow: High 72°F, Low 58°F. Partly cloudy with 20% chance of rain"
        pass

    # ... etc
```

#### Data Sources Needed
- **Primary**: Weather.gov API (NOAA - free, no key)
- **Backup**: OpenWeatherMap API, WeatherAPI.com
- **Location**: Canton, Baltimore MD 21224 (39.2808° N, 76.5822° W)

---

## Missing Category 4: Airport & Flight Information

### Current State
- Basic BWI distance information only

### What's Missing

#### Supported Airports
1. **BWI** - Baltimore/Washington International (15 mi, primary)
2. **DCA** - Ronald Reagan Washington National (40 mi)
3. **IAD** - Washington Dulles International (50 mi)
4. **PHL** - Philadelphia International (95 mi)
5. **JFK** - New York JFK (195 mi)
6. **EWR** - Newark Liberty International (185 mi)
7. **LGA** - New York LaGuardia (190 mi)

#### Airport Information Queries
```python
# General airport info
if 'airport' in q:
    if 'closest' in q or 'nearest' in q:
        return ('quick', "Closest airport: BWI (15 mi, 25-30 min, $35-45 Uber). Also: DCA (40 mi), IAD (50 mi), PHL (95 mi)")

    # Specific airport codes
    for airport_code in ['bwi', 'dca', 'iad', 'phl', 'jfk', 'ewr', 'lga']:
        if airport_code in q:
            return ('api_call', f'airport_info_{airport_code.upper()}')

# How to get to airport
if 'how' in q and 'get to' in q and 'airport' in q:
    if 'bwi' in q:
        return ('quick', "To BWI: 1) Uber/Lyft $35-45 (25 min), 2) Light Rail from Canton Crossing ($2, 45 min), 3) MARC train to BWI station then shuttle")
    elif 'dca' in q:
        return ('quick', "To DCA: Uber $60-75 (45 min) or MARC to Union Station + Metro (1.5 hrs, ~$12)")
    elif 'iad' in q:
        return ('quick', "To IAD: Uber $80-100 (1 hr) or MARC to Union Station + Silver Line Express ($12-15, 2 hrs)")

# Flight status
if 'flight' in q and ('status' in q or 'delayed' in q or 'on time' in q):
    # Extract flight number or ask for it
    return ('api_call', 'flight_status')

# Airport delays
if 'delay' in q and 'airport' in q:
    return ('api_call', 'airport_delays')
```

#### Airport Static Data
```python
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
        'phone': '410-859-7111'
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
        'phone': '703-417-8000'
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
        'phone': '703-572-2700'
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
        'phone': '215-937-6937'
    },
    'JFK': {
        'name': 'John F. Kennedy International Airport',
        'code': 'JFK',
        'distance_miles': 195,
        'drive_time': '3.5-4 hrs',
        'amtrak': 'Amtrak to Penn Station NYC, then AirTrain ($60-100 + $8, 3-4 hrs)',
        'airlines': 'All major international carriers',
        'phone': '718-244-4444'
    },
    'EWR': {
        'name': 'Newark Liberty International Airport',
        'code': 'EWR',
        'distance_miles': 185,
        'drive_time': '3-3.5 hrs',
        'amtrak': 'Amtrak to Newark Airport station (2.5 hrs, $60-100)',
        'airlines': 'United (hub), international flights',
        'phone': '973-961-6000'
    },
    'LGA': {
        'name': 'LaGuardia Airport',
        'code': 'LGA',
        'distance_miles': 190,
        'drive_time': '3.5-4 hrs',
        'amtrak': 'Amtrak to Penn Station NYC, then taxi/Uber ($60-100 + $30-40)',
        'airlines': 'Delta (hub), American, United - domestic only',
        'phone': '718-533-3400'
    }
}
```

#### Flight Status API Integration
```python
def get_flight_status(flight_number: str = None, airport_code: str = None) -> str:
    """Get real-time flight status"""

    # API options:
    # 1. FlightAware API (free tier available)
    # 2. AviationStack API
    # 3. FlightStats API (Cirium)
    # 4. FAA APIs

    if flight_number:
        # Lookup specific flight
        # Return: "AA1234 from DCA to BWI: On time, departs 3:45 PM, arrives 4:30 PM"
        pass

    elif airport_code:
        # Get general delays for airport
        # Return: "BWI: Average delays 15 min due to weather. 3 cancellations today"
        pass
```

#### Data Sources Needed
- **Flight Status**: FlightAware API, AviationStack API, FlightStats
- **Airport Delays**: FAA ASPM data, FlightAware
- **Ground Transportation**: Uber API (prices), WMATA API (Metro), SEPTA API (Philly)

---

## Missing Category 5: News & Information

### Current State
- None implemented

### What's Missing

#### Local News (Baltimore)
```python
# Local news
if 'news' in q:
    if 'local' in q or 'baltimore' in q:
        return ('api_call', 'baltimore_news')
    elif 'headlines' in q or 'top' in q:
        return ('api_call', 'national_news_headlines')
    elif 'breaking' in q:
        return ('api_call', 'breaking_news')

# Sports news (beyond scores)
if 'ravens' in q or 'orioles' in q:
    if 'news' in q or 'update' in q or 'injury' in q:
        return ('api_call', 'sports_news')
```

#### News Sources
- **Baltimore**: Baltimore Sun, WBALTV, Fox45, Baltimore Brew
- **National**: AP News, Reuters, NPR
- **Sports**: ESPN, CBS Sports, The Athletic

#### News API Integration
```python
def get_news(query_type: str, topic: str = None) -> str:
    """Fetch news from various sources"""

    # News API, Google News API, RSS feeds

    if query_type == 'baltimore_news':
        # Top 3 Baltimore stories
        # Return: "Top Baltimore news: 1) Harbor cleanup project approved, 2) Ravens sign new linebacker, 3) New restaurant opens in Fells Point"
        pass

    elif query_type == 'national_news_headlines':
        # Top 5 national stories
        pass
```

#### Data Sources Needed
- **News API**: NewsAPI.org, Google News API
- **RSS Feeds**: Baltimore Sun, local TV stations
- **Sports**: ESPN API, CBS Sports API

---

## Missing Category 6: Stock Market & Financial Information

### Current State
- None implemented

### What's Missing

#### Stock Tickers
```python
# Stock price lookup
if 'stock' in q or 'ticker' in q or 'share price' in q:
    # Extract ticker symbol (AAPL, GOOGL, TSLA, etc.)
    return ('api_call', 'stock_quote')

# Market summary
if 'dow' in q or 'nasdaq' in q or 's&p' in q or 'market' in q:
    return ('api_call', 'market_summary')

# Specific tickers by name
common_stocks = {
    'apple': 'AAPL',
    'google': 'GOOGL',
    'amazon': 'AMZN',
    'tesla': 'TSLA',
    'microsoft': 'MSFT',
    'meta': 'META',
    'facebook': 'META',
    'netflix': 'NFLX'
}

for name, ticker in common_stocks.items():
    if name in q:
        return ('api_call', f'stock_quote_{ticker}')
```

#### Market Indices
```python
MARKET_INDICES = {
    'dow': 'DJI',
    'dow jones': 'DJI',
    'nasdaq': 'IXIC',
    's&p': 'SPX',
    's&p 500': 'SPX',
    'russell': 'RUT'
}
```

#### Stock API Integration
```python
def get_stock_data(ticker: str = None, query_type: str = None) -> str:
    """Get stock/market data"""

    # API options:
    # 1. Alpha Vantage (free tier)
    # 2. Yahoo Finance API (unofficial but works)
    # 3. IEX Cloud
    # 4. Finnhub

    if ticker:
        # Return: "AAPL: $175.43 (+2.3%, +$3.94). Day range $173.20-$176.15. Market cap $2.8T"
        pass

    elif query_type == 'market_summary':
        # Return: "Dow: 35,432 (+0.8%), Nasdaq: 14,234 (+1.2%), S&P 500: 4,567 (+0.9%)"
        pass
```

#### Cryptocurrency (Optional)
```python
# Crypto prices
if 'bitcoin' in q or 'btc' in q:
    return ('api_call', 'crypto_BTC')

if 'ethereum' in q or 'eth' in q:
    return ('api_call', 'crypto_ETH')
```

#### Data Sources Needed
- **Stocks**: Alpha Vantage API (free tier), Yahoo Finance, IEX Cloud
- **Crypto**: CoinGecko API, CoinMarketCap API
- **Market News**: Bloomberg API, CNBC feeds

---

## Missing Category 7: General Web Search Fallback

### Current State
- Unclassified queries go directly to LLM
- No web search capability

### What's Missing

#### Web Search Integration
```python
def analyze_query(query: str) -> Tuple[str, str]:
    """Enhanced query analysis with web search fallback"""

    # ... existing classification logic ...

    # Check if query needs current/factual information
    needs_current_info = any(word in q for word in [
        'latest', 'current', 'recent', 'today', 'now',
        'who is', 'what is', 'when did', 'where is'
    ])

    # Check if LLM likely doesn't know the answer
    likely_unknown = any(pattern in q for pattern in [
        'phone number', 'address of', 'hours', 'open',
        'website', 'email', 'contact'
    ])

    # If no other classification matches and needs current info
    if needs_current_info or likely_unknown:
        return ('web_search', query)

    # Default: Let LLM handle
    return ('llm', 'general')
```

#### Web Search Implementation
```python
def web_search(query: str) -> str:
    """Perform web search and return concise answer"""

    # API options:
    # 1. DuckDuckGo Instant Answer API (free, no key)
    # 2. Google Custom Search API (100 free queries/day)
    # 3. Brave Search API
    # 4. SerpAPI (Google results)

    try:
        # DuckDuckGo example (simplest, free)
        response = requests.get(
            'https://api.duckduckgo.com/',
            params={
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            },
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            # Get instant answer or abstract
            answer = data.get('AbstractText') or data.get('Answer')

            if answer:
                return ('quick', answer[:300])  # Truncate to 300 chars

        # Fallback to LLM if web search fails
        return ('llm', 'general')

    except Exception as e:
        logger.error(f"Web search error: {e}")
        return ('llm', 'general')
```

#### Use Cases for Web Search
- Business hours: "What time does Koco's Pub close?"
- Phone numbers: "Phone number for Canton Water Taxi"
- Current events: "Who won the election?"
- Definitions: "What is a blue crab?"
- Factual lookup: "How tall is the Washington Monument?"
- Unknown local businesses: "Where is the nearest dry cleaner?"

#### Data Sources Needed
- **Primary**: DuckDuckGo Instant Answer API (free, no auth)
- **Backup**: Google Custom Search, Brave Search API
- **Fallback**: Always return to LLM if search fails

---

## Implementation Priority

### Phase 1: Essential Guest Information (Week 1)
1. ✅ **Weather** - Most frequently asked
2. ✅ **Airport Info (BWI, DCA, IAD)** - Travel planning
3. ✅ **Web Search Fallback** - Catch-all for unknown queries

### Phase 2: Extended Travel (Week 2)
4. ✅ **Flight Status** - Real-time travel info
5. ✅ **Transportation (detailed)** - Complete transit options
6. ✅ **Airport Info (PHL, JFK, EWR, LGA)** - Extended airports

### Phase 3: Entertainment & Activities (Week 3)
7. ✅ **Streaming Services** - TV/movie recommendations
8. ✅ **Local Events** - Things to do
9. ✅ **Movie Theaters** - Cinema options

### Phase 4: News & Finance (Week 4)
10. ✅ **News** - Local and national
11. ✅ **Stock Market** - Ticker quotes and indices

---

## Data Source Requirements Summary

### Free / No Auth Required
- ✅ **Weather.gov API** - NOAA weather data
- ✅ **DuckDuckGo Instant Answer** - Web search
- ✅ **MTA Maryland** - Transit schedules (scraping or RSS)
- ✅ **Yahoo Finance** - Stock quotes (unofficial API)

### Free Tier / Auth Required
- ✅ **OpenWeatherMap** - Weather (1000 calls/day free)
- ✅ **Alpha Vantage** - Stock market (500 calls/day free)
- ✅ **NewsAPI.org** - News headlines (100 calls/day free)
- ✅ **FlightAware** - Flight tracking (free tier available)
- ✅ **JustWatch API** - Streaming service search
- ✅ **TMDb API** - Movie/TV data (free with attribution)

### Paid / Premium
- ⚠️ **Google Custom Search** - 100 free/day, then $5/1000
- ⚠️ **FlightStats (Cirium)** - Professional flight data
- ⚠️ **SerpAPI** - Google search results
- ⚠️ **IEX Cloud** - Financial data (free tier limited)

### To Be Determined
- ❓ **Streaming Services List** - Need user to provide
- ❓ **Twilio** - Already configured for SMS?
- ❓ **Eventbrite** - Local events (free tier?)

---

## Recommended Implementation Approach

### 1. Create Intent Classification Module
```python
# src/jetson/intent_classifier.py

class IntentClassifier:
    """
    Comprehensive intent classification for Airbnb guest queries

    Returns: (intent_type, handler, data)
    - intent_type: 'quick' | 'api_call' | 'web_search' | 'llm'
    - handler: Function name or endpoint to call
    - data: Any additional context needed
    """

    def __init__(self):
        self.cache = {}
        self.api_handlers = {
            'weather': WeatherHandler(),
            'flights': FlightHandler(),
            'stocks': StockHandler(),
            'news': NewsHandler(),
            'streaming': StreamingHandler(),
            'events': EventsHandler(),
            'web_search': WebSearchHandler()
        }

    def classify(self, query: str) -> Tuple[str, str, Any]:
        """Main classification entry point"""
        pass
```

### 2. Create API Handler Classes
```python
# src/jetson/api_handlers/weather.py
class WeatherHandler:
    def get_current(self, location: str) -> str:
        pass

    def get_forecast(self, location: str, days: int = 1) -> str:
        pass

# src/jetson/api_handlers/flights.py
class FlightHandler:
    def get_status(self, flight_number: str) -> str:
        pass

    def get_airport_delays(self, airport_code: str) -> str:
        pass

# Similar for stocks, news, streaming, events, web_search
```

### 3. Create Configuration for APIs
```python
# src/jetson/config/api_config.py

API_KEYS = {
    'weather': os.getenv('OPENWEATHER_API_KEY', ''),
    'news': os.getenv('NEWSAPI_KEY', ''),
    'stocks': os.getenv('ALPHAVANTAGE_KEY', ''),
    'flights': os.getenv('FLIGHTAWARE_KEY', ''),
    'streaming': os.getenv('JUSTWATCH_KEY', ''),
}

API_ENDPOINTS = {
    'weather': 'https://api.weather.gov',
    'weather_backup': 'https://api.openweathermap.org/data/2.5',
    'news': 'https://newsapi.org/v2',
    'stocks': 'https://www.alphavantage.co/query',
    'flights': 'https://aeroapi.flightaware.com/aeroapi',
    'web_search': 'https://api.duckduckgo.com',
}
```

### 4. Update Facade to Use Intent Classifier
```python
# research/jetson-iterations/ollama_baltimore_smart_facade.py

from intent_classifier import IntentClassifier

classifier = IntentClassifier()

def analyze_query(query: str) -> Tuple[str, str]:
    """Use new comprehensive intent classifier"""
    intent_type, handler, data = classifier.classify(query)

    if intent_type == 'quick':
        return ('quick', data)  # Static response

    elif intent_type == 'api_call':
        # Call external API
        result = classifier.api_handlers[handler].execute(data)
        return ('quick', result)

    elif intent_type == 'web_search':
        # Perform web search
        result = classifier.api_handlers['web_search'].search(query)
        return ('quick', result)

    else:  # llm
        return ('llm', 'general')
```

---

## Success Criteria

### Coverage Metrics
- ✅ **Weather queries**: 100% answered with real-time data
- ✅ **Airport information**: All 7 airports covered
- ✅ **Flight status**: Real-time lookup available
- ✅ **Transportation**: Comprehensive options (car, transit, bike, etc.)
- ✅ **Entertainment**: Streaming + local events + theaters
- ✅ **News**: Local Baltimore + national headlines
- ✅ **Financial**: Stock tickers + market indices
- ✅ **Web search**: Fallback for >90% of unclassified queries

### Performance Metrics
- Quick responses (<500ms) for all cached/static data
- API calls complete in <3 seconds
- Web search completes in <5 seconds
- Cache hit rate >70% for common queries
- <5% fallback to LLM for factual questions

### User Experience
- Guests get specific, actionable answers
- No "I don't know" responses for common questions
- Current, accurate information (not LLM training data)
- Concise responses (1-2 sentences max)

---

## Next Steps

1. **Get Streaming Services List** from user
2. **Select APIs** - Choose free tiers for Phase 1
3. **Implement Intent Classifier** - Comprehensive classification logic
4. **Create API Handlers** - Weather, airports, flights (Phase 1)
5. **Test & Validate** - Real queries from Airbnb guests
6. **Add Remaining Categories** - Phases 2-4
7. **Monitor & Tune** - Track most common queries, optimize responses

---

## Research Summary

### Complete Feature Coverage Documented

✅ **Transportation** (Comprehensive)
- Public transit (bus, Light Rail, water taxi, MARC, Amtrak)
- Rideshare (Uber/Lyft pricing)
- Bike share and scooters
- Parking information
- 7 airports covered (BWI, DCA, IAD, PHL, JFK, EWR, LGA)

✅ **Entertainment** (10 Streaming Services)
- Netflix, Hulu, Disney+, HBO Max, Prime Video
- Peacock, Paramount+, Apple TV+
- YouTube TV (100+ channels)
- NFL Sunday Ticket
- Local events via Eventbrite, Ticketmaster, Songkick APIs

✅ **Weather** (Real-time)
- Current conditions
- Hourly/daily/weekly forecasts
- Temperature, precipitation, clothing advice
- Weather.gov API (free) + OpenWeatherMap backup

✅ **Airport & Flights**
- All 7 airports with detailed info
- Flight status lookups (FlightAware API)
- Airport delay information
- Ground transportation options

✅ **News**
- Baltimore local news
- National headlines
- Sports news (Ravens/Orioles)
- NewsAPI.org integration

✅ **Financial**
- Stock ticker quotes (Alpha Vantage)
- Market indices (Dow, Nasdaq, S&P)
- Crypto prices (optional)

✅ **Web Search Fallback**
- DuckDuckGo Instant Answer API
- Catches unclassified queries
- No API key required

✅ **Local Events** (Comprehensive)
- 19 event categories documented
- Museums, festivals, concerts, sports
- Breweries, nightlife, tours
- Seasonal events (Christmas, Halloween, NYE)
- Day trips and attractions

### API Requirements Summary

**Free Tier / No Auth:**
- Weather.gov (NOAA) - Weather data
- DuckDuckGo - Web search
- TVMaze - TV schedules
- Yahoo Finance (unofficial) - Stock quotes

**Free Tier / API Key Required:**
- OpenWeatherMap - Weather (1000/day)
- TMDb - Movies/TV (free with attribution)
- Alpha Vantage - Stocks (500/day)
- NewsAPI.org - News (100/day)
- FlightAware - Flight tracking
- Eventbrite - Events (1000/day)
- Ticketmaster - Events (5000/day)
- Songkick - Concerts (free)
- Bandsintown - Concerts (free)
- JustWatch - Streaming search

**Total Estimated API Calls/Day:**
- Weather: ~100 calls (guests check frequently)
- News: ~50 calls
- Events: ~50 calls
- Streaming: ~30 calls
- Flights: ~20 calls
- Stocks: ~10 calls
- Web search: ~100 calls
- **Total: ~360 calls/day** (well within free tiers)

### Implementation Phases Updated

**Phase 1: Essential Guest Information (Week 1) - Priority**
1. Weather (Weather.gov + OpenWeatherMap)
2. Web Search Fallback (DuckDuckGo)
3. Airport Info (BWI, DCA, IAD static data)
4. Streaming Services (static quick answers)

**Phase 2: Extended Travel & Events (Week 2)**
5. Flight Status (FlightAware API)
6. Transportation Details (MTA, Water Taxi schedules)
7. Local Events (Eventbrite, Ticketmaster)
8. Airport Info (PHL, JFK, EWR, LGA)

**Phase 3: Entertainment Deep Dive (Week 3)**
9. Streaming Search (JustWatch, TMDb)
10. TV Schedules (TVMaze)
11. Movie Theaters
12. Concerts (Songkick, Bandsintown)

**Phase 4: News & Finance (Week 4)**
13. News (NewsAPI, local sources)
14. Stock Market (Alpha Vantage)
15. Sports News (ESPN API)

### Next Steps

1. ✅ **Streaming Services List** - COMPLETE (10 services documented)
2. **Select & Register APIs** - Sign up for free tier API keys
3. **Create Intent Classifier Module** - Comprehensive classification engine
4. **Implement API Handlers** - Weather, Events, Streaming, Flights, etc.
5. **Update Facade** - Integrate new handlers into ollama_baltimore_smart_facade.py
6. **Test & Validate** - Real guest queries
7. **Monitor & Optimize** - Track hit rates, optimize responses

### Success Metrics

**Coverage:**
- ✅ 100% of transportation queries answered
- ✅ 100% of weather queries with real-time data
- ✅ 100% of streaming service questions
- ✅ 95%+ of local events/activities
- ✅ 90%+ web search fallback effectiveness

**Performance:**
- Quick responses: <500ms (static/cached)
- API calls: <3s
- Web search: <5s
- Cache hit rate: >70%
- <5% fallback to LLM for factual queries

**User Experience:**
- Specific, actionable answers
- No "I don't know" for common questions
- Current, accurate information
- Concise responses (1-3 sentences)

---

**Research Status**: ✅ COMPLETE
**Next Action**: Select APIs and begin Phase 1 implementation
**Estimated Effort**: 4 weeks full implementation (4 phases)
**Dependencies**: API keys for free tier services
