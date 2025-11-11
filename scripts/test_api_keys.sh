#!/bin/bash
#
# Project Athena - API Key Testing Script
#
# This script tests all configured API keys to ensure they're valid
# and working correctly before you start using them in production.
#
# Usage:
#   bash scripts/test_api_keys.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
}

print_data() {
    echo -e "       ${GREEN}→${NC} $1"
}

# Check if .env file exists
if [ ! -f "config/env/.env" ]; then
    echo -e "${RED}❌ Error: config/env/.env not found${NC}"
    echo ""
    echo "Please create the .env file first:"
    echo "  cp config/env/.env.template config/env/.env"
    echo "  nano config/env/.env  # Edit with your actual keys"
    exit 1
fi

# Load environment variables
source config/env/.env

print_header "Project Athena - API Key Testing"

# =============================================================================
# OpenWeatherMap (Weather)
# =============================================================================
print_header "1. OpenWeatherMap (Weather)"

print_test "Testing OpenWeatherMap API..."

if [ -z "$OPENWEATHER_API_KEY" ] || [ "$OPENWEATHER_API_KEY" == "get_this_today" ]; then
    print_skip "OpenWeatherMap API key not configured"
    echo ""
    echo "Get your key from: https://openweathermap.org/api"
    echo "Add to .env: OPENWEATHER_API_KEY=your_key_here"
else
    WEATHER_RESPONSE=$(curl -sf "https://api.openweathermap.org/data/2.5/weather?q=Baltimore&appid=${OPENWEATHER_API_KEY}&units=imperial")

    if [ $? -eq 0 ]; then
        TEMP=$(echo $WEATHER_RESPONSE | jq -r '.main.temp' 2>/dev/null)
        FEELS_LIKE=$(echo $WEATHER_RESPONSE | jq -r '.main.feels_like' 2>/dev/null)
        DESCRIPTION=$(echo $WEATHER_RESPONSE | jq -r '.weather[0].description' 2>/dev/null)
        CITY=$(echo $WEATHER_RESPONSE | jq -r '.name' 2>/dev/null)

        if [ ! -z "$TEMP" ] && [ "$TEMP" != "null" ]; then
            print_pass "OpenWeatherMap API is working!"
            print_data "City: ${CITY}"
            print_data "Temperature: ${TEMP}°F (feels like ${FEELS_LIKE}°F)"
            print_data "Conditions: ${DESCRIPTION}"
        else
            print_fail "Got response but couldn't parse weather data"
            echo "$WEATHER_RESPONSE" | jq '.' 2>/dev/null || echo "$WEATHER_RESPONSE"
        fi
    else
        print_fail "OpenWeatherMap API request failed"
        echo ""
        echo "Possible issues:"
        echo "  - Invalid API key"
        echo "  - API key not activated yet (can take a few minutes)"
        echo "  - Network connectivity issue"
    fi
fi

# =============================================================================
# FlightAware (Airports/Flights)
# =============================================================================
print_header "2. FlightAware (Airports)"

print_test "Testing FlightAware API..."

if [ -z "$FLIGHTAWARE_API_KEY" ] || [ "$FLIGHTAWARE_API_KEY" == "get_this_week" ]; then
    print_skip "FlightAware API key not configured"
    echo ""
    echo "Get your key from: https://www.flightaware.com/commercial/flightxml/"
    echo "Add to .env: FLIGHTAWARE_API_KEY=your_key_here"
else
    AIRPORT_RESPONSE=$(curl -sf "https://aeroapi.flightaware.com/aeroapi/airports/KBWI" \
        -H "x-apikey: ${FLIGHTAWARE_API_KEY}")

    if [ $? -eq 0 ]; then
        AIRPORT_CODE=$(echo $AIRPORT_RESPONSE | jq -r '.airport_code' 2>/dev/null)
        AIRPORT_NAME=$(echo $AIRPORT_RESPONSE | jq -r '.name' 2>/dev/null)
        AIRPORT_CITY=$(echo $AIRPORT_RESPONSE | jq -r '.city' 2>/dev/null)

        if [ ! -z "$AIRPORT_CODE" ] && [ "$AIRPORT_CODE" != "null" ]; then
            print_pass "FlightAware API is working!"
            print_data "Airport: ${AIRPORT_CODE}"
            print_data "Name: ${AIRPORT_NAME}"
            print_data "City: ${AIRPORT_CITY}"
        else
            print_fail "Got response but couldn't parse airport data"
            echo "$AIRPORT_RESPONSE" | jq '.' 2>/dev/null || echo "$AIRPORT_RESPONSE"
        fi
    else
        print_fail "FlightAware API request failed"
        echo ""
        echo "Possible issues:"
        echo "  - Invalid API key"
        echo "  - API key not activated yet (can take 1-2 hours)"
        echo "  - Free tier quota exceeded (100/month)"
    fi
fi

# =============================================================================
# TheSportsDB (Sports)
# =============================================================================
print_header "3. TheSportsDB (Sports)"

print_test "Testing TheSportsDB API..."

if [ -z "$THESPORTSDB_API_KEY" ]; then
    print_skip "TheSportsDB API key not configured"
    echo ""
    echo "Options:"
    echo "  Free tier: Use key '1' (limited)"
    echo "  Patreon: Get personal key for \$2/month"
    echo "Add to .env: THESPORTSDB_API_KEY=1  # or your patreon key"
else
    SPORTS_RESPONSE=$(curl -sf "https://www.thesportsdb.com/api/v1/json/${THESPORTSDB_API_KEY}/searchteams.php?t=Baltimore_Ravens")

    if [ $? -eq 0 ]; then
        TEAM_NAME=$(echo $SPORTS_RESPONSE | jq -r '.teams[0].strTeam' 2>/dev/null)
        LEAGUE=$(echo $SPORTS_RESPONSE | jq -r '.teams[0].strLeague' 2>/dev/null)
        STADIUM=$(echo $SPORTS_RESPONSE | jq -r '.teams[0].strStadium' 2>/dev/null)

        if [ ! -z "$TEAM_NAME" ] && [ "$TEAM_NAME" != "null" ]; then
            print_pass "TheSportsDB API is working!"
            print_data "Team: ${TEAM_NAME}"
            print_data "League: ${LEAGUE}"
            print_data "Stadium: ${STADIUM}"
        else
            print_fail "Got response but couldn't parse team data"
            echo "$SPORTS_RESPONSE" | jq '.' 2>/dev/null || echo "$SPORTS_RESPONSE"
        fi
    else
        print_fail "TheSportsDB API request failed"
        echo ""
        echo "Possible issues:"
        echo "  - Using free key '1' with rate limiting"
        echo "  - Network connectivity issue"
        echo "  - Consider upgrading to Patreon key (\$2/month)"
    fi
fi

# =============================================================================
# Phase 2 API Keys (Future)
# =============================================================================
print_header "4. Phase 2 Keys (Not Required Yet)"

# NewsAPI
if [ ! -z "$NEWSAPI_KEY" ] && [ "$NEWSAPI_KEY" != "defer_to_phase2" ]; then
    print_test "NewsAPI key configured (Phase 2)"
else
    print_skip "NewsAPI - Not needed for Phase 1"
fi

# Spoonacular
if [ ! -z "$SPOONACULAR_API_KEY" ] && [ "$SPOONACULAR_API_KEY" != "defer_to_phase2" ]; then
    print_test "Spoonacular key configured (Phase 2)"
else
    print_skip "Spoonacular - Not needed for Phase 1"
fi

# TMDB
if [ ! -z "$TMDB_API_KEY" ] && [ "$TMDB_API_KEY" != "defer_to_phase2" ]; then
    print_test "TMDB key configured (Phase 2)"
else
    print_skip "TMDB - Not needed for Phase 1"
fi

# Yelp
if [ ! -z "$YELP_API_KEY" ] && [ "$YELP_API_KEY" != "defer_to_phase2" ]; then
    print_test "Yelp key configured (Phase 2)"
else
    print_skip "Yelp - Not needed for Phase 1"
fi

# =============================================================================
# Summary
# =============================================================================
print_header "Testing Complete"

echo "Phase 1 API keys status:"
echo ""

if [ ! -z "$OPENWEATHER_API_KEY" ] && [ "$OPENWEATHER_API_KEY" != "get_this_today" ]; then
    echo -e "  ✅ OpenWeatherMap - Configured and tested"
else
    echo -e "  ⏳ OpenWeatherMap - Not configured (GET THIS TODAY)"
fi

if [ ! -z "$FLIGHTAWARE_API_KEY" ] && [ "$FLIGHTAWARE_API_KEY" != "get_this_week" ]; then
    echo -e "  ✅ FlightAware - Configured and tested"
else
    echo -e "  ⏳ FlightAware - Not configured (get this week)"
fi

if [ ! -z "$THESPORTSDB_API_KEY" ]; then
    echo -e "  ✅ TheSportsDB - Configured and tested"
else
    echo -e "  ⏳ TheSportsDB - Not configured (get this week)"
fi

echo ""
echo "For detailed instructions, see: docs/API_KEY_GUIDE.md"
