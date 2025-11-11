# Project Athena - Repository Migration

**Date:** 2025-11-11
**Migration Type:** Architecture Pivot (Jetson → Mac Studio/mini)

---

## Overview

This repository has been restructured to support the new Mac Studio/mini implementation while preserving all the valuable Jetson research and development work.

## Branch Structure

### `main` Branch (NEW Implementation)

**Purpose:** Current development for Mac Studio/mini architecture

**Contents:**
- `START_HERE.md` - Entry point for new implementation
- `apps/` - New microservices architecture (gateway, orchestrator, RAG services)
- `config/` - Configuration templates and network settings
- `deployment/` - docker-compose for Mac mini services (Qdrant, Redis)
- `docs/` - Day 1 Quick Start, API guides, integration docs
- `scripts/` - Verification, testing, and initialization scripts
- `thoughts/shared/` - Implementation plans and research (Nov 2025)

**Timeline:** 4-6 weeks to complete Phase 1

### `archive/jetson-implementation` Branch (OLD Implementation)

**Purpose:** Preserved Jetson-based research and code

**Contents:**
- `src/jetson/facade/` - Facade pattern implementation with:
  - 43 versions of airbnb_intent_classifier (v1-v43)
  - RAG handlers: weather, airports, flights, events, streaming, news, stocks, sports, web_search
  - Intent processor, query splitter, response merger
- `tests/facade/` - Comprehensive test suite with 1000+ query benchmarks
- `analysis/` - Intent classification analysis documents
- `brightness-analysis/` - Brightness formula research
- `athena-lite/` - Proof-of-concept documentation (code on Jetson device)
- `thoughts/shared/` - January 2025 research and plans
- Integration status documents and marathon session results

**Historical Value:**
- 104,249 lines of code representing months of iteration
- Patterns and lessons learned for migration
- Benchmark data and performance analysis
- Complete RAG handler implementations

---

## How to Use Both Branches

### Working on New Implementation (main)

```bash
# Ensure you're on main
git checkout main

# Pull latest changes
git pull origin main

# Start Day 1
open START_HERE.md
open docs/DAY_1_QUICK_START.md

# Begin implementation
bash scripts/verify_day1.sh
```

### Referencing Old Jetson Code (archive)

```bash
# View old implementation
git checkout archive/jetson-implementation

# Explore code
ls -la src/jetson/facade/handlers/

# Read a specific handler
cat src/jetson/facade/handlers/weather.py

# View test results
cat tests/facade/v22_benchmark_output.txt

# Return to main
git checkout main
```

### Comparing Old and New

```bash
# From main branch, view archived code without switching branches
git show archive/jetson-implementation:src/jetson/facade/handlers/weather.py

# Compare directory structures
git diff --name-status main archive/jetson-implementation

# View archived commit history
git log archive/jetson-implementation
```

---

## Migration Strategy

### Phase 1.3-1.4: RAG Handler Migration (Week 3-4)

For each RAG handler (weather, airports, sports):

1. **Reference old implementation:**
   ```bash
   git show archive/jetson-implementation:src/jetson/facade/handlers/weather.py > /tmp/old_weather.py
   ```

2. **Extract patterns:**
   - API endpoint configuration
   - Request/response models
   - Caching strategy
   - Error handling
   - Data transformation logic

3. **Adapt to new structure:**
   ```
   apps/rag/weather/
   ├── main.py          # FastAPI entrypoint (new)
   ├── handler.py       # Core logic (migrated from old handler)
   ├── models.py        # Pydantic models (new)
   ├── config.py        # API config (migrated from facade/config/)
   └── Dockerfile       # Container definition (new)
   ```

4. **Add new features:**
   - Async/await support
   - Health check endpoints
   - Prometheus metrics
   - Structured logging

5. **Test:**
   ```bash
   pytest apps/rag/weather/tests/
   ```

### Example: Weather Handler Migration

**Old (Jetson):**
```python
# src/jetson/facade/handlers/weather.py
def handle_weather_query(query: str) -> str:
    # Synchronous implementation
    api_key = get_api_key()
    response = requests.get(f"https://api.openweathermap.org/...")
    return format_response(response.json())
```

**New (Mac Studio):**
```python
# apps/rag/weather/handler.py
async def handle_weather_query(query: str) -> WeatherResponse:
    # Async implementation with health checks and metrics
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openweathermap.org/...",
            headers={"X-Request-ID": generate_request_id()}
        )
        metrics.weather_api_calls.inc()
        return WeatherResponse.parse_obj(response.json())
```

---

## What Was Preserved

### ✅ Fully Preserved (archive branch)

- **All 43 intent classifier iterations** - Evolution from v1 to v43
- **All RAG handlers** - Complete implementations with API integrations
- **Test suites** - 1000+ query benchmarks and results
- **Analysis documents** - Research findings and performance data
- **Integration status** - Marathon session results and progress tracking

### ✅ Carried Forward (main branch)

- **November 2025 plans** - Phase 1-3 implementation specifications
- **Architecture pivot research** - Rationale for Mac Studio/mini
- **Athena Lite status** - Proof-of-concept documentation
- **Configuration templates** - Network, zones, models
- **Documentation** - CLAUDE.md, README.md, thoughts/README.md

### ❌ Not Preserved (old/obsolete)

- **January 2025 plans** - Superseded by November architecture pivot
- **Brightness analysis** - One-off research not relevant to new implementation
- **Integration summary** - Status documents from old implementation
- **Marathon results** - Historical data for archive only

---

## Directory Comparison

### Old Structure (archive/jetson-implementation)

```
project-athena/
├── src/jetson/                    # Jetson-specific code
│   ├── athena_lite.py             # Proof-of-concept
│   ├── facade/                    # Facade pattern implementation
│   │   ├── airbnb_intent_classifier*.py  # 43 versions
│   │   ├── handlers/              # RAG handlers (9 total)
│   │   ├── config/                # API configurations
│   │   └── utils/                 # Cache and utilities
│   ├── ha_client.py               # Home Assistant client
│   ├── ollama_proxy.py            # Ollama proxy service
│   └── systemd/                   # Service definitions
├── tests/facade/                  # Comprehensive test suite
└── analysis/                      # Research documents
```

### New Structure (main)

```
project-athena/
├── apps/                          # Microservices architecture
│   ├── gateway/                   # LiteLLM OpenAI gateway
│   ├── orchestrator/              # LangGraph state machine
│   ├── rag/                       # RAG microservices
│   │   ├── weather/               # OpenWeatherMap
│   │   ├── airports/              # FlightAware
│   │   └── sports/                # TheSportsDB
│   ├── shared/                    # Common utilities
│   ├── validators/                # Anti-hallucination
│   └── share-service/             # SMS/Email (Phase 2)
├── deployment/                    # docker-compose configs
├── scripts/                       # Automation scripts
└── docs/                          # Implementation guides
```

---

## Key Differences

### Architecture

| Aspect | Old (Jetson) | New (Mac Studio/mini) |
|--------|-------------|----------------------|
| **Compute** | Single Jetson Orin Nano | Mac Studio M4 + Mac mini M4 |
| **Models** | Jetson-optimized | Ollama with Metal acceleration |
| **Structure** | Monolithic facade | Microservices |
| **Orchestration** | Single-file processor | LangGraph state machine |
| **API Gateway** | Custom proxy | LiteLLM (OpenAI-compatible) |
| **Deployment** | systemd services | Docker Compose → Kubernetes |

### Development Workflow

| Aspect | Old (Jetson) | New (Mac Studio/mini) |
|--------|-------------|----------------------|
| **Language** | Python (sync) | Python (async) |
| **Testing** | Manual + pytest | Automated CI/CD |
| **Deployment** | SSH + rsync | Docker + git |
| **Monitoring** | Basic logging | Prometheus + Grafana |
| **Documentation** | Inline comments | Comprehensive docs + plans |

---

## FAQ

### Can I still access the old Jetson code?

**Yes!** All code is preserved in the `archive/jetson-implementation` branch:
```bash
git checkout archive/jetson-implementation
```

### Will the Jetson code be deleted?

**No!** The archive branch is permanent and will remain in the repository. You can always reference it or extract code from it.

### What about Athena Lite on the Jetson device?

Athena Lite code remains on the Jetson device at `/mnt/nvme/athena-lite/`. The `athena-lite/` directory in this repo only contains documentation about what's on the Jetson.

### How do I migrate a specific handler?

See the "Migration Strategy" section above. Use:
```bash
git show archive/jetson-implementation:src/jetson/facade/handlers/YOUR_HANDLER.py
```

### Should I ever commit to the archive branch?

**No.** The archive branch is read-only. All new development happens on `main`. If you find a bug in archived code, note it in `main` but don't modify the archive.

### What if I need to reference old test data?

Test results and benchmarks are in the archive branch:
```bash
git show archive/jetson-implementation:tests/facade/v22_benchmark_output.txt
```

### How do I know which code is current?

- **Current:** Anything in `main` branch, especially `apps/` directory
- **Archived:** Anything in `archive/jetson-implementation` branch

---

## Quick Reference Commands

```bash
# View current branch
git branch

# List all branches
git branch -a

# View archived file without switching branches
git show archive/jetson-implementation:path/to/file

# Compare branches
git diff main archive/jetson-implementation

# View archive commit history
git log archive/jetson-implementation --oneline

# Search archived code
git grep "search_term" archive/jetson-implementation

# Extract file from archive to temp location
git show archive/jetson-implementation:src/jetson/facade/handlers/weather.py > /tmp/old_weather.py

# Return to main branch
git checkout main
```

---

## Related Documentation

**New Implementation:**
- `START_HERE.md` - Entry point
- `docs/DAY_1_QUICK_START.md` - Immediate next steps
- `thoughts/shared/plans/2025-11-11-phase1-core-services-implementation.md` - Detailed plan
- `apps/README.md` - Application architecture

**Migration Guides:**
- Component Deep-Dive: `thoughts/shared/plans/2025-11-11-component-deep-dive-plans.md`
- Full Bootstrap: `thoughts/shared/plans/2025-11-11-full-bootstrap-implementation.md`

**Architecture:**
- Architecture Pivot: `thoughts/shared/research/2025-11-11-complete-architecture-pivot.md`
- Athena Lite Status: `thoughts/shared/research/2025-11-09-athena-lite-complete-status.md`

---

**Migration Completed:** 2025-11-11
**Commits:**
- Archive branch: `b443fa3` (145 files, 104,249 insertions)
- New implementation: `cfe35e9` (42 files, 29,075 insertions)
- Apps structure: `72e7d0f` (9 files, 363 insertions)
