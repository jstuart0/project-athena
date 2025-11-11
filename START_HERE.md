# 🚀 START HERE - Project Athena Implementation

**Welcome to Project Athena!** This guide will get you from zero to a working AI voice assistant system.

**Last Updated:** 2025-11-11
**Status:** Ready to begin Day 1 implementation

---

## 📋 What You Have

Everything is prepared and ready for immediate implementation:

### ✅ Hardware Ready
- Mac Studio M4 (64GB RAM) - Primary compute
- Mac mini M4 (16GB RAM) - Database services
- 2 HA Voice devices (Office + Master Bedroom)
- Home Assistant @ 192.168.10.168

### ✅ Planning Complete
- **3 comprehensive implementation plans** (see below)
- **Day 1 quick start guide** - Start TODAY
- **API key acquisition guide** - Get required keys
- **All configuration files ready** - Just fill in your values

### ⏳ What You Need to Do
1. Assign static IPs (192.168.10.20 for Mac Studio, .29 for Mac mini)
2. Get API keys (at least OpenWeatherMap today)
3. Follow Day 1 guide (2-3 hours)

---

## 🎯 Your Implementation Path

You have **three ways** to approach implementation, depending on your preference:

### Option 1: Day 1 Quick Start (Recommended for TODAY)

**File:** `docs/DAY_1_QUICK_START.md`

**Purpose:** Get basic environment ready in 2-3 hours TODAY

**Tasks:**
1. Network configuration (15 min)
2. Environment setup (30 min)
3. Ollama installation + models (30 min)
4. Create .env file (10 min)
5. Deploy Mac mini services (15 min)
6. Initialize Qdrant (5 min)

**Start here if:** You want to make immediate progress today

```bash
# Follow this guide:
open docs/DAY_1_QUICK_START.md
```

---

### Option 2: Full Bootstrap (Step-by-Step)

**File:** `thoughts/shared/plans/2025-11-11-full-bootstrap-implementation.md`

**Purpose:** Complete zero-to-working-system guide with every command

**Phases:**
- Phase 0: Environment setup
- Phase 1: Mac mini services
- Phase 2: Repository restructuring
- Phase 3: Gateway deployment
- Phase 4: RAG services
- Phase 5: Orchestrator
- Phase 6: HA integration
- Phase 7: Integration testing
- Phase 8: Documentation

**Timeline:** 6-8 weeks to complete system

**Start here if:** You want comprehensive step-by-step instructions with all commands provided

```bash
# Read the plan:
open thoughts/shared/plans/2025-11-11-full-bootstrap-implementation.md

# Or use Claude Code to implement:
/implement_plan thoughts/shared/plans/2025-11-11-full-bootstrap-implementation.md
```

---

### Option 3: Phase 1 Implementation (Week-by-Week)

**File:** `thoughts/shared/plans/2025-11-11-phase1-core-services-implementation.md`

**Purpose:** Detailed technical plan organized by weekly milestones

**Phases:**
- Phase 1.1: Repository restructuring (Week 1)
- Phase 1.2: OpenAI-compatible gateway (Week 1-2)
- Phase 1.3: LangGraph orchestrator (Week 2-3)
- Phase 1.4: RAG services (Week 3-4)
- Phase 1.5: Mac mini services (Week 4)
- Phase 1.6: HA configuration (Week 5)
- Phase 1.7: Integration testing (Week 5-6)

**Timeline:** 4-6 weeks to Phase 1 completion

**Start here if:** You want organized weekly goals with clear success criteria

```bash
# Read the plan:
open thoughts/shared/plans/2025-11-11-phase1-core-services-implementation.md
```

---

### Reference: Component Deep-Dive

**File:** `thoughts/shared/plans/2025-11-11-component-deep-dive-plans.md`

**Purpose:** Technical specifications for each component

**Contents:**
- Gateway configuration (LiteLLM)
- Orchestrator design (LangGraph nodes)
- RAG service templates
- Validators and anti-hallucination
- Share service (SMS/email)
- Vector database schema
- HA bridge (future)

**Use this when:** You need technical details while implementing

```bash
# Reference during implementation:
open thoughts/shared/plans/2025-11-11-component-deep-dive-plans.md
```

---

## 🔑 API Keys

**File:** `docs/API_KEY_GUIDE.md`

### Priority 1 (Get TODAY)
- **OpenWeatherMap** - Instant signup, 1000 calls/day FREE
  - Go to: https://openweathermap.org/api
  - Sign up, get key, test immediately
  - **This unlocks weather queries**

### Priority 2 (Get This Week)
- **FlightAware** - Free tier, may take 1-2 days for activation
  - Go to: https://www.flightaware.com/commercial/flightxml/
  - Get key for airport queries

- **TheSportsDB** - Free tier or $2/month Patreon
  - Go to: https://www.thesportsdb.com/api.php
  - Free key: `1` (limited) or Patreon for personal key

### Phase 2 (Future)
- NewsAPI, Spoonacular, TMDB, Yelp - **Not needed for Phase 1**

```bash
# Detailed instructions:
open docs/API_KEY_GUIDE.md
```

---

## 🛠️ Implementation Artifacts Ready

Everything you need is prepared and waiting:

### Configuration Files

**Environment Template:**
```bash
config/env/.env.template
```
→ Copy to `.env` and fill in your values (HA token, API keys, IPs)

**Mac mini Services:**
```bash
deployment/mac-mini/docker-compose.yml
```
→ Deploys Qdrant + Redis (copy to Mac mini and run `docker compose up -d`)

### Helper Scripts

**Verification:**
```bash
bash scripts/verify_day1.sh
```
→ Comprehensive check of all Day 1 prerequisites

**API Key Testing:**
```bash
bash scripts/test_api_keys.sh
```
→ Test all configured API keys

**Qdrant Initialization:**
```bash
python3 scripts/init_qdrant.py
```
→ Create vector database collection

**Script Documentation:**
```bash
open scripts/README.md
```
→ Full documentation of all helper scripts

---

## 📝 Day 1 Checklist

Use this checklist to track your Day 1 progress:

### Network (15 min)
- [ ] Assign Mac Studio static IP: 192.168.10.20
- [ ] Assign Mac mini static IP: 192.168.10.181
- [ ] Verify connectivity: `ping 192.168.10.181`
- [ ] Verify HA connectivity: `ping 192.168.10.168`

### Environment Setup (30 min)
- [ ] Install Homebrew (Mac Studio + Mac mini)
- [ ] Install Docker (Mac Studio + Mac mini)
- [ ] Install Python 3.11 (Mac Studio)
- [ ] Create virtual environment: `python3 -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`

### Ollama + Models (30 min)
- [ ] Install Ollama: `brew install ollama`
- [ ] Start Ollama: `ollama serve &`
- [ ] Pull small model: `ollama pull phi3:mini-q8` (~2.5GB)
- [ ] Pull medium model: `ollama pull llama3.1:8b-q4` (~4.7GB)
- [ ] Verify: `ollama list`

### Configuration (10 min)
- [ ] Copy .env template: `cp config/env/.env.template config/env/.env`
- [ ] Get HA long-lived token from https://192.168.10.168:8123
- [ ] Edit .env with HA token
- [ ] Edit .env with actual IPs (if different from plan)

### Mac mini Services (15 min)
- [ ] Copy docker-compose to Mac mini
- [ ] SSH to Mac mini: `ssh user@192.168.10.181`
- [ ] Deploy services: `cd ~/athena/mac-mini && docker compose up -d`
- [ ] Verify Qdrant: `curl http://192.168.10.181:6333/healthz`
- [ ] Verify Redis: `redis-cli -h 192.168.10.181 PING`

### Qdrant Initialization (5 min)
- [ ] Install qdrant-client: `pip install qdrant-client`
- [ ] Run init script: `python3 scripts/init_qdrant.py`
- [ ] Verify collection created

### API Keys (Ongoing)
- [ ] Get OpenWeatherMap key TODAY
- [ ] Test weather key: `bash scripts/test_api_keys.sh`
- [ ] Get FlightAware key this week
- [ ] Get TheSportsDB key this week

### Verification
- [ ] Run comprehensive check: `bash scripts/verify_day1.sh`
- [ ] All checks passing (or only warnings)

---

## 🆘 If You Get Stuck

### Day 1 Issues

**Docker won't start:**
```bash
# Check if running
ps aux | grep Docker

# Restart
killall Docker
open /Applications/Docker.app
```

**Can't reach Mac mini:**
```bash
# Check firewall on Mac mini
# System Settings → Network → Firewall
# Add exceptions for ports 6333, 6379 or disable firewall
```

**Ollama models won't download:**
```bash
# Check disk space
df -h

# Models need:
# - phi3:mini-q8: ~2.5GB
# - llama3.1:8b-q4: ~4.7GB
```

**Qdrant won't connect:**
```bash
# Check Docker logs
docker logs qdrant

# Verify port not in use
lsof -i :6333

# Restart container
docker restart qdrant
```

### Getting Help

1. **Check troubleshooting sections:**
   - `docs/DAY_1_QUICK_START.md` - Day 1 specific issues
   - `scripts/README.md` - Script-related issues

2. **Run diagnostics:**
   ```bash
   bash scripts/verify_day1.sh
   ```

3. **Ask Claude Code for help:**
   - Describe the specific error you're seeing
   - Include any error messages or logs
   - Mention which step you're on

---

## 📊 Timeline Overview

**Day 1 (TODAY):** Environment setup - **2-3 hours**
- [ ] Network, Docker, Ollama, .env, Mac mini services, Qdrant

**Week 1:** Repository restructuring + Gateway deployment - **6-8 hours**
- [ ] Create apps/ directory structure
- [ ] Deploy LiteLLM gateway
- [ ] Test first OpenAI-compatible call

**Week 2-3:** RAG services + Orchestrator - **10-12 hours**
- [ ] Migrate weather, airports, sports handlers
- [ ] Implement LangGraph orchestrator
- [ ] Test classification and routing

**Week 4:** Mac mini final setup + Monitoring - **4-6 hours**
- [ ] Optimize Qdrant and Redis
- [ ] Add Prometheus metrics
- [ ] Performance testing

**Week 5:** HA integration - **6-8 hours**
- [ ] Configure Wyoming protocol
- [ ] Create Assist Pipelines
- [ ] Test voice devices

**Week 6:** Integration testing + Documentation - **4-6 hours**
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Documentation updates

**Total:** 4-6 weeks to complete Phase 1

---

## 🎉 Success Criteria

### Day 1 Complete When:
- ✅ Both Macs have static IPs and can reach each other
- ✅ Docker running on both Macs
- ✅ Ollama running with 2 models downloaded
- ✅ .env file created with HA token
- ✅ Qdrant + Redis running on Mac mini
- ✅ At least OpenWeatherMap API key obtained

### Phase 1 Complete When:
- ✅ Voice command "what's the weather" returns accurate response
- ✅ Control pipeline handles device commands (< 3.5s P95)
- ✅ Knowledge pipeline handles complex queries (< 5.5s P95)
- ✅ RAG services operational (weather, airports, sports)
- ✅ Both HA Voice devices functional
- ✅ Metrics and monitoring operational

---

## 🚦 What's Next After Day 1?

Once Day 1 is complete:

1. **Verify everything works:**
   ```bash
   bash scripts/verify_day1.sh
   ```

2. **Choose your path:**
   - **Fast track:** Follow `docs/DAY_1_QUICK_START.md` into Week 1
   - **Comprehensive:** Use `/implement_plan` with bootstrap guide
   - **Weekly milestones:** Follow Phase 1 plan week-by-week

3. **Start Week 1:**
   - Create `apps/` directory structure
   - Deploy LiteLLM gateway
   - Test first OpenAI-compatible API call

---

## 📚 Additional Resources

**Architecture Documentation:**
- `docs/ARCHITECTURE.md` - System architecture and design decisions

**Research Documents:**
- `thoughts/shared/research/2025-11-11-complete-architecture-pivot.md` - Architecture rationale

**Related Plans:**
- Guest Mode + Quality Tracking (Phase 2)
- Admin Interface (Phase 3)
- Kubernetes Deployment (Open Source)
- Haystack/RAG Eval/DVC Integration (Production)

**External Documentation:**
- Ollama: https://ollama.ai/
- LiteLLM: https://docs.litellm.ai/
- LangGraph: https://python.langchain.com/docs/langgraph
- Qdrant: https://qdrant.tech/documentation/
- Home Assistant: https://www.home-assistant.io/

---

## ✨ Let's Begin!

You're ready to start! Here's your immediate next action:

```bash
# 1. Open Day 1 guide
open docs/DAY_1_QUICK_START.md

# 2. Start with network configuration
# Assign Mac Studio: 192.168.10.20
# Assign Mac mini: 192.168.10.181

# 3. Follow the guide step-by-step

# 4. Verify when done
bash scripts/verify_day1.sh
```

**Welcome to Project Athena - Let's build something amazing! 🚀**
