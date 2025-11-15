"""
Weather RAG Service - OpenWeatherMap Integration

Provides weather data retrieval with caching and geocoding support.

Endpoints:
- GET /health - Health check
- GET /weather/current?location={location} - Current weather
- GET /weather/forecast?location={location}&days={days} - Weather forecast
"""

import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
from contextlib import asynccontextmanager

# Import shared utilities (adjust path as needed when deployed)
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.cache import CacheClient, cached
from shared.logging_config import configure_logging

# Configure logging
logger = configure_logging("weather-rag")

# Environment variables
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.10.181:6379/0")
SERVICE_PORT = int(os.getenv("WEATHER_SERVICE_PORT", "8010"))

# Cache client and HTTP client
cache = None
http_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global cache, http_client

    # Startup
    logger.info("Starting Weather RAG service")
    cache = CacheClient(url=REDIS_URL)
    await cache.connect()

    # OPTIMIZATION: Create reusable HTTP client
    http_client = httpx.AsyncClient(timeout=10.0)
    logger.info("HTTP client initialized")

    yield

    # Shutdown
    logger.info("Shutting down Weather RAG service")
    if http_client:
        await http_client.aclose()
    if cache:
        await cache.disconnect()


app = FastAPI(
    title="Weather RAG Service",
    description="OpenWeatherMap integration with caching",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "weather-rag",
        "version": "1.0.0"
    }


@cached(ttl=600, key_prefix="geocode")  # Cache for 10 minutes
async def geocode_location(location: str) -> Dict[str, Any]:
    """
    Geocode location name to lat/lon coordinates.

    Args:
        location: City name (e.g., "Los Angeles", "New York, NY")

    Returns:
        Dict with lat, lon, name, country
    """
    logger.info(f"Geocoding location: {location}")

    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": location,
        "limit": 1,
        "appid": OPENWEATHER_API_KEY
    }

    # OPTIMIZATION: Use global HTTP client
    response = await http_client.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if not data:
        raise ValueError(f"Location not found: {location}")

    result = data[0]
    return {
        "lat": result["lat"],
        "lon": result["lon"],
        "name": result["name"],
        "country": result.get("country", "")
    }


@cached(ttl=300, key_prefix="weather")  # Cache for 5 minutes
async def get_current_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get current weather for coordinates.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Current weather data
    """
    logger.info(f"Fetching current weather for lat={lat}, lon={lon}")

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "imperial"  # Fahrenheit
    }

    # OPTIMIZATION: Use global HTTP client
    response = await http_client.get(url, params=params)
    response.raise_for_status()
    return response.json()


@cached(ttl=600, key_prefix="forecast")  # Cache for 10 minutes
async def get_weather_forecast(lat: float, lon: float, days: int = 5) -> Dict[str, Any]:
    """
    Get weather forecast for coordinates.

    Args:
        lat: Latitude
        lon: Longitude
        days: Number of days (max 5 for free tier)

    Returns:
        Forecast data
    """
    logger.info(f"Fetching {days}-day forecast for lat={lat}, lon={lon}")

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "imperial",  # Fahrenheit
        "cnt": days * 8  # 8 data points per day (every 3 hours)
    }

    # OPTIMIZATION: Use global HTTP client
    response = await http_client.get(url, params=params)
    response.raise_for_status()
    return response.json()


@app.get("/weather/current")
async def current_weather(
    location: str = Query(..., description="City name (e.g., 'Los Angeles, CA')")
):
    """Get current weather for a location."""
    try:
        # Geocode location
        coords = await geocode_location(location)

        # Get weather
        weather = await get_current_weather(coords["lat"], coords["lon"])

        # Format response
        return {
            "location": {
                "name": coords["name"],
                "country": coords["country"],
                "lat": coords["lat"],
                "lon": coords["lon"]
            },
            "current": {
                "temperature": weather["main"]["temp"],
                "feels_like": weather["main"]["feels_like"],
                "humidity": weather["main"]["humidity"],
                "description": weather["weather"][0]["description"],
                "wind_speed": weather["wind"]["speed"]
            },
            "timestamp": weather["dt"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenWeatherMap API error: {e}")
        raise HTTPException(status_code=502, detail="Weather service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/weather/forecast")
async def weather_forecast(
    location: str = Query(..., description="City name (e.g., 'Los Angeles, CA')"),
    days: int = Query(5, ge=1, le=5, description="Number of days (1-5)")
):
    """Get weather forecast for a location."""
    try:
        # Geocode location
        coords = await geocode_location(location)

        # Get forecast
        forecast = await get_weather_forecast(coords["lat"], coords["lon"], days)

        # Format response
        return {
            "location": {
                "name": coords["name"],
                "country": coords["country"],
                "lat": coords["lat"],
                "lon": coords["lon"]
            },
            "forecast": [
                {
                    "timestamp": item["dt"],
                    "temperature": item["main"]["temp"],
                    "description": item["weather"][0]["description"],
                    "humidity": item["main"]["humidity"],
                    "wind_speed": item["wind"]["speed"]
                }
                for item in forecast["list"]
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenWeatherMap API error: {e}")
        raise HTTPException(status_code=502, detail="Weather service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Weather RAG service on port {SERVICE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
