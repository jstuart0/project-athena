# Project Athena - Scripts Directory

Automation and utility scripts for Project Athena setup and management.

## Day 1 Setup Scripts

### `verify_day1.sh`

**Purpose:** Comprehensive verification of all Day 1 prerequisites

**Usage:**
```bash
bash scripts/verify_day1.sh
```

**Checks:**
- Network connectivity (Mac Studio, Mac mini, Home Assistant)
- Local environment (Homebrew, Docker, Python, Ollama)
- Ollama models (phi3:mini-q8, llama3.1:8b-q4)
- Mac mini services (Qdrant, Redis)
- Configuration files (.env)
- API keys (Phase 1)

**Exit codes:**
- `0` - All checks passed
- `1` - Some checks failed (review output)

**Example output:**
```
[PASS] Mac mini is reachable at 192.168.10.181
[PASS] Ollama installed: ollama version 0.1.14
[FAIL] Small model not found: phi3:mini-q8
[WARN] OpenWeatherMap API key not configured
```

---

### `test_api_keys.sh`

**Purpose:** Test all configured API keys to ensure they're working

**Usage:**
```bash
bash scripts/test_api_keys.sh
```

**Tests:**
- OpenWeatherMap (weather query for Baltimore)
- FlightAware (airport info for BWI)
- TheSportsDB (team info for Baltimore Ravens)
- Phase 2 keys (skipped if not configured)

**Requirements:**
- `.env` file must exist with API keys
- `jq` installed for JSON parsing: `brew install jq`

**Example output:**
```
[PASS] OpenWeatherMap API is working!
       → City: Baltimore
       → Temperature: 72.5°F (feels like 71.2°F)
       → Conditions: clear sky

[SKIP] FlightAware API key not configured
```

---

### `init_qdrant.py`

**Purpose:** Initialize Qdrant vector database with athena_knowledge collection

**Usage:**
```bash
# From Mac Studio (after Mac mini services are running)
python3 scripts/init_qdrant.py
```

**Requirements:**
- Python 3.x
- `qdrant-client` library: `pip install qdrant-client`
- Qdrant running at http://192.168.10.181:6333

**What it does:**
1. Connects to Qdrant
2. Creates `athena_knowledge` collection (384 dimensions, cosine similarity)
3. Inserts test point to verify functionality
4. Tests search capability
5. Cleans up test point

**Configuration:**
- Collection: `athena_knowledge`
- Vector size: 384 (all-MiniLM-L6-v2)
- Distance: Cosine similarity
- URL: Set via `QDRANT_URL` env var or defaults to `http://192.168.10.181:6333`

---

## Workflow: Day 1 Setup

Follow this workflow to set up Project Athena on Day 1:

**1. Environment Setup**
```bash
# Install prerequisites
brew install homebrew docker python@3.11 ollama jq

# Start Docker
open /Applications/Docker.app

# Start Ollama and pull models
ollama serve &
ollama pull phi3:mini-q8
ollama pull llama3.1:8b-q4
```

**2. Configuration**
```bash
# Create .env from template
cp config/env/.env.template config/env/.env

# Edit with your actual values
nano config/env/.env
```

**3. Deploy Mac mini Services**
```bash
# Copy docker-compose to Mac mini
scp deployment/mac-mini/docker-compose.yml user@192.168.10.181:~/athena/mac-mini/

# SSH to Mac mini and deploy
ssh user@192.168.10.181
cd ~/athena/mac-mini
docker compose up -d
```

**4. Initialize Qdrant**
```bash
# From Mac Studio
python3 scripts/init_qdrant.py
```

**5. Verify Everything**
```bash
# Run comprehensive verification
bash scripts/verify_day1.sh

# Test API keys
bash scripts/test_api_keys.sh
```

---

## Troubleshooting

### Permission Denied

```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py
```

### Python Module Not Found

```bash
# Install required packages
pip install qdrant-client

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install qdrant-client
```

### Cannot Connect to Qdrant

```bash
# Verify Qdrant is running on Mac mini
curl http://192.168.10.181:6333/healthz

# If not running, deploy services
cd deployment/mac-mini
docker compose up -d

# Check logs
docker logs qdrant
```

### API Key Tests Failing

```bash
# Verify .env file exists and has correct keys
cat config/env/.env | grep API_KEY

# Test individual API manually
curl "https://api.openweathermap.org/data/2.5/weather?q=Baltimore&appid=YOUR_KEY&units=imperial"
```

---

## Script Dependencies

**All scripts:**
- bash 4.0+
- curl
- Network connectivity

**verify_day1.sh:**
- docker (optional, checks if installed)
- ollama (optional, checks if installed)
- redis-cli (optional, for Redis check)

**test_api_keys.sh:**
- jq (JSON parser): `brew install jq`
- config/env/.env file with API keys

**init_qdrant.py:**
- Python 3.x
- qdrant-client: `pip install qdrant-client`
- Qdrant service running

---

## Adding New Scripts

When adding new scripts to this directory:

1. **Name clearly:** Use descriptive names (e.g., `verify_phase2.sh`, `migrate_rag_handlers.py`)
2. **Make executable:** `chmod +x scripts/your_script.sh`
3. **Add header comments:** Document purpose, usage, requirements
4. **Update this README:** Add entry with description and usage
5. **Use consistent output:** Follow existing color/format conventions

---

## Related Documentation

- **Day 1 Quick Start:** `/docs/DAY_1_QUICK_START.md`
- **API Key Guide:** `/docs/API_KEY_GUIDE.md`
- **Phase 1 Implementation Plan:** `/thoughts/shared/plans/2025-11-11-phase1-core-services-implementation.md`
- **Full Bootstrap Guide:** `/thoughts/shared/plans/2025-11-11-full-bootstrap-implementation.md`
