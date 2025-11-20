"""
Sports RAG Service - TheSportsDB Integration

Provides sports team and game data retrieval with caching.

Endpoints:
- GET /health - Health check
- GET /sports/teams/search?query={query} - Search teams
- GET /sports/teams/{team_id} - Get team details
- GET /sports/events/{team_id}/next - Get next events for team
- GET /sports/events/{team_id}/last - Get last events for team
"""

import os
import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse
import httpx
from contextlib import asynccontextmanager
import feedparser

# Import shared utilities
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.cache import CacheClient, cached
from shared.logging_config import configure_logging

# Configure logging
logger = configure_logging("sports-rag")

# Environment variables / defaults
ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://localhost:8080")
NEWS_GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")  # Optional key if provided via admin
THESPORTSDB_API_KEY = os.getenv("THESPORTSDB_API_KEY", "3")  # Free tier key
THESPORTSDB_BASE_URL = os.getenv(
    "THESPORTSDB_BASE_URL",
    f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_API_KEY}"
)
API_FOOTBALL_KEY_DEFAULT = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE_URL_DEFAULT = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")
REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.10.181:6379/0")
SERVICE_PORT = int(os.getenv("SPORTS_SERVICE_PORT", "8011"))

# Fixed endpoints
ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"
OLYMPICS_BASE_URL = "https://olympics.com"

# Cache client and HTTP client
cache = None
http_client = None

# API configs loaded from admin database (with env fallbacks)
api_configs = {
    "thesportsdb": {"endpoint_url": THESPORTSDB_BASE_URL, "api_key": None},
    "espn": {"endpoint_url": ESPN_BASE_URL, "api_key": None},
    "api-football": {"endpoint_url": API_FOOTBALL_BASE_URL_DEFAULT, "api_key": API_FOOTBALL_KEY_DEFAULT},
    "olympics": {"endpoint_url": OLYMPICS_BASE_URL, "api_key": None},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global cache, http_client

    # Startup
    logger.info("Starting Sports RAG service")
    cache = CacheClient(url=REDIS_URL)
    await cache.connect()

    # OPTIMIZATION: Create reusable HTTP client
    http_client = httpx.AsyncClient(timeout=10.0)
    logger.info("HTTP client initialized")

    # Load API configs from admin API (with fallbacks)
    await initialize_api_configs()

    yield

    # Shutdown
    logger.info("Shutting down Sports RAG service")
    if http_client:
        await http_client.aclose()
    if cache:
        await cache.disconnect()


app = FastAPI(
    title="Sports RAG Service",
    description="TheSportsDB integration with caching",
    version="1.0.0",
    lifespan=lifespan
)


async def get_api_key_config(service_name: str) -> Optional[Dict[str, Any]]:
    """Fetch API key/config from admin backend."""
    try:
        response = await http_client.get(
            f"{ADMIN_API_URL}/api/external-api-keys/public/{service_name}/key",
            timeout=5.0
        )
        response.raise_for_status()
        data = response.json()
        return {
            "endpoint_url": data.get("endpoint_url"),
            "api_key": data.get("api_key"),
            "rate_limit_per_minute": data.get("rate_limit_per_minute"),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch API key for {service_name}: {e}")
        return None


async def initialize_api_configs():
    """Load API configuration from admin backend with env fallbacks."""
    global api_configs

    api_football = await get_api_key_config("api-football")
    if api_football and api_football.get("api_key"):
        api_configs["api-football"].update(api_football)
        logger.info("Loaded API-Football config from admin API")
    else:
        logger.info("Using fallback API-Football config (env)", has_key=bool(API_FOOTBALL_KEY_DEFAULT))

    thesportsdb = await get_api_key_config("thesportsdb")
    if thesportsdb and thesportsdb.get("endpoint_url"):
        api_configs["thesportsdb"].update(thesportsdb)
        logger.info("Loaded TheSportsDB config from admin API")

    # ESPN has no key, but allow admin override of endpoint
    espn_cfg = await get_api_key_config("espn")
    if espn_cfg and espn_cfg.get("endpoint_url"):
        api_configs["espn"].update({"endpoint_url": espn_cfg["endpoint_url"]})

    # Olympics (currently public endpoints; no key expected)
    olympics_cfg = await get_api_key_config("olympics")
    if olympics_cfg and olympics_cfg.get("endpoint_url"):
        api_configs["olympics"].update({"endpoint_url": olympics_cfg["endpoint_url"]})

    logger.info(
        "api_configs_initialized",
        api_football=bool(api_configs.get("api-football", {}).get("api_key")),
        thesportsdb_endpoint=api_configs["thesportsdb"]["endpoint_url"],
        espn_endpoint=api_configs["espn"]["endpoint_url"],
        olympics_endpoint=api_configs["olympics"]["endpoint_url"],
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sports-rag",
        "version": "1.0.0"
    }


def build_url(base: str, path: str) -> str:
    """Safely join base URL and path."""
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def parse_team_identifier(team_id: str) -> Tuple[str, str, Optional[str]]:
    """
    Parse team identifier into provider, raw id, and optional sport.
    Formats:
        - thesportsdb: "<numeric>"
        - espn: "espn:<sport>:<team_id>"
        - api-football: "api-football:<team_id>"
    """
    if ":" not in team_id:
        return "thesportsdb", team_id, None

    parts = team_id.split(":")
    if len(parts) == 3 and parts[0] == "espn":
        sport_path = parts[1].replace("-", "/")
        return "espn", parts[2], sport_path
    if len(parts) == 2 and parts[0] == "api-football":
        return "api-football", parts[1], None

    # Olympics events may use "olympics:<sport>:<id>" in future expansion
    if len(parts) >= 2 and parts[0] == "olympics":
        return "olympics", parts[-1], ":".join(parts[1:-1])

    return "thesportsdb", team_id, None


def _normalize_thesportsdb_team(team: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize TheSportsDB team payload."""
    normalized = dict(team)
    normalized["source"] = "thesportsdb"
    return normalized


def _normalize_espn_team(team: Dict[str, Any], sport: str) -> Dict[str, Any]:
    """Normalize ESPN team payload into expected fields."""
    team_id = team.get("id") or team.get("uid", "").split(":")[-1]
    display_name = team.get("displayName") or team.get("name")
    sport_safe = sport.replace("/", "-") if sport else sport
    return {
        "idTeam": f"espn:{sport_safe}:{team_id}",
        "strTeam": display_name,
        "strTeamShort": team.get("abbreviation"),
        "strLeague": sport,
        "strSport": sport.split("/")[0] if sport else None,
        "source": "espn"
    }


def _normalize_api_football_team(team_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize API-Football team payload."""
    team = team_payload.get("team", {})
    return {
        "idTeam": f"api-football:{team.get('id')}",
        "strTeam": team.get("name"),
        "strLeague": team_payload.get("country"),
        "strSport": "soccer",
        "strStadium": team.get("venue", {}).get("name") if isinstance(team.get("venue"), dict) else None,
        "source": "api-football"
    }


def _sort_events_by_date(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort events by date, prioritize upcoming; fallback to recent past if no future."""
    now = datetime.now(timezone.utc).date()
    parsed: List[Tuple[datetime.date, Dict[str, Any]]] = []
    for ev in events:
        date_str = ev.get("dateEvent") or ev.get("date") or ""
        try:
            # Support ISO date or datetime
            d = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except Exception:
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                continue
        parsed.append((d, ev))

    future = [(d, ev) for d, ev in parsed if d >= now]
    past = [(d, ev) for d, ev in parsed if d < now]

    future_sorted = sorted(future, key=lambda x: x[0])
    past_sorted = sorted(past, key=lambda x: x[0], reverse=True)

    ordered = future_sorted or past_sorted
    return [ev for _, ev in ordered]


def _filter_events_window(events: List[Dict[str, Any]], days_ahead: int = 7) -> List[Dict[str, Any]]:
    """Filter events to today through today+days_ahead."""
    now = datetime.now(timezone.utc).date()
    window_end = now + timedelta(days=days_ahead)
    filtered: List[Dict[str, Any]] = []
    for ev in events:
        date_str = ev.get("dateEvent") or ev.get("date")
        try:
            d = datetime.fromisoformat((date_str or "").replace("Z", "+00:00")).date()
        except Exception:
            try:
                d = datetime.strptime(date_str or "", "%Y-%m-%d").date()
            except Exception:
                continue
        if now <= d <= window_end:
            filtered.append(ev)
    return filtered


async def fetch_news(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch sports news headlines using RSS (Google News) with optional GNews API override.
    """
    headlines: List[Dict[str, Any]] = []

    # Prefer GNews API if key available
    if NEWS_GNEWS_API_KEY:
        try:
            resp = await http_client.get(
                "https://gnews.io/api/v4/search",
                params={"q": query, "lang": "en", "max": limit, "token": NEWS_GNEWS_API_KEY},
                timeout=5.0
            )
            resp.raise_for_status()
            data = resp.json()
            for article in data.get("articles", [])[:limit]:
                headlines.append({
                    "title": article.get("title"),
                    "link": article.get("url"),
                    "published": article.get("publishedAt"),
                    "source": article.get("source", {}).get("name", "gnews")
                })
        except Exception as e:
            logger.warning(f"GNews fetch failed, falling back to RSS: {e}")

    if len(headlines) < limit:
        # Fallback to Google News RSS search
        try:
            rss_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}"
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:limit]:
                headlines.append({
                    "title": entry.get("title"),
                    "link": entry.get("link"),
                    "published": entry.get("published"),
                    "source": entry.get("source", {}).get("title") if entry.get("source") else "google_news"
                })
        except Exception as e:
            logger.warning(f"RSS fetch failed: {e}")

    return headlines[:limit]


async def fetch_olympics_events(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Best-effort Olympics events via news headlines (no stable free schedule API).
    """
    enriched_query = f"Olympics {query} schedule"
    headlines = await fetch_news(enriched_query, limit=limit)
    events: List[Dict[str, Any]] = []
    for h in headlines:
        events.append({
            "strEvent": h.get("title"),
            "dateEvent": h.get("published"),
            "strHomeTeam": None,
            "strAwayTeam": None,
            "source": h.get("source", "olympics-news"),
            "link": h.get("link")
        })
    return events

@cached(ttl=3600, key_prefix="team_search_v2")  # Cache for 1 hour; v2 to invalidate old schema
async def search_teams_parallel(query: str) -> List[Dict[str, Any]]:
    """
    Search for teams across providers in parallel and return first provider with data.
    """
    async def search_thesportsdb(q: str):
        try:
            url = build_url(api_configs["thesportsdb"]["endpoint_url"], "searchteams.php")
            response = await http_client.get(url, params={"t": q}, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            teams = data.get("teams", []) or []
            teams = [_normalize_thesportsdb_team(t) for t in teams]
            return {"source": "thesportsdb", "teams": teams}
        except Exception as e:
            logger.warning(f"TheSportsDB search failed: {e}")
            return {"source": "thesportsdb", "teams": []}

    async def search_espn(q: str):
        try:
            searches = []
            for sport in [
                "football/nfl",
                "basketball/nba",
                "baseball/mlb",
                "hockey/nhl",
                # Popular soccer leagues (covers most queries; API-Football also handles global teams)
                "soccer/eng.1",      # English Premier League
                "soccer/usa.1",      # MLS
                "soccer/esp.1",      # La Liga
                "soccer/ita.1",      # Serie A
                "soccer/ger.1",      # Bundesliga
                "soccer/fra.1",      # Ligue 1
                "soccer/uefa.champions"
            ]:
                url = build_url(api_configs["espn"]["endpoint_url"], f"{sport}/teams")
                searches.append((sport, http_client.get(url, timeout=5.0)))

            responses = await asyncio.gather(*[s[1] for s in searches], return_exceptions=True)
            all_teams: List[Dict[str, Any]] = []
            for idx, resp in enumerate(responses):
                sport = searches[idx][0]
                if isinstance(resp, httpx.Response):
                    data = resp.json()
                    # ESPN nests teams under sports -> leagues -> teams
                    teams_nested = (
                        data.get("sports", [{}])[0]
                        .get("leagues", [{}])[0]
                        .get("teams", [])
                        or []
                    )
                    # Fallback if structure changes
                    teams = teams_nested or data.get("teams", []) or []
                    matching = []
                    for t in teams:
                        normalized = _normalize_espn_team(t.get("team", t), sport)
                        name = normalized.get("strTeam", "") or ""
                        if q.lower() in name.lower():
                            matching.append(normalized)
                    all_teams.extend(matching)
            return {"source": "espn", "teams": all_teams}
        except Exception as e:
            logger.warning(f"ESPN search failed: {e}")
            return {"source": "espn", "teams": []}

    async def search_api_football(q: str):
        cfg = api_configs.get("api-football", {})
        if not cfg.get("api_key"):
            return {"source": "api-football", "teams": []}

        try:
            url = build_url(cfg["endpoint_url"], "teams")
            response = await http_client.get(
                url,
                headers={"x-apisports-key": cfg["api_key"]},
                params={"search": q},
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            teams = data.get("response", []) or []
            teams = [_normalize_api_football_team(t) for t in teams]
            return {"source": "api-football", "teams": teams}
        except Exception as e:
            logger.warning(f"API-Football search failed: {e}")
            return {"source": "api-football", "teams": []}

    logger.info(f"Searching teams in parallel across providers: {query}")
    results = await asyncio.gather(
        search_thesportsdb(query),
        search_espn(query),
        search_api_football(query),
        return_exceptions=False
    )

    # Prefer more reliable providers first (ESPN, API-Football) before falling back to TheSportsDB
    results_by_source = {result["source"]: result for result in results if isinstance(result, dict)}
    for source in ["espn", "api-football", "thesportsdb"]:
        provider_result = results_by_source.get(source)
        if provider_result and provider_result.get("teams"):
            logger.info("Using teams from provider", provider=source, count=len(provider_result["teams"]))
            return provider_result["teams"]

    logger.warning(f"No teams found across providers for query: {query}")
    return []


async def get_team_info_api(team_id: str) -> Dict[str, Any]:
    """Get team info based on provider identifier."""
    provider, raw_id, sport = parse_team_identifier(team_id)

    if provider == "thesportsdb":
        url = build_url(api_configs["thesportsdb"]["endpoint_url"], "lookupteam.php")
        response = await http_client.get(url, params={"id": raw_id}, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        teams = data.get("teams", [])
        if not teams:
            raise ValueError(f"Team not found: {team_id}")
        team = teams[0]
        team["source"] = "thesportsdb"
        return team

    if provider == "espn":
        url = build_url(api_configs["espn"]["endpoint_url"], f"{sport}/teams/{raw_id}")
        response = await http_client.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        return _normalize_espn_team(data.get("team", data), sport)

    if provider == "api-football":
        cfg = api_configs.get("api-football", {})
        if not cfg.get("api_key"):
            raise ValueError("API-Football key not configured")
        url = build_url(cfg["endpoint_url"], "teams")
        response = await http_client.get(
            url,
            headers={"x-apisports-key": cfg["api_key"]},
            params={"id": raw_id},
            timeout=5.0
        )
        response.raise_for_status()
        data = response.json()
        if data.get("response"):
            return _normalize_api_football_team(data["response"][0])
        raise ValueError(f"Team not found: {team_id}")

    raise ValueError(f"Unknown provider for team id: {team_id}")


@cached(ttl=600, key_prefix="next_events_v4")  # Cache for 10 minutes; v4 to avoid stale/old windows
async def get_next_events_api(team_id: str) -> List[Dict[str, Any]]:
    """Get next events for a team (provider-aware)."""
    provider, raw_id, sport = parse_team_identifier(team_id)
    logger.info(f"Fetching next events for team: {team_id}", provider=provider)

    if provider == "thesportsdb":
        url = build_url(api_configs["thesportsdb"]["endpoint_url"], "eventsnext.php")
        response = await http_client.get(url, params={"id": raw_id}, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        events = data.get("events", []) or []
        for event in events:
            event["source"] = "thesportsdb"
        filtered = _filter_events_window(events, days_ahead=7)
        return _sort_events_by_date(filtered)[:5]

    if provider == "espn" and sport:
        url = build_url(api_configs["espn"]["endpoint_url"], f"{sport}/teams/{raw_id}/schedule")
        response = await http_client.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        events_raw = data.get("events", []) or []
        events_pruned: List[Dict[str, Any]] = []
        for event in events_raw:
            comp = (event.get("competitions") or [{}])[0]
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            # Parse start time and filter to next 7 days
            start_raw = event.get("date")
            try:
                start = datetime.fromisoformat(start_raw.replace("Z", "+00:00")) if start_raw else None
            except Exception:
                start = None
            now = datetime.now(timezone.utc)
            week_end = now + timedelta(days=7)
            if start and not (now <= start <= week_end):
                continue

            events_pruned.append({
                "strEvent": event.get("name"),
                "dateEvent": start.date().isoformat() if start else (event.get("date") or "").split("T")[0],
                "strHomeTeam": home.get("team", {}).get("displayName"),
                "strAwayTeam": away.get("team", {}).get("displayName"),
                "source": "espn"
            })
        events_pruned = _filter_events_window(events_pruned, days_ahead=7)
        return _sort_events_by_date(events_pruned)[:5]

    if provider == "api-football":
        cfg = api_configs.get("api-football", {})
        if not cfg.get("api_key"):
            return []
        url = build_url(cfg["endpoint_url"], "fixtures")
        response = await http_client.get(
            url,
            headers={"x-apisports-key": cfg["api_key"]},
            params={
                "team": raw_id,
                "from": datetime.utcnow().date().isoformat(),
                "to": (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
            },
            timeout=5.0
        )
        response.raise_for_status()
        data = response.json()
        events = []
        for fixture in data.get("response", []) or []:
            start_raw = fixture.get("fixture", {}).get("date")
            try:
                start = datetime.fromisoformat(start_raw.replace("Z", "+00:00")) if start_raw else None
            except Exception:
                start = None
            if start and not (window_start <= start <= window_end):
                continue
            teams = fixture.get("teams", {})
            events.append({
                "strEvent": fixture.get("fixture", {}).get("status", {}).get("long") or fixture.get("league", {}).get("name") or "Fixture",
                "dateEvent": start.date().isoformat() if start else (fixture.get("fixture", {}).get("date") or "").split("T")[0],
                "strHomeTeam": (teams.get("home") or {}).get("name"),
                "strAwayTeam": (teams.get("away") or {}).get("name"),
                "source": "api-football"
            })
        return _sort_events_by_date(events)[:5]

    return []


@cached(ttl=600, key_prefix="last_events_v2")  # Cache for 10 minutes; v2 to avoid stale data
async def get_last_events_api(team_id: str) -> List[Dict[str, Any]]:
    """Get last events for a team (provider-aware)."""
    provider, raw_id, sport = parse_team_identifier(team_id)
    logger.info(f"Fetching last events for team: {team_id}", provider=provider)

    if provider == "thesportsdb":
        url = build_url(api_configs["thesportsdb"]["endpoint_url"], "eventslast.php")
        response = await http_client.get(url, params={"id": raw_id}, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        events = data.get("results", []) or []
        for event in events:
            event["source"] = "thesportsdb"
        return events

    if provider == "espn" and sport:
        url = build_url(api_configs["espn"]["endpoint_url"], f"{sport}/teams/{raw_id}/schedule")
        response = await http_client.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        events = []
        for event in reversed(data.get("events", []) or [])[:5]:
            comp = (event.get("competitions") or [{}])[0]
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            events.append({
                "strEvent": event.get("name"),
                "dateEvent": (event.get("date") or "").split("T")[0],
                "strHomeTeam": home.get("team", {}).get("displayName"),
                "strAwayTeam": away.get("team", {}).get("displayName"),
                "source": "espn"
            })
        return events

    if provider == "api-football":
        cfg = api_configs.get("api-football", {})
        if not cfg.get("api_key"):
            return []
        url = build_url(cfg["endpoint_url"], "fixtures")
        response = await http_client.get(
            url,
            headers={"x-apisports-key": cfg["api_key"]},
            params={"team": raw_id, "last": 5},
            timeout=5.0
        )
        response.raise_for_status()
        data = response.json()
        events = []
        for fixture in data.get("response", []) or []:
            teams = fixture.get("teams", {})
            events.append({
                "strEvent": fixture.get("fixture", {}).get("status", {}).get("long") or "Fixture",
                "dateEvent": (fixture.get("fixture", {}).get("date") or "").split("T")[0],
                "strHomeTeam": (teams.get("home") or {}).get("name"),
                "strAwayTeam": (teams.get("away") or {}).get("name"),
                "source": "api-football"
            })
        return events

    return []


@app.get("/sports/teams/search")
async def search_teams(
    query: str = Query(..., description="Team name to search")
):
    """Search for teams by name."""
    try:
        teams = await search_teams_parallel(query)
        return {"query": query, "teams": teams, "count": len(teams)}
    except httpx.HTTPStatusError as e:
        logger.error(f"TheSportsDB API error: {e}")
        raise HTTPException(status_code=502, detail="Sports service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/sports/teams/{team_id}")
async def get_team(
    team_id: str = Path(..., description="Team ID")
):
    """Get team details by ID."""
    try:
        team = await get_team_info_api(team_id)
        return team
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except httpx.HTTPStatusError as e:
        logger.error(f"TheSportsDB API error: {e}")
        raise HTTPException(status_code=502, detail="Sports service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/sports/events/{team_id}/next")
async def get_next_events(
    team_id: str = Path(..., description="Team ID")
):
    """Get next events for a team."""
    try:
        events = await get_next_events_api(team_id)
        return {"team_id": team_id, "events": events}
    except httpx.HTTPStatusError as e:
        logger.error(f"TheSportsDB API error: {e}")
        raise HTTPException(status_code=502, detail="Sports service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/sports/events/{team_id}/last")
async def get_last_events(
    team_id: str = Path(..., description="Team ID")
):
    """Get last events for a team."""
    try:
        events = await get_last_events_api(team_id)
        return {"team_id": team_id, "events": events}
    except httpx.HTTPStatusError as e:
        logger.error(f"TheSportsDB API error: {e}")
        raise HTTPException(status_code=502, detail="Sports service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/sports/news")
async def get_sports_news(
    query: str = Query(..., description="Team, sport, or event to search news for"),
    limit: int = Query(5, le=10, ge=1)
):
    """Fetch sports news headlines."""
    try:
        headlines = await fetch_news(query, limit=limit)
        if not headlines:
            raise HTTPException(status_code=404, detail="No news found")
        return {"query": query, "headlines": headlines, "count": len(headlines)}
    except Exception as e:
        logger.error(f"Unexpected error fetching news: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/sports/olympics/events")
async def get_olympics_events(
    query: str = Query(..., description="Sport or event, e.g., '100m', 'swimming'"),
    date: Optional[str] = Query(None, description="ISO date filter (YYYY-MM-DD)")
):
    """
    Olympics events (best-effort via news headlines).
    Note: No stable free Olympics schedule API in use; returns curated headlines as stand-ins.
    """
    try:
        events = await fetch_olympics_events(query, limit=5)
        if not events:
            raise HTTPException(status_code=404, detail="No Olympics events found")
        return {"query": query, "events": events, "count": len(events)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Olympics fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch Olympics events")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Sports RAG service on port {SERVICE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
