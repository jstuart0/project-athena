# Phase 4: RAG Services Deployment Guide

**Status:** Implementation files prepared, ready to deploy when Mac Studio connectivity is restored

---

## Prerequisites

**Before deploying Phase 4:**
1. ✅ Mac Studio network connectivity restored (ping 192.168.10.167)
2. ✅ Mac Studio SSH accessible (ssh jstuart@192.168.10.167)
3. ✅ Phase 3 Gateway tested and verified
4. ⚠️ (Optional) Mac mini services deployed (Qdrant + Redis)

---

## Services Overview

Three RAG microservices have been fully implemented:

### 1. Weather RAG Service
- **Port:** 8010
- **API:** OpenWeatherMap
- **Features:**
  - Current weather by location
  - 5-day weather forecast
  - Location geocoding
  - 5-minute cache for weather data
  - 10-minute cache for forecasts

### 2. Airports RAG Service
- **Port:** 8011
- **API:** FlightAware
- **Features:**
  - Airport search by name/code
  - Airport details (ICAO/IATA codes)
  - Flight information
  - 1-hour cache for airport data
  - 5-minute cache for flight data

### 3. Sports RAG Service
- **Port:** 8012
- **API:** TheSportsDB
- **Features:**
  - Team search by name
  - Team details
  - Next 5 events for team
  - Last 5 events for team
  - 1-hour cache for teams
  - 10-minute cache for events

---

## Implementation Files

All implementation files are ready in the repository:

**Weather Service:**
- `src/rag/weather/main.py` - FastAPI service (254 lines)
- `src/rag/weather/requirements.txt` - Dependencies
- `src/rag/weather/start.sh` - Startup script
- `src/rag/weather/__init__.py` - Package init

**Airports Service:**
- `src/rag/airports/main.py` - FastAPI service (211 lines)
- `src/rag/airports/requirements.txt` - Dependencies
- `src/rag/airports/start.sh` - Startup script
- `src/rag/airports/__init__.py` - Package init

**Sports Service:**
- `src/rag/sports/main.py` - FastAPI service (222 lines)
- `src/rag/sports/requirements.txt` - Dependencies
- `src/rag/sports/start.sh` - Startup script
- `src/rag/sports/__init__.py` - Package init

---

## Deployment Steps

### Step 1: Verify Connectivity and Prerequisites

```bash
# Test Mac Studio connectivity
ping -c 3 192.168.10.167

# SSH to Mac Studio
ssh jstuart@192.168.10.167

# Verify Phase 3 gateway is running
ps aux | grep litellm

# Test gateway
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-athena-9fd1ef6c8ed1eb0278f5133095c60271" \
  -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}'
```

Expected: JSON response with model completion

### Step 2: Install Service Dependencies

```bash
# SSH to Mac Studio
ssh jstuart@192.168.10.167

# Navigate to project
cd ~/dev/project-athena

# Activate virtual environment
source .venv/bin/activate

# Install dependencies for all RAG services
pip install -r src/rag/weather/requirements.txt
pip install -r src/rag/airports/requirements.txt
pip install -r src/rag/sports/requirements.txt
```

### Step 3: Test Services Locally

**Test Weather Service:**
```bash
cd ~/dev/project-athena
source .venv/bin/activate
set -a; source config/env/.env; set +a
export WEATHER_SERVICE_PORT=8010

# Start service in foreground (for testing)
python -m src.rag.weather.main
```

In another terminal:
```bash
# Test health endpoint
curl http://localhost:8010/health

# Test current weather
curl "http://localhost:8010/weather/current?location=Los%20Angeles,%20CA"

# Test forecast
curl "http://localhost:8010/weather/forecast?location=Los%20Angeles,%20CA&days=3"
```

Press Ctrl+C to stop the service.

**Test Airports Service:**
```bash
cd ~/dev/project-athena
source .venv/bin/activate
set -a; source config/env/.env; set +a
export AIRPORTS_SERVICE_PORT=8011

# Start service in foreground
python -m src.rag.airports.main
```

In another terminal:
```bash
# Test health endpoint
curl http://localhost:8011/health

# Test airport search
curl "http://localhost:8011/airports/search?query=Los%20Angeles"

# Test airport details
curl http://localhost:8011/airports/LAX
```

Press Ctrl+C to stop the service.

**Test Sports Service:**
```bash
cd ~/dev/project-athena
source .venv/bin/activate
set -a; source config/env/.env; set +a
export SPORTS_SERVICE_PORT=8012

# Start service in foreground
python -m src.rag.sports.main
```

In another terminal:
```bash
# Test health endpoint
curl http://localhost:8012/health

# Test team search
curl "http://localhost:8012/sports/teams/search?query=Lakers"

# Test team events (use team ID from search results)
curl http://localhost:8012/sports/events/134875/next
```

Press Ctrl+C to stop the service.

### Step 4: Deploy Services as Background Processes

```bash
# SSH to Mac Studio
ssh jstuart@192.168.10.167

cd ~/dev/project-athena

# Make startup scripts executable
chmod +x src/rag/weather/start.sh
chmod +x src/rag/airports/start.sh
chmod +x src/rag/sports/start.sh

# Start Weather service
nohup bash src/rag/weather/start.sh > logs/weather.log 2>&1 &
echo "Weather service PID: $!"

# Start Airports service
nohup bash src/rag/airports/start.sh > logs/airports.log 2>&1 &
echo "Airports service PID: $!"

# Start Sports service
nohup bash src/rag/sports/start.sh > logs/sports.log 2>&1 &
echo "Sports service PID: $!"
```

### Step 5: Verify All Services Running

```bash
# Check processes
ps aux | grep "src.rag"

# Test all health endpoints
curl http://localhost:8010/health  # Weather
curl http://localhost:8011/health  # Airports
curl http://localhost:8012/health  # Sports

# Check logs for errors
tail -20 logs/weather.log
tail -20 logs/airports.log
tail -20 logs/sports.log
```

Expected: All three services responding with "healthy" status

### Step 6: Test from Remote Host

```bash
# From your local machine (not Mac Studio)

# Test Weather service
curl "http://192.168.10.167:8010/weather/current?location=Los%20Angeles,%20CA"

# Test Airports service
curl http://192.168.10.167:8011/airports/LAX

# Test Sports service
curl "http://192.168.10.167:8012/sports/teams/search?query=Lakers"
```

---

## Service Management

### View Service Status

```bash
# SSH to Mac Studio
ssh jstuart@192.168.10.167

# Check processes
ps aux | grep "src.rag.weather" | grep -v grep
ps aux | grep "src.rag.airports" | grep -v grep
ps aux | grep "src.rag.sports" | grep -v grep

# Check logs
tail -f logs/weather.log
tail -f logs/airports.log
tail -f logs/sports.log
```

### Restart a Service

```bash
# SSH to Mac Studio
ssh jstuart@192.168.10.167

# Stop service (example: weather)
pkill -f "src.rag.weather"

# Start service
cd ~/dev/project-athena
nohup bash src/rag/weather/start.sh > logs/weather.log 2>&1 &
```

### Stop All Services

```bash
# SSH to Mac Studio
ssh jstuart@192.168.10.167

# Stop all RAG services
pkill -f "src.rag.weather"
pkill -f "src.rag.airports"
pkill -f "src.rag.sports"
```

---

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
tail -50 logs/weather.log   # Or airports.log, sports.log
```

**Common issues:**
1. **Missing dependencies:** Run `pip install -r src/rag/{service}/requirements.txt`
2. **Port already in use:** Check for existing process: `lsof -i :8010` (or 8011, 8012)
3. **Environment variables missing:** Verify config/env/.env exists and has API keys
4. **Redis not accessible:** Check if Mac mini Redis is running (or skip cache if not)

### API Errors

**OpenWeatherMap (Weather service):**
- **Error: 401 Unauthorized** - Check OPENWEATHER_API_KEY in .env
- **Error: 429 Too Many Requests** - Free tier rate limit (60 calls/minute)

**FlightAware (Airports service):**
- **Error: 401 Unauthorized** - Check FLIGHTAWARE_API_KEY in .env
- **Error: 429 Too Many Requests** - Check API tier limits

**TheSportsDB (Sports service):**
- **Error: 401 Unauthorized** - Check THESPORTSDB_API_KEY in .env (use "3" for free tier)
- **No data returned** - Some teams/events may not have data in free tier

### Cache Issues

If Redis is not accessible (Mac mini SSH not enabled):

**Option 1: Mock cache (temporary):**
Edit `src/shared/cache.py` to add a NullCache class that does nothing.

**Option 2: Use local Redis:**
```bash
# Install Redis on Mac Studio
brew install redis
brew services start redis

# Update .env to use local Redis
REDIS_URL=redis://localhost:6379/0
```

**Option 3: Disable caching:**
Remove the `@cached` decorator from service functions (not recommended).

---

## Phase 4 Success Criteria

Mark Phase 4 complete when:

- [ ] All three services installed and running
- [ ] Weather: http://192.168.10.167:8010/health responds "healthy"
- [ ] Airports: http://192.168.10.167:8011/health responds "healthy"
- [ ] Sports: http://192.168.10.167:8012/health responds "healthy"
- [ ] External API integrations working:
  - [ ] Weather API returns current weather for a city
  - [ ] Airports API returns airport details for LAX
  - [ ] Sports API returns search results for a team
- [ ] Caching reduces redundant calls (check logs for cache hits)
- [ ] No errors in service logs
- [ ] Services accessible from remote hosts

---

## Next Steps

After Phase 4 is complete, proceed to **Phase 5: LangGraph Orchestrator**

The orchestrator will:
1. Receive user queries
2. Classify intent (control, weather, airport, sports, general)
3. Route to appropriate RAG service
4. Synthesize response using LLM
5. Return to user

---

## Rollback Procedure

If Phase 4 deployment fails and needs rollback:

```bash
# Stop all RAG services
pkill -f "src.rag.weather"
pkill -f "src.rag.airports"
pkill -f "src.rag.sports"

# Verify stopped
ps aux | grep "src.rag" | grep -v grep
# Should return empty

# Phase 3 (Gateway) remains running
ps aux | grep litellm
# Should still show gateway process
```

System will be back to Phase 3 completion state.

---

## Estimated Time

- **Dependency installation:** 5 minutes
- **Testing each service:** 5 minutes per service (15 minutes total)
- **Deployment:** 5 minutes
- **Verification:** 10 minutes

**Total estimated time:** 35-40 minutes

---

**Prepared:** 2025-11-11
**Status:** Ready to deploy when Mac Studio connectivity is restored
**Prerequisites:** Phase 0-3 complete, Mac Studio accessible
