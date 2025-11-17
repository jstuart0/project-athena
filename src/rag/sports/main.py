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
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse
import httpx
from contextlib import asynccontextmanager

# Import shared utilities
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.cache import CacheClient, cached
from shared.logging_config import configure_logging

# Configure logging
logger = configure_logging("sports-rag")

# Environment variables
THESPORTSDB_API_KEY = os.getenv("THESPORTSDB_API_KEY", "3")  # Free tier key
REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.10.181:6379/0")
SERVICE_PORT = int(os.getenv("SPORTS_SERVICE_PORT", "8011"))

# TheSportsDB API base URL
THESPORTSDB_BASE_URL = "https://www.thesportsdb.com/api/v1/json"

# Cache client and HTTP client
cache = None
http_client = None


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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sports-rag",
        "version": "1.0.0"
    }


@cached(ttl=3600, key_prefix="team_search")  # Cache for 1 hour
async def search_teams_api(query: str) -> List[Dict[str, Any]]:
    """
    Search for teams by name.

    Args:
        query: Team name

    Returns:
        List of matching teams
    """
    logger.info(f"Searching teams: {query}")

    url = f"{THESPORTSDB_BASE_URL}/{THESPORTSDB_API_KEY}/searchteams.php"
    params = {"t": query}

    # OPTIMIZATION: Use global HTTP client
    response = await http_client.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("teams", []) or []


@cached(ttl=3600, key_prefix="team_info")  # Cache for 1 hour
async def get_team_info_api(team_id: str) -> Dict[str, Any]:
    """
    Get detailed team information.

    Args:
        team_id: Team ID

    Returns:
        Team details
    """
    logger.info(f"Fetching team info: {team_id}")

    url = f"{THESPORTSDB_BASE_URL}/{THESPORTSDB_API_KEY}/lookupteam.php"
    params = {"id": team_id}

    # OPTIMIZATION: Use global HTTP client
    response = await http_client.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    teams = data.get("teams", [])
    if not teams:
        raise ValueError(f"Team not found: {team_id}")
    return teams[0]


@cached(ttl=600, key_prefix="next_events")  # Cache for 10 minutes
async def get_next_events_api(team_id: str) -> List[Dict[str, Any]]:
    """
    Get next 5 events for a team.

    Args:
        team_id: Team ID

    Returns:
        List of upcoming events
    """
    logger.info(f"Fetching next events for team: {team_id}")

    url = f"{THESPORTSDB_BASE_URL}/{THESPORTSDB_API_KEY}/eventsnext.php"
    params = {"id": team_id}

    # OPTIMIZATION: Use global HTTP client
    response = await http_client.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("events", []) or []


@cached(ttl=600, key_prefix="last_events")  # Cache for 10 minutes
async def get_last_events_api(team_id: str) -> List[Dict[str, Any]]:
    """
    Get last 5 events for a team.

    Args:
        team_id: Team ID

    Returns:
        List of past events
    """
    logger.info(f"Fetching last events for team: {team_id}")

    url = f"{THESPORTSDB_BASE_URL}/{THESPORTSDB_API_KEY}/eventslast.php"
    params = {"id": team_id}

    # OPTIMIZATION: Use global HTTP client
    response = await http_client.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("results", []) or []


@app.get("/sports/teams/search")
async def search_teams(
    query: str = Query(..., description="Team name to search")
):
    """Search for teams by name."""
    try:
        teams = await search_teams_api(query)
        return {"query": query, "teams": teams}
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


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Sports RAG service on port {SERVICE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
