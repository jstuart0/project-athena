# Phase 2: Complete Feature Implementation Plan

**Date:** 2025-01-13
**Status:** Planning
**Phase:** 2 of 4
**Dependencies:** Phase 1 must be 100% complete (Gateway, Orchestrator, 3 base RAG services, HA integration)
**Related:**
- [Phase 1 Core Services](2025-11-11-phase1-core-services-implementation.md)
- [Guest Mode Specification](2025-11-11-guest-mode-and-quality-tracking.md)
- [Admin Interface Specification](2025-11-11-admin-interface-specification.md)
- [Admin Integration Principle](../decisions/2025-01-13-admin-app-as-configuration-interface.md)
- [Open Source Release Target](../decisions/2025-01-13-open-source-release-target.md)

---

## Executive Summary

Phase 2 transforms Project Athena from a functional voice assistant into a **production-ready, feature-complete system** with:
- **Clean git branching strategy** - Phase 2 developed in dedicated feature branch
- **7 additional RAG services** (News, Events, Stocks, Recipes, Dining, Streaming, Flights)
- **Full guest mode** with Airbnb calendar integration and permission scoping
- **Quality tracking and feedback** system for continuous improvement
- **Performance optimization** targeting ≤4.0s response times
- **Admin UI integration** for all features
- **Open source readiness** with comprehensive documentation

**Timeline:** 8-10 weeks (after Phase 1 complete)
**Team Size:** 1-2 developers
**Complexity:** High (multi-service coordination, calendar integration, real-time metrics)

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Desired End State](#2-desired-end-state)
3. [What We're NOT Doing](#3-what-were-not-doing)
4. [Architecture Principles](#4-architecture-principles)
5. [Phase 2.0: Branch Setup and Preparation](#phase-20-branch-setup-and-preparation)
6. [Phase 2.1: Additional RAG Services](#phase-21-additional-rag-services-7-services)
7. [Phase 2.2: Guest Mode Implementation](#phase-22-guest-mode-implementation)
8. [Phase 2.3: Quality Tracking & Feedback](#phase-23-quality-tracking--feedback)
9. [Phase 2.4: Performance Optimization](#phase-24-performance-optimization)
10. [Phase 2.5: Admin Interface Extensions](#phase-25-admin-interface-extensions)
11. [Testing Strategy](#testing-strategy)
12. [Open Source Readiness](#open-source-readiness)
13. [Migration Notes](#migration-notes)
14. [References](#references)

---

## 1. Current State Analysis

### What Exists (From Phase 1)

**✅ Complete Infrastructure:**
- Mac Studio M4/64GB (192.168.10.167) - AI processing
- Mac mini M4/16GB (192.168.10.181) - Data layer (Qdrant + Redis)
- Home Assistant integration configured
- Kubernetes cluster (thor) for admin app

**✅ Complete Services:**
- Gateway service (LiteLLM) - Port 8000
- Orchestrator service (LangGraph) - Port 8001
- Weather RAG service - Port 8010
- Airports RAG service - Port 8011
- Sports RAG service - Port 8012
- Piper TTS - Port 10200
- Whisper STT - Port 10300
- Ollama (phi3:mini-q8, llama3.1:8b-q4) - Port 11434

**✅ Complete Admin Infrastructure:**
- Admin backend API (FastAPI + PostgreSQL + OIDC)
- Admin frontend UI (vanilla JS + TailwindCSS)
- Kubernetes deployment on thor cluster
- Authentik SSO integration
- Audit logging system
- User management

**✅ Complete Shared Utilities:**
- `src/shared/cache.py` - Redis caching with @cached decorator
- `src/shared/ha_client.py` - Async Home Assistant client
- `src/shared/ollama_client.py` - Async Ollama client
- `src/shared/logging_config.py` - Structured logging

### What's Missing (Phase 2 Scope)

**❌ Additional RAG Services:**
- News (NewsAPI)
- Events (Eventbrite/Ticketmaster)
- Stocks (Alpha Vantage)
- Recipes (Spoonacular)
- Dining (Yelp/Google Places)
- Streaming (TMDB/JustWatch)
- Flights (FlightAware - flight tracking)

**❌ Guest Mode:**
- Airbnb calendar integration (iCal polling)
- Mode detection service
- Permission scoping system
- PII scrubbing
- Auto-purge on checkout
- Voice PIN override

**❌ Quality Tracking:**
- Request/response logging
- Feedback collection ("that answer was wrong")
- Prometheus metrics export
- Quality analytics dashboard
- Nightly improvement analysis

**❌ Performance Optimization:**
- Cache tuning (optimal TTLs)
- Latency profiling
- Model quantization optimization
- Response time ≤4.0s target

**❌ Admin UI Extensions:**
- RAG service management UI
- Guest mode configuration UI
- Quality tracking dashboard
- Performance metrics dashboard
- Airbnb calendar setup UI

---

## 2. Desired End State

### Success Criteria Overview

**When Phase 2 is complete:**

1. **10 RAG services operational** (Weather, Airports, Sports, News, Events, Stocks, Recipes, Dining, Streaming, Flights)
2. **Guest mode fully functional** with automatic calendar-based activation
3. **Quality metrics tracked** with feedback loops and analytics
4. **Performance target met** (≤4.0s for knowledge queries)
5. **All features configurable** via admin UI
6. **Documentation complete** for open source release
7. **Test coverage ≥90%** for all new components

### User Experience Goals

**For homeowners:**
- "Jarvis, what's in the news today?" → News service responds in ≤4s
- "Athena, suggest a recipe for dinner" → Recipe service provides ideas
- "What movies are streaming tonight?" → Streaming service recommends content

**For Airbnb hosts:**
- Calendar synced automatically every 10 minutes
- Guest mode activates 2 hours before check-in
- Restricted access to owner-only devices
- All guest data purged automatically after checkout

**For admins:**
- Enable/disable RAG services via UI toggle
- Configure guest mode restrictions via web form
- View quality metrics dashboard with charts
- Review recent interactions and feedback

### System Performance Goals

- **Response time:** ≤4.0s for knowledge queries (down from 5.5s)
- **Cache hit rate:** ≥85% for frequently asked questions
- **Uptime:** ≥99.5% for core services
- **Error rate:** ≤2% for successful queries
- **User satisfaction:** ≥4.0/5.0 rating

---

## 3. What We're NOT Doing

**Explicitly out of scope for Phase 2:**

1. ❌ **Multi-user voice identification** - Defer to Phase 4
2. ❌ **Learning from feedback** (automated model retraining) - Defer to Phase 3
3. ❌ **Full 10-zone deployment** - Phase 2 tests with 1-3 Wyoming devices
4. ❌ **Production Kubernetes deployment** of voice services - Docker Compose only
5. ❌ **Cross-model validation** - Single model inference for speed
6. ❌ **Mobile app** - Web admin UI only
7. ❌ **SMS/Email sharing** - Stub implementation, not fully functional
8. ❌ **Custom wake word training** - Use pre-trained Jarvis/Athena models
9. ❌ **Multi-language support** - English only for Phase 2
10. ❌ **Commercial API alternatives** - Free tier APIs only (open source requirement)

**Deferred to Phase 3:**
- Advanced learning algorithms
- Occupancy-based routing
- Property context enrichment (guest guide integration)
- Voice identification and personalization

---

## 4. Architecture Principles

### Principle 1: Admin-First Configuration

**From:** [Admin Integration Decision](../decisions/2025-01-13-admin-app-as-configuration-interface.md)

**All features must be configurable via admin UI:**
- RAG services: Enable/disable, API keys, cache settings
- Guest mode: Restrictions, calendar URL, buffer times
- Quality tracking: Enable/disable feedback, metric retention
- Performance: Cache TTLs, timeout values

**Implementation pattern:**
1. Database model for configuration (PostgreSQL)
2. Admin backend API endpoints (FastAPI)
3. Admin frontend UI pages (vanilla JS)
4. Services poll admin API every 60s for config updates

### Principle 2: Open Source Readiness

**From:** [Open Source Release Decision](../decisions/2025-01-13-open-source-release-target.md)

**All code must be production-ready for public release:**
- No hardcoded secrets (use .env.example)
- Comprehensive documentation (inline + docs/)
- Platform-independent (Mac, Linux, Docker)
- Multiple API provider support (free tiers)
- MIT or Apache 2.0 license
- ≥90% test coverage

**Implementation requirements:**
1. `.env.example` for every service showing required variables
2. README.md in each service directory
3. Type hints and docstrings for all functions
4. Unit + integration tests
5. Working Docker Compose example in `examples/`

### Principle 3: Pattern Consistency

**All RAG services follow identical structure:**
- FastAPI application with lifespan management
- `@cached` decorator for API calls (from `shared/cache.py`)
- Three-tier error handling (ValueError → 404, HTTPStatusError → 502, Exception → 500)
- Structured logging with `shared/logging_config.py`
- Health check endpoint at `/health`
- Port allocation: 8010+ (sequential)

**All admin endpoints follow identical structure:**
- OIDC authentication via `Depends(get_current_user)`
- Permission checking (read/write/delete)
- Audit logging for all changes
- Pydantic models for request/response
- Alembic migrations for schema changes

---

## Phase 2.0: Branch Setup and Preparation

### Overview

Before beginning Phase 2 implementation, establish a clean git branch for all Phase 2 work **in a separate directory**. This enables parallel development: Phase 1 work continues in the original directory on main branch, while Phase 2 work happens in a new directory on the phase-2 branch.

**Timeline:** 30 minutes - 1 hour
**Dependencies:** Phase 1 must be 100% complete and working

**Development Strategy:**
- **Original directory** (`/Users/jaystuart/dev/project-athena/`) - stays on `main` branch
- **New directory** (`/Users/jaystuart/dev/project-athena-phase2/`) - uses `phase-2-complete-features` branch
- No branch switching required - work in parallel without interference

---

### Step 1: Verify Phase 1 Completion

Before creating the Phase 2 branch, ensure Phase 1 is fully functional and all changes are committed.

**Commands:**

```bash
# Navigate to project root
cd /Users/jaystuart/dev/project-athena

# Check current git status
git status

# Verify current branch (should be 'main' or 'master')
git branch --show-current
```

**Expected output:**
- Clean working directory (no uncommitted changes)
- On main/master branch
- All Phase 1 features tested and working

**If there are uncommitted changes:**

```bash
# Review uncommitted changes
git status
git diff

# Stage all changes
git add .

# Create Phase 1 completion commit
git commit -m "Complete Phase 1: Core voice assistant implementation

- Gateway service (LiteLLM) operational
- Orchestrator service (LangGraph) complete
- 3 base RAG services deployed (Weather, Airports, Sports)
- Home Assistant Assist Pipelines configured
- Admin interface deployed to Kubernetes
- Mac Studio/mini infrastructure operational

Phase 1 complete and tested. Ready for Phase 2 development.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to remote
git push origin main
```

---

### Step 2: Create Phase 2 Development Branch

Create a dedicated branch for all Phase 2 development work. **Important:** This step only creates the branch in the current directory - you'll check it out in a separate directory in the next step.

**Commands:**

```bash
# Create Phase 2 branch (but don't switch to it)
git branch phase-2-complete-features

# Push branch to remote and set upstream
git push -u origin phase-2-complete-features

# Verify branch exists (should still be on main)
git branch -a
# Output shows:
#   main
#   phase-2-complete-features
#   remotes/origin/main
#   remotes/origin/phase-2-complete-features

# Confirm you're still on main
git branch --show-current
# Output: main
```

**Branch naming convention:**
- `phase-2-complete-features` - Main Phase 2 branch
- Can create sub-branches for specific features:
  - `phase-2/rag-services` - For RAG services only
  - `phase-2/guest-mode` - For guest mode only
  - `phase-2/quality-tracking` - For quality tracking only

---

### Step 3: Clone Repository to New Directory for Phase 2

Clone the repository to a separate directory for Phase 2 development. This allows parallel work on main and Phase 2 branches without constant branch switching.

**Commands:**

```bash
# Navigate to parent directory
cd /Users/jaystuart/dev

# Clone repository to new directory for Phase 2 work
git clone project-athena project-athena-phase2

# Navigate to Phase 2 directory
cd project-athena-phase2

# Checkout the Phase 2 branch
git checkout phase-2-complete-features

# Verify you're on Phase 2 branch
git branch --show-current
# Output: phase-2-complete-features

# Verify remote tracking is set up
git branch -vv
# Output: * phase-2-complete-features <hash> [origin/phase-2-complete-features] <commit message>
```

**Directory structure after this step:**

```
/Users/jaystuart/dev/
├── project-athena/              # Original directory - stays on 'main' branch
│   └── (continue main branch work here)
└── project-athena-phase2/       # New directory - on 'phase-2-complete-features' branch
    └── (do all Phase 2 work here)
```

**Benefits of this approach:**

1. ✅ **Parallel development** - Work on main and Phase 2 simultaneously
2. ✅ **No branch switching** - Each directory has its own branch
3. ✅ **Easy comparison** - Can compare files across branches easily
4. ✅ **Separate builds** - Run both main and Phase 2 services at same time (different ports)
5. ✅ **Safe experimentation** - Phase 2 changes don't affect main directory

---

### Step 4: Document Phase 2 Start

Create a marker commit documenting the start of Phase 2 development in the Phase 2 directory.

**Commands:**

```bash
# Make sure you're in the Phase 2 directory
cd /Users/jaystuart/dev/project-athena-phase2

# Verify you're on the Phase 2 branch
git branch --show-current
# Output: phase-2-complete-features

# Create a Phase 2 kickoff document
cat > PHASE2_START.md << 'EOF'
# Phase 2 Development Started

**Date:** 2025-01-13
**Branch:** phase-2-complete-features
**Development Directory:** /Users/jaystuart/dev/project-athena-phase2

## Phase 2 Scope

This branch implements Phase 2 features:
- 7 additional RAG services (News, Events, Stocks, Recipes, Dining, Streaming, Flights)
- Full guest mode with Airbnb calendar integration
- Quality tracking and feedback system
- Performance optimization (≤4.0s target)
- Admin UI extensions for all features

## Implementation Plan

See: thoughts/shared/plans/2025-01-13-phase2-complete-implementation.md

## Development Strategy

**Parallel Development:**
- Main branch work continues in: /Users/jaystuart/dev/project-athena/
- Phase 2 work happens in: /Users/jaystuart/dev/project-athena-phase2/
- No branch switching required - separate directories

## Merge Strategy

Phase 2 will be merged back to main when:
- All features implemented and tested
- Test coverage ≥90%
- Documentation complete
- Performance targets met
- Code review approved

EOF

# Add and commit the marker
git add PHASE2_START.md
git commit -m "Start Phase 2 development

Creating feature branch for Phase 2 implementation.
See PHASE2_START.md for scope and plan.

Development directory: /Users/jaystuart/dev/project-athena-phase2
Main branch directory: /Users/jaystuart/dev/project-athena

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to remote
git push
```

---

### Step 5: Set Up Branch Protection (Optional)

If using GitHub/GitLab, set up branch protection rules to prevent accidental force-pushes or deletions.

**GitHub Branch Protection Settings:**

1. Go to repository → Settings → Branches
2. Add rule for `phase-2-complete-features`
3. Enable:
   - ✅ Require pull request reviews before merging (optional)
   - ✅ Require status checks to pass before merging (if CI/CD set up)
   - ✅ Require branches to be up to date before merging
   - ❌ Do not require approval for your own PRs (if working solo)

**Or via command line (if using GitHub CLI):**

```bash
# Protect the Phase 2 branch
gh api repos/:owner/:repo/branches/phase-2-complete-features/protection \
  --method PUT \
  --field required_status_checks=null \
  --field enforce_admins=false \
  --field required_pull_request_reviews=null \
  --field restrictions=null
```

---

### Step 6: Create .env.example Files for Phase 2

Before starting implementation, create `.env.example` files for all new services (open source requirement).

**Commands:**

```bash
# Make sure you're in the Phase 2 directory
cd /Users/jaystuart/dev/project-athena-phase2

# Create .env.example for each new RAG service
for service in news events stocks recipes dining streaming flights; do
  mkdir -p src/rag/$service
  cat > src/rag/$service/.env.example << EOF
# ${service^} RAG Service Configuration

# API Key (get free key at: [PROVIDER_URL])
${service^^}_API_KEY=your_api_key_here

# Redis Cache
REDIS_URL=redis://192.168.10.181:6379/0

# Service Configuration
${service^^}_SERVICE_PORT=801X
EOF
done

# Create .env.example for mode service
mkdir -p src/mode_service
cat > src/mode_service/.env.example << 'EOF'
# Mode Service Configuration

# Admin API URL
ADMIN_API_URL=http://localhost:5000

# Redis Cache
REDIS_URL=redis://192.168.10.181:6379/0

# Service Configuration
MODE_SERVICE_PORT=8020

# Calendar Polling (seconds)
CALENDAR_POLL_INTERVAL_SECONDS=600
EOF

# Commit the .env.example files
git add src/rag/*/.env.example src/mode_service/.env.example
git commit -m "Add .env.example files for Phase 2 services

Creating environment templates for:
- 7 new RAG services (News, Events, Stocks, Recipes, Dining, Streaming, Flights)
- Mode service (guest mode detection)

Part of open source readiness requirements.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

---

### Phase 2.0 Success Criteria

#### Automated Verification:

**In main directory (`/Users/jaystuart/dev/project-athena`):**
- [ ] Git status clean: `git status` shows no uncommitted changes
- [ ] On main branch: `git branch --show-current` returns `main`
- [ ] Phase 2 branch exists: `git branch -a | grep phase-2-complete-features`

**In Phase 2 directory (`/Users/jaystuart/dev/project-athena-phase2`):**
- [ ] Directory exists: `test -d /Users/jaystuart/dev/project-athena-phase2 && echo "exists"`
- [ ] On Phase 2 branch: `cd /Users/jaystuart/dev/project-athena-phase2 && git branch --show-current` returns `phase-2-complete-features`
- [ ] Can pull from remote: `git pull` succeeds
- [ ] Can push to remote: `git push` succeeds
- [ ] PHASE2_START.md exists: `test -f PHASE2_START.md && echo "exists"`
- [ ] .env.example files exist: `find src -name ".env.example" | wc -l` shows 8+ files

**Both directories:**
- [ ] Main directory on main branch: `cd /Users/jaystuart/dev/project-athena && git branch --show-current`
- [ ] Phase 2 directory on phase-2 branch: `cd /Users/jaystuart/dev/project-athena-phase2 && git branch --show-current`

#### Manual Verification:

- [ ] Phase 1 is fully functional and tested
- [ ] All Phase 1 services are running correctly in main directory
- [ ] Main branch is stable (can be deployed to production)
- [ ] Branch protection configured (if using GitHub/GitLab)
- [ ] Team notified of Phase 2 branch (if working with others)
- [ ] Can work in both directories simultaneously without conflicts
- [ ] Development environment is ready in Phase 2 directory

**Implementation Note:**
- Do NOT proceed to Phase 2.1 until all success criteria are met and Phase 1 is verified working
- All Phase 2 work should be done in `/Users/jaystuart/dev/project-athena-phase2/`
- Main branch work continues in `/Users/jaystuart/dev/project-athena/`

---

## Phase 2.1: Additional RAG Services (7 Services)

### Overview

Implement 7 new RAG services following the established pattern from Weather/Airports/Sports services. Each service provides knowledge retrieval for specific domains.

**Services to implement:**
1. News (NewsAPI)
2. Events (Eventbrite)
3. Stocks (Alpha Vantage)
4. Recipes (Spoonacular)
5. Dining (Yelp/Google Places)
6. Streaming (TMDB/JustWatch)
7. Flights (FlightAware - flight tracking, not airport info)

**Timeline:** 2-3 weeks (2-3 days per service)
**Dependencies:** Phase 1 complete, Orchestrator operational

---

### Service 1: News RAG Service

**API:** NewsAPI (https://newsapi.org)
- Free tier: 100 requests/day, 1000 requests/month
- Endpoints: Top headlines, everything search, sources
- Rate limit: 1 request/second

**Port:** 8013

**File:** `src/rag/news/main.py`

**Endpoints:**
- `GET /health` - Health check
- `GET /news/headlines?country={country}&category={category}` - Top headlines
- `GET /news/search?q={query}&from={date}&to={date}` - Search news
- `GET /news/sources?country={country}` - News sources

**Caching strategy:**
- Headlines: 15 minutes (breaking news changes frequently)
- Search results: 30 minutes
- Sources list: 1 hour

**Implementation:**

```python
"""
News RAG Service - NewsAPI Integration

Provides news headline and search with caching.

Endpoints:
- GET /health - Health check
- GET /news/headlines?country={country}&category={category} - Top headlines
- GET /news/search?q={query} - Search news articles
- GET /news/sources?country={country} - Available news sources
"""
import os
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

# Import shared utilities
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.cache import CacheClient, cached
from shared.logging_config import configure_logging

# Configure logging
logger = configure_logging("news-rag")

# Environment variables
NEWSAPI_API_KEY = os.getenv("NEWSAPI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.10.181:6379/0")
SERVICE_PORT = int(os.getenv("NEWS_SERVICE_PORT", "8013"))

# NewsAPI base URL
NEWSAPI_BASE_URL = "https://newsapi.org/v2"

# Cache client
cache = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global cache

    # Startup
    logger.info("Starting News RAG service")
    cache = CacheClient(redis_url=REDIS_URL)
    await cache.connect()

    yield

    # Shutdown
    logger.info("Shutting down News RAG service")
    if cache:
        await cache.disconnect()


app = FastAPI(
    title="News RAG Service",
    description="NewsAPI integration with caching",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "news-rag",
        "version": "1.0.0"
    }


@cached(ttl=900, key_prefix="news_headlines")  # Cache for 15 minutes
async def get_top_headlines_api(country: str = "us", category: Optional[str] = None) -> Dict[str, Any]:
    """
    Get top headlines from NewsAPI.

    Args:
        country: Country code (e.g., "us", "gb", "ca")
        category: Category filter (business, entertainment, health, science, sports, technology)

    Returns:
        Dict with articles list
    """
    logger.info(f"Fetching top headlines: country={country}, category={category}")

    url = f"{NEWSAPI_BASE_URL}/top-headlines"
    params = {
        "apiKey": NEWSAPI_API_KEY,
        "country": country,
        "pageSize": 10
    }
    if category:
        params["category"] = category

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


@cached(ttl=1800, key_prefix="news_search")  # Cache for 30 minutes
async def search_news_api(query: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Search news articles.

    Args:
        query: Search query
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)

    Returns:
        Dict with articles list
    """
    logger.info(f"Searching news: query={query}, from={from_date}, to={to_date}")

    url = f"{NEWSAPI_BASE_URL}/everything"
    params = {
        "apiKey": NEWSAPI_API_KEY,
        "q": query,
        "pageSize": 10,
        "sortBy": "relevancy"
    }
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


@app.get("/news/headlines")
async def get_headlines(
    country: str = Query("us", description="Country code (us, gb, ca, etc.)"),
    category: Optional[str] = Query(None, description="Category (business, sports, technology, etc.)")
):
    """Get top news headlines."""
    try:
        data = await get_top_headlines_api(country, category)

        articles = [{
            "title": article["title"],
            "description": article.get("description"),
            "source": article["source"]["name"],
            "url": article["url"],
            "published_at": article["publishedAt"]
        } for article in data.get("articles", [])]

        return {
            "headlines": articles,
            "total_results": data.get("totalResults", len(articles))
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="News not found")
        logger.error(f"NewsAPI API error: {e}")
        raise HTTPException(status_code=502, detail="News service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/news/search")
async def search_news(
    q: str = Query(..., description="Search query"),
    days_back: int = Query(7, ge=1, le=30, description="Number of days to search back (1-30)")
):
    """Search news articles."""
    try:
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        data = await search_news_api(q, from_date, to_date)

        articles = [{
            "title": article["title"],
            "description": article.get("description"),
            "source": article["source"]["name"],
            "url": article["url"],
            "published_at": article["publishedAt"]
        } for article in data.get("articles", [])]

        return {
            "articles": articles,
            "total_results": data.get("totalResults", len(articles)),
            "query": q,
            "date_range": {"from": from_date, "to": to_date}
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"NewsAPI API error: {e}")
        raise HTTPException(status_code=502, detail="News service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting News RAG service on port {SERVICE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
```

**Configuration:** `src/rag/news/requirements.txt`

```txt
# Project Athena - News RAG Service

fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
python-dotenv>=1.0.0
httpx>=0.24.0
redis>=5.0.0
structlog>=23.2.0
```

**Environment:** `src/rag/news/.env.example`

```bash
# NewsAPI Configuration
# Get free API key at: https://newsapi.org/register
NEWSAPI_API_KEY=your_api_key_here

# Redis Cache
REDIS_URL=redis://192.168.10.181:6379/0

# Service Configuration
NEWS_SERVICE_PORT=8013
```

**Database Schema:** (Admin backend - `admin/backend/app/models.py`)

Add to RAGConnector model's `connector_type` enum:
```python
connector_type = Column(String(50), nullable=False)  # Add 'news' as valid type
```

No new table needed - uses existing `rag_connectors` table.

---

### Service 2-7: Remaining RAG Services

**Following the same pattern, implement:**

2. **Events RAG** (Port 8014) - Eventbrite API
   - Endpoints: Search events, event details, categories
   - Cache: 1 hour for search, 2 hours for details

3. **Stocks RAG** (Port 8015) - Alpha Vantage API
   - Endpoints: Quote, intraday prices, company overview
   - Cache: 5 minutes for quotes, 1 hour for company info

4. **Recipes RAG** (Port 8016) - Spoonacular API
   - Endpoints: Search recipes, recipe details, ingredients
   - Cache: 24 hours for recipes, 1 week for ingredients

5. **Dining RAG** (Port 8017) - Yelp Fusion API
   - Endpoints: Search restaurants, business details, reviews
   - Cache: 6 hours for search, 24 hours for business info

6. **Streaming RAG** (Port 8018) - TMDB API
   - Endpoints: Search movies/shows, details, where to watch
   - Cache: 24 hours for content, 12 hours for availability

7. **Flights RAG** (Port 8019) - FlightAware API
   - Endpoints: Flight tracking, flight status, flight history
   - Cache: 5 minutes for real-time status, 1 hour for history

**Each service includes:**
- Main service file (`src/rag/{service}/main.py`)
- Requirements file (`src/rag/{service}/requirements.txt`)
- Environment example (`.env.example`)
- README with API signup instructions
- Health check endpoint
- 2-3 primary endpoints
- Proper error handling
- Redis caching
- Structured logging

---

### Phase 2.1 Success Criteria

#### Automated Verification:

- [ ] All 7 services start successfully: `cd src/rag/{service} && python main.py`
- [ ] Health checks pass: `curl http://localhost:801{3-9}/health` returns 200
- [ ] Redis connection works: All services connect to Redis on startup
- [ ] API calls work: Each service can query its external API
- [ ] Caching works: Second identical request is faster (cache hit)
- [ ] Error handling works: Invalid API key returns 502, invalid input returns 404
- [ ] Tests pass: `pytest tests/rag/` has ≥90% coverage
- [ ] Linting passes: `black src/rag/ && flake8 src/rag/ && mypy src/rag/`
- [ ] Docker builds: `docker build -t athena-rag-{service} src/rag/{service}`

#### Manual Verification:

- [ ] News headlines return current stories from last 24 hours
- [ ] Event search finds local events in your area
- [ ] Stock quotes return current prices (within 15 minutes delay for free tier)
- [ ] Recipe search finds relevant recipes for ingredients
- [ ] Restaurant search finds businesses near specified location
- [ ] Movie/show search finds content on streaming platforms
- [ ] Flight tracking returns real-time flight status
- [ ] All services respond in ≤2 seconds on cache hit
- [ ] All services respond in ≤5 seconds on cache miss
- [ ] Error messages are user-friendly (no stack traces in responses)
- [ ] `.env.example` files have clear instructions for getting API keys

---

## Phase 2.2: Guest Mode Implementation

### Overview

Implement automatic guest mode detection via Airbnb calendar integration, with permission scoping and PII protection. This allows Airbnb hosts to automatically restrict voice assistant capabilities during guest stays.

**Key Features:**
- iCal calendar polling (every 10 minutes)
- Automatic mode detection (guest vs owner)
- Permission scoping (entity allowlist/denylist)
- Voice PIN override for owner access
- PII scrubbing in guest mode
- Auto-purge on checkout

**Timeline:** 3-4 weeks
**Dependencies:** Phase 1 complete, Orchestrator operational

---

### Database Schema Changes

**File:** `admin/backend/app/models.py`

```python
class GuestModeConfig(Base):
    """
    Guest mode configuration for vacation rental properties.

    Stores calendar integration settings, permission scopes, and
    data retention policies for guest mode operation.
    """
    __tablename__ = 'guest_mode_config'

    id = Column(Integer, primary_key=True)

    # Enable/disable guest mode globally
    enabled = Column(Boolean, default=False, nullable=False)

    # Calendar Integration
    calendar_source = Column(String(50), default='ical')  # 'ical', 'hostaway', 'guesty'
    calendar_url = Column(String(500))  # iCal URL for Airbnb calendar
    calendar_poll_interval_minutes = Column(Integer, default=10)

    # Buffer Times (hours)
    buffer_before_checkin_hours = Column(Integer, default=2)
    buffer_after_checkout_hours = Column(Integer, default=1)

    # Owner Override
    owner_pin = Column(String(128))  # Hashed PIN for voice override
    override_timeout_minutes = Column(Integer, default=60)

    # Permission Scopes (JSON arrays)
    guest_allowed_intents = Column(ARRAY(String), default=[])
    guest_restricted_entities = Column(ARRAY(String), default=[])
    guest_allowed_domains = Column(ARRAY(String), default=[])

    # Rate Limiting
    max_queries_per_minute_guest = Column(Integer, default=10)
    max_queries_per_minute_owner = Column(Integer, default=100)

    # Data Retention
    guest_data_retention_hours = Column(Integer, default=24)
    auto_purge_enabled = Column(Boolean, default=True)

    # Additional flexible config
    config = Column(JSONB, default={})

    # Audit fields
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship('User', foreign_keys=[created_by_id])

    __table_args__ = (
        Index('idx_guest_mode_enabled', 'enabled'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'enabled': self.enabled,
            'calendar_source': self.calendar_source,
            'calendar_url': self.calendar_url if self.calendar_url else None,
            'calendar_poll_interval_minutes': self.calendar_poll_interval_minutes,
            'buffer_before_checkin_hours': self.buffer_before_checkin_hours,
            'buffer_after_checkout_hours': self.buffer_after_checkout_hours,
            'guest_allowed_intents': self.guest_allowed_intents,
            'guest_restricted_entities': self.guest_restricted_entities,
            'guest_allowed_domains': self.guest_allowed_domains,
            'max_queries_per_minute_guest': self.max_queries_per_minute_guest,
            'guest_data_retention_hours': self.guest_data_retention_hours,
            'auto_purge_enabled': self.auto_purge_enabled,
            'config': self.config,
            'created_by': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class CalendarEvent(Base):
    """
    Calendar events from vacation rental calendar (Airbnb, Vrbo, etc.).

    Cached events from iCal feed or PMS webhooks.
    """
    __tablename__ = 'calendar_events'

    id = Column(Integer, primary_key=True)

    # Event identification
    external_id = Column(String(255), unique=True, nullable=False)  # UID from iCal
    source = Column(String(50), default='ical')  # 'ical', 'airbnb', 'vrbo', 'hostaway'

    # Event details
    title = Column(String(255))
    checkin = Column(DateTime(timezone=True), nullable=False)
    checkout = Column(DateTime(timezone=True), nullable=False)
    guest_name = Column(String(255))  # May be redacted based on PMS settings
    notes = Column(Text)

    # Status
    status = Column(String(50), default='confirmed')  # 'confirmed', 'cancelled', 'pending'

    # Metadata
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_calendar_checkin', 'checkin'),
        Index('idx_calendar_checkout', 'checkout'),
        Index('idx_calendar_status', 'status'),
        Index('idx_calendar_synced_at', 'synced_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'external_id': self.external_id,
            'source': self.source,
            'title': self.title,
            'checkin': self.checkin.isoformat(),
            'checkout': self.checkout.isoformat(),
            'guest_name': self.guest_name,
            'status': self.status,
            'synced_at': self.synced_at.isoformat(),
        }


class ModeOverride(Base):
    """
    Manual mode overrides (owner voice PIN activation).

    Tracks when owner manually switches to owner mode via voice PIN.
    """
    __tablename__ = 'mode_overrides'

    id = Column(Integer, primary_key=True)

    # Override details
    mode = Column(String(20), nullable=False)  # 'owner' or 'guest'
    activated_by = Column(String(50))  # 'voice_pin', 'admin_ui', 'api'
    activated_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))  # Null = no expiration

    # Context
    voice_device_id = Column(String(100))  # Which device activated it
    ip_address = Column(String(50))

    # Audit
    deactivated_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('idx_mode_override_active', 'activated_at', 'expires_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'mode': self.mode,
            'activated_by': self.activated_by,
            'activated_at': self.activated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'voice_device_id': self.voice_device_id,
            'deactivated_at': self.deactivated_at.isoformat() if self.deactivated_at else None,
        }
```

**Alembic Migration:** `admin/backend/alembic/versions/005_guest_mode.py`

```python
"""
Add guest mode tables

Revision ID: 005
Revises: 004
Create Date: 2025-01-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Add tables for guest mode"""

    # Guest mode configuration
    op.create_table(
        'guest_mode_config',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('enabled', sa.Boolean(), default=False, nullable=False),
        sa.Column('calendar_source', sa.String(50), default='ical'),
        sa.Column('calendar_url', sa.String(500)),
        sa.Column('calendar_poll_interval_minutes', sa.Integer(), default=10),
        sa.Column('buffer_before_checkin_hours', sa.Integer(), default=2),
        sa.Column('buffer_after_checkout_hours', sa.Integer(), default=1),
        sa.Column('owner_pin', sa.String(128)),
        sa.Column('override_timeout_minutes', sa.Integer(), default=60),
        sa.Column('guest_allowed_intents', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('guest_restricted_entities', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('guest_allowed_domains', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('max_queries_per_minute_guest', sa.Integer(), default=10),
        sa.Column('max_queries_per_minute_owner', sa.Integer(), default=100),
        sa.Column('guest_data_retention_hours', sa.Integer(), default=24),
        sa.Column('auto_purge_enabled', sa.Boolean(), default=True),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    op.create_index('idx_guest_mode_enabled', 'guest_mode_config', ['enabled'])

    # Seed default configuration
    op.execute("""
        INSERT INTO guest_mode_config (enabled, guest_allowed_intents, guest_allowed_domains, created_by_id)
        VALUES (
            false,
            ARRAY['weather', 'time', 'general_question'],
            ARRAY['light', 'media_player', 'switch', 'scene'],
            1
        )
    """)

    # Calendar events
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('external_id', sa.String(255), unique=True, nullable=False),
        sa.Column('source', sa.String(50), default='ical'),
        sa.Column('title', sa.String(255)),
        sa.Column('checkin', sa.TIMESTAMP(), nullable=False),
        sa.Column('checkout', sa.TIMESTAMP(), nullable=False),
        sa.Column('guest_name', sa.String(255)),
        sa.Column('notes', sa.Text()),
        sa.Column('status', sa.String(50), default='confirmed'),
        sa.Column('synced_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    op.create_index('idx_calendar_checkin', 'calendar_events', ['checkin'])
    op.create_index('idx_calendar_checkout', 'calendar_events', ['checkout'])
    op.create_index('idx_calendar_status', 'calendar_events', ['status'])
    op.create_index('idx_calendar_synced_at', 'calendar_events', ['synced_at'])

    # Mode overrides
    op.create_table(
        'mode_overrides',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('activated_by', sa.String(50)),
        sa.Column('activated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.TIMESTAMP()),
        sa.Column('voice_device_id', sa.String(100)),
        sa.Column('ip_address', sa.String(50)),
        sa.Column('deactivated_at', sa.TIMESTAMP())
    )

    op.create_index('idx_mode_override_active', 'mode_overrides', ['activated_at', 'expires_at'])


def downgrade():
    """Remove guest mode tables"""
    op.drop_table('mode_overrides')
    op.drop_table('calendar_events')
    op.drop_table('guest_mode_config')
```

---

### Mode Service Implementation

**File:** `src/mode_service/main.py`

This service runs continuously, polling the Airbnb calendar and determining the current mode.

```python
"""
Mode Service - Guest Mode Detection and Management

Polls Airbnb iCal calendar, detects active stays, and determines current mode (guest/owner).
Provides API for orchestrator to query current mode and permissions.
"""
import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
import httpx
from icalendar import Calendar
import pytz
from contextlib import asynccontextmanager

# Import shared utilities
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.logging_config import configure_logging
from shared.cache import CacheClient

# Configure logging
logger = configure_logging("mode-service")

# Environment variables
ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://localhost:5000")
REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.10.181:6379/0")
SERVICE_PORT = int(os.getenv("MODE_SERVICE_PORT", "8020"))
POLL_INTERVAL_SECONDS = int(os.getenv("CALENDAR_POLL_INTERVAL_SECONDS", "600"))  # 10 minutes

# Global state
cache = None
current_config = {}
current_events = []
current_mode = "guest"  # Safe default


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global cache

    # Startup
    logger.info("Starting Mode Service")
    cache = CacheClient(redis_url=REDIS_URL)
    await cache.connect()

    # Load initial config
    await load_config()

    # Start background tasks
    asyncio.create_task(calendar_polling_loop())
    asyncio.create_task(config_refresh_loop())

    yield

    # Shutdown
    logger.info("Shutting down Mode Service")
    if cache:
        await cache.disconnect()


app = FastAPI(
    title="Mode Service",
    description="Guest mode detection and management",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mode-service",
        "version": "1.0.0",
        "current_mode": current_mode,
        "events_loaded": len(current_events)
    }


async def load_config():
    """Load guest mode configuration from admin API."""
    global current_config

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ADMIN_API_URL}/api/guest-mode/config")
            response.raise_for_status()
            current_config = response.json()
            logger.info("Loaded guest mode configuration", enabled=current_config.get('enabled'))
    except Exception as e:
        logger.error(f"Failed to load config from admin API: {e}")
        # Use safe defaults
        current_config = {
            'enabled': False,
            'buffer_before_checkin_hours': 2,
            'buffer_after_checkout_hours': 1,
            'guest_allowed_intents': ['weather', 'time', 'general_question'],
            'guest_restricted_entities': ['lock.*', 'garage.*', 'alarm.*'],
            'guest_allowed_domains': ['light', 'media_player', 'switch', 'scene'],
        }


async def config_refresh_loop():
    """Periodically refresh configuration from admin API."""
    while True:
        await asyncio.sleep(60)  # Check every 60 seconds
        await load_config()


async def calendar_polling_loop():
    """Periodically poll iCal calendar for events."""
    global current_events, current_mode

    while True:
        try:
            if current_config.get('enabled') and current_config.get('calendar_url'):
                # Fetch iCal feed
                calendar_url = current_config['calendar_url']
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(calendar_url)
                    response.raise_for_status()

                    # Parse iCal
                    cal = Calendar.from_ical(response.content)
                    events = []

                    for component in cal.walk():
                        if component.name == "VEVENT":
                            events.append({
                                'uid': str(component.get('uid')),
                                'summary': str(component.get('summary', '')),
                                'dtstart': component.get('dtstart').dt,
                                'dtend': component.get('dtend').dt,
                            })

                    current_events = events
                    logger.info(f"Loaded {len(events)} calendar events")

                    # Update current mode
                    current_mode = determine_mode()
                    logger.info(f"Current mode: {current_mode}")

        except Exception as e:
            logger.error(f"Calendar polling error: {e}", exc_info=True)

        # Wait for next poll
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


def determine_mode() -> str:
    """
    Determine current mode based on calendar events and overrides.

    Priority:
    1. Manual override (from database)
    2. Active calendar event (with buffer times)
    3. Default mode (guest for safety)
    """
    # TODO: Check mode_overrides table for active override
    # For now, skip override check

    # Check for active stay
    now = datetime.now(pytz.UTC)
    buffer_before = timedelta(hours=current_config.get('buffer_before_checkin_hours', 2))
    buffer_after = timedelta(hours=current_config.get('buffer_after_checkout_hours', 1))

    for event in current_events:
        checkin = event['dtstart']
        checkout = event['dtend']

        # Make timezone-aware if needed
        if checkin.tzinfo is None:
            checkin = pytz.UTC.localize(checkin)
        if checkout.tzinfo is None:
            checkout = pytz.UTC.localize(checkout)

        checkin_with_buffer = checkin - buffer_before
        checkout_with_buffer = checkout + buffer_after

        if checkin_with_buffer <= now <= checkout_with_buffer:
            return "guest"

    # No active stay - owner mode
    return "owner"


@app.get("/mode/current")
async def get_current_mode():
    """Get current mode and permissions."""
    return {
        "mode": current_mode,
        "config": {
            "allowed_intents": current_config.get('guest_allowed_intents', []) if current_mode == "guest" else [],
            "restricted_entities": current_config.get('guest_restricted_entities', []) if current_mode == "guest" else [],
            "allowed_domains": current_config.get('guest_allowed_domains', []) if current_mode == "guest" else [],
            "max_queries_per_minute": current_config.get('max_queries_per_minute_guest', 10) if current_mode == "guest" else 100
        },
        "active_events": [
            {
                "checkin": event['dtstart'].isoformat(),
                "checkout": event['dtend'].isoformat(),
                "summary": event['summary']
            }
            for event in current_events
        ]
    }


@app.get("/mode/events")
async def get_calendar_events():
    """Get all calendar events."""
    return {
        "events": [
            {
                "uid": event['uid'],
                "summary": event['summary'],
                "checkin": event['dtstart'].isoformat(),
                "checkout": event['dtend'].isoformat()
            }
            for event in current_events
        ],
        "total": len(current_events),
        "config_enabled": current_config.get('enabled', False)
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Mode Service on port {SERVICE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
```

**Dependencies:** `src/mode_service/requirements.txt`

```txt
# Project Athena - Mode Service

fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
python-dotenv>=1.0.0
httpx>=0.24.0
redis>=5.0.0
structlog>=23.2.0
icalendar>=5.0.0
pytz>=2023.3
```

**Environment:** `src/mode_service/.env.example`

```bash
# Admin API Configuration
ADMIN_API_URL=http://localhost:5000

# Redis Cache
REDIS_URL=redis://192.168.10.181:6379/0

# Service Configuration
MODE_SERVICE_PORT=8020

# Calendar Polling
CALENDAR_POLL_INTERVAL_SECONDS=600  # 10 minutes
```

---

### Admin API Endpoints

**File:** `admin/backend/app/routes/guest_mode.py`

```python
"""
Guest mode configuration API routes.

Manages guest mode settings, calendar integration, and permissions.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
import structlog

from app.database import get_db
from app.auth.oidc import get_current_user
from app.models import User, GuestModeConfig, CalendarEvent, AuditLog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/guest-mode", tags=["guest-mode"])


class GuestModeConfigUpdate(BaseModel):
    """Request model for updating guest mode configuration."""
    enabled: bool = None
    calendar_source: str = None
    calendar_url: str = None
    calendar_poll_interval_minutes: int = None
    buffer_before_checkin_hours: int = None
    buffer_after_checkout_hours: int = None
    guest_allowed_intents: List[str] = None
    guest_restricted_entities: List[str] = None
    guest_allowed_domains: List[str] = None
    max_queries_per_minute_guest: int = None
    guest_data_retention_hours: int = None
    auto_purge_enabled: bool = None


def create_audit_log(db, user, action, config, old_value=None, new_value=None, request=None):
    """Create audit log entry."""
    audit = AuditLog(
        user_id=user.id,
        action=action,
        resource_type='guest_mode_config',
        resource_id=config.id,
        old_value=old_value,
        new_value=new_value,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get('user-agent') if request else None,
        success=True,
    )
    db.add(audit)
    db.commit()


@app.get("/config")
async def get_guest_mode_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current guest mode configuration."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    config = db.query(GuestModeConfig).first()
    if not config:
        # Create default config
        config = GuestModeConfig(
            enabled=False,
            calendar_source='ical',
            guest_allowed_intents=['weather', 'time', 'general_question'],
            guest_allowed_domains=['light', 'media_player', 'switch', 'scene'],
            guest_restricted_entities=['lock.*', 'garage.*', 'alarm.*', 'camera.*'],
            created_by_id=current_user.id
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return config.to_dict()


@app.put("/config")
async def update_guest_mode_config(
    config_data: GuestModeConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update guest mode configuration."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    config = db.query(GuestModeConfig).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Store old values
    old_value = {
        'enabled': config.enabled,
        'calendar_url': config.calendar_url,
        'guest_allowed_intents': config.guest_allowed_intents
    }

    # Update fields
    if config_data.enabled is not None:
        config.enabled = config_data.enabled
    if config_data.calendar_source is not None:
        config.calendar_source = config_data.calendar_source
    if config_data.calendar_url is not None:
        config.calendar_url = config_data.calendar_url
    if config_data.calendar_poll_interval_minutes is not None:
        config.calendar_poll_interval_minutes = config_data.calendar_poll_interval_minutes
    if config_data.buffer_before_checkin_hours is not None:
        config.buffer_before_checkin_hours = config_data.buffer_before_checkin_hours
    if config_data.buffer_after_checkout_hours is not None:
        config.buffer_after_checkout_hours = config_data.buffer_after_checkout_hours
    if config_data.guest_allowed_intents is not None:
        config.guest_allowed_intents = config_data.guest_allowed_intents
    if config_data.guest_restricted_entities is not None:
        config.guest_restricted_entities = config_data.guest_restricted_entities
    if config_data.guest_allowed_domains is not None:
        config.guest_allowed_domains = config_data.guest_allowed_domains
    if config_data.max_queries_per_minute_guest is not None:
        config.max_queries_per_minute_guest = config_data.max_queries_per_minute_guest
    if config_data.guest_data_retention_hours is not None:
        config.guest_data_retention_hours = config_data.guest_data_retention_hours
    if config_data.auto_purge_enabled is not None:
        config.auto_purge_enabled = config_data.auto_purge_enabled

    db.commit()
    db.refresh(config)

    # Audit log
    new_value = {
        'enabled': config.enabled,
        'calendar_url': config.calendar_url,
        'guest_allowed_intents': config.guest_allowed_intents
    }
    create_audit_log(db, current_user, 'update', config,
                    old_value=old_value, new_value=new_value, request=request)

    logger.info("guest_mode_updated", config_id=config.id, enabled=config.enabled,
                user=current_user.username)

    return config.to_dict()


@app.get("/events")
async def get_calendar_events(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get calendar events."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    events = db.query(CalendarEvent)\
              .filter(CalendarEvent.status == 'confirmed')\
              .order_by(CalendarEvent.checkin.desc())\
              .offset(offset)\
              .limit(limit)\
              .all()

    return [event.to_dict() for event in events]
```

**Register router in `admin/backend/main.py`:**

```python
from app.routes import policies, secrets, devices, audit, users, servers, services, rag_connectors, voice_tests, guest_mode

app.include_router(guest_mode.router)
```

---

*[The implementation plan continues with Phase 2.3, 2.4, 2.5, testing strategy, and success criteria. Due to length limits, I'll complete this in the file write.]*

Let me complete the full Phase 2 plan file now:
