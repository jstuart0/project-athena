# Complete Architecture Pivot - Project Athena
**Date:** 2025-11-11
**Status:** New Direction - Replaces Previous Implementation

## Executive Summary

Project Athena is undergoing a **complete architectural redesign**. The previous Jetson-based implementation (Athena Lite) is now **deprecated**. The new direction focuses on:

1. **Mac Studio M4/64GB + Mac mini M4/16GB** as primary compute (replacing Jetson cluster)
2. **Dual-pipeline architecture** (Control vs Knowledge) via Home Assistant Assist Pipelines
3. **LangGraph-based orchestration** with advanced RAG, anti-hallucination, and cross-model validation
4. **Guest-focused Airbnb experience** (Baltimore property @ 912 South Clinton St)
5. **Open-source deployable project** + opinionated Baltimore implementation

**Related Plans:**
- [Guest Mode & Quality Tracking](../plans/2025-11-11-guest-mode-and-quality-tracking.md)
- [Admin Interface Specification](../plans/2025-11-11-admin-interface-specification.md)
- [Kubernetes Deployment Strategy](../plans/2025-11-11-kubernetes-deployment-strategy.md)
- [Haystack, RAG Eval & DVC Integration](../plans/2025-11-11-haystack-rageval-dvc-integration.md)

## What Changed: Before vs After

### Previous Architecture (DEPRECATED)

```
┌─────────────────────────────────────────────────────────┐
│                 Athena Lite (Jetson)                    │
├─────────────────────────────────────────────────────────┤
│ Jetson Orin Nano Super (192.168.10.62)                 │
│   ├─> OpenWakeWord (Jarvis + Athena)                   │
│   ├─> Faster-Whisper (STT)                             │
│   ├─> Piper TTS                                        │
│   ├─> Voice Activity Detection                          │
│   └─> Home Assistant API Integration                    │
├─────────────────────────────────────────────────────────┤
│ Home Assistant (192.168.10.168)                        │
│   └─> Device Control & State Management                 │
└─────────────────────────────────────────────────────────┘

Plan: Scale to Wyoming devices + Proxmox services
```

### New Architecture (ACTIVE)

```
┌─────────────────────────────────────────────────────────────────┐
│                    HA Voice Preview Devices                     │
│  (Wyoming satellites in each room: dual wake words Jarvis/Athena)│
├─────────────────────────────────────────────────────────────────┤
│           Home Assistant @ 192.168.10.168 (Proxmox)            │
│  ├─> Assist Pipeline 1: CONTROL (Local)                        │
│  │    STT: Wyoming Whisper → Agent: Home Assistant → TTS: Piper│
│  └─> Assist Pipeline 2: KNOWLEDGE (LLM)                        │
│       STT: Wyoming Whisper → Agent: OpenAI Conversation → Piper │
│                              ↓                                   │
│                       Points to gateway @                       │
│                       192.168.10.20:8000                        │
├─────────────────────────────────────────────────────────────────┤
│              Mac Studio M4/64GB @ 192.168.10.20                 │
│  ├─> OpenAI-compatible Gateway (LiteLLM/proxy)                 │
│  ├─> LangGraph Orchestrator                                    │
│  │    ├─> Classifier (control vs info vs complex)              │
│  │    ├─> Router (small/medium/large model selection)          │
│  │    ├─> RAG Retrieval (multi-source)                         │
│  │    ├─> Validators (policy + retrieval + cross-model)        │
│  │    └─> Share Service (Twilio SMS + Email)                   │
│  ├─> Local LLMs (Ollama/vLLM/llama.cpp)                        │
│  │    ├─> Classifier: tiny/fast (3-4B)                          │
│  │    ├─> Command LLM: (3-4B) for HA semantics                 │
│  │    ├─> Reasoner: (7-8B) for complex + RAG                   │
│  │    └─> Fallback: (13B optional) for deep reasoning          │
│  ├─> Embeddings (sentence transformers/bge)                    │
│  ├─> RAG Connectors                                            │
│  │    ├─> Weather (Baltimore, Open-Meteo/NWS)                  │
│  │    ├─> News (RSS/NewsAPI - local + national)                │
│  │    ├─> Events (Ticketmaster/Meetup/Eventbrite)              │
│  │    ├─> Transport (MTA MD/Transitland)                       │
│  │    ├─> Airports (PHL,BWI,EWR,LGA,JFK,IAD,DCA + flights)    │
│  │    ├─> Sports (all major leagues + local favorites)         │
│  │    ├─> Recipes (Spoonacular + pantry suggestions)           │
│  │    ├─> Streaming (Prime,Netflix,Disney+,Paramount+,         │
│  │    │              Peacock,YouTube TV,Hulu,NFL Sunday Ticket)│
│  │    └─> Dining (Yelp/Places - nearby with distance/time)     │
│  └─> Share Service (Twilio + SMTP/SendGrid)                    │
├─────────────────────────────────────────────────────────────────┤
│              Mac mini M4/16GB @ 192.168.10.181                   │
│  ├─> Vector DB (Qdrant/Weaviate/Chroma)                        │
│  ├─> Job Queue (RQ/Celery) + Cache (Redis)                     │
│  └─> Monitoring Sidecar + Log Aggregation                      │
├─────────────────────────────────────────────────────────────────┤
│                         Observability                           │
│  └─> Prometheus/Grafana (existing infrastructure)              │
└─────────────────────────────────────────────────────────────────┘
```

## New Product Vision

**Goal:** A privacy-first, multi-zone, voice-controlled home assistant with:

1. **Dual wake words** ("Jarvis", "Athena")
2. **Fast local control** (≤2.5s p95 for simple commands)
3. **Powerful RAG** for real-time information (≤4.0s p95)
4. **Anti-hallucination** + cross-model validation
5. **Guest-friendly UX** (Airbnb Baltimore property)
6. **SMS/email share-outs** (directions, recipes, recommendations)
7. **Automatic Guest Mode** with Airbnb calendar integration
8. **Permission scoping** (guest vs owner with configurable allowlists)
9. **Quality tracking** with feedback loops for continuous improvement
10. **Real-time Admin Interface** for configuration, monitoring, and operations

**📋 DETAILED PLANS:**
- [Guest Mode & Quality Tracking](../plans/2025-11-11-guest-mode-and-quality-tracking.md)
- [Admin Interface Specification](../plans/2025-11-11-admin-interface-specification.md)

### Key Differentiators

**Dual Pipeline Approach:**
- **Control (Local):** HA native agent for device control (lights, scenes, climate)
- **Knowledge (LLM):** LangGraph-powered for questions, RAG, complex reasoning

**Tiered Model Strategy:**
- Small/fast (3-4B): Intent routing, simple queries
- Medium (7-8B): Complex reasoning + RAG synthesis
- Large (13B optional): Deep multi-hop reasoning when needed

**Anti-Hallucination System:**
- Policy guard (block unsafe, escalate gracefully)
- Retrieval confidence thresholds
- Constrained function calls (schema + allowlist)
- Cross-model validation (quorum vote on high-stakes queries)

**Context Awareness:**
- Room location + occupancy tracking
- Property address (912 South Clinton St, Baltimore, MD 21224)
- Time/date context
- Guest mode (no PII retention, limited memory)
- Owner mode (future: voice profiles, preferences)

**Real-Time Information:**
- Weather (Baltimore + 48hr cache)
- News (local + national, hourly refresh)
- Events (Baltimore area, daily refresh)
- Transport (MTA MD + rideshare estimates)
- Airports (7 nearby: PHL, BWI, EWR, LGA, JFK, IAD, DCA)
- Flights (basic lookup by airline/flight#/status)
- Sports (all major leagues, local favorites: Orioles, Ravens)
- Recipes (pantry-style + "text me shopping list")
- Streaming availability (8 services with deep links)
- Dining (nearby with distance/time, 24h cache)

**Share Capabilities:**
- Twilio SMS for quick info (directions, tickets, recipes)
- Email (SMTP/SendGrid) for detailed answers
- Guest contact stored transiently, purged on checkout

## What's Still Relevant from Old Implementation

### Keep/Adapt:
1. **Home Assistant integration** - Still core, but different approach (Assist Pipelines)
2. **Dual wake words** (Jarvis/Athena) - Preserved in new design
3. **Wyoming protocol** - Still used for STT/TTS (Faster-Whisper/Piper as HA add-ons)
4. **Multi-zone concept** - Still present (10 zones via Wyoming satellites)
5. **Privacy focus** - Enhanced with guest mode and data retention policies
6. **Fast response times** - Target refined (≤2.5s control, ≤4.0s knowledge)
7. **Local processing** - Enhanced (Mac Studio vs Jetson, but still local-first)

### Discard:
1. **Jetson-based architecture** - Hardware replaced by Mac Studio/mini
2. **Athena Lite implementation** - Proof-of-concept deprecated
3. **Proxmox-hosted voice services** - Moved to Mac Studio
4. **Simple STT→LLM→TTS pipeline** - Replaced by sophisticated LangGraph orchestration
5. **Phase 0-4 deployment plan** - New implementation phases below

## Network Configuration Changes

### Old IPs (Deprecated):
- 192.168.10.62 - jetson-01 (Athena Lite) ❌
- 192.168.10.63 - jetson-02 (planned) ❌
- 192.168.10.71-80 - Wyoming devices (planned) ❌

### New IPs (Active):
- **192.168.10.168** - Home Assistant (Proxmox VM) ✅ **SAME IP**
- **192.168.10.20** - Mac Studio M4/64GB (gateway, orchestrator, models)
- **192.168.10.181** - Mac mini M4/16GB (vector DB, cache, monitoring)
- **192.168.10.50-59** - HA Voice preview devices (Wyoming satellites)
- Existing Prometheus/Grafana infrastructure (no new IPs)

## Hardware Changes

### Deprecated:
- ❌ NVIDIA Jetson Orin Nano Super (2 units)
- ❌ Proxmox VMs for voice services
- ❌ Generic Wyoming voice devices

### New:
- ✅ Mac Studio M4 (64GB RAM) - Primary brains
- ✅ Mac mini M4 (16GB RAM) - Auxiliary services
- ✅ HA Voice preview devices - One per room (PoE powered)
- ✅ Proxmox VM for Home Assistant only (same IP: 192.168.10.168)

## Implementation Approach

### Two Deliverables:

1. **Open-Source Deployable Project** (Generic)
   - Configurable, no hardcoded location/API keys
   - Docker Compose + Helm charts
   - Pluggable RAG sources
   - MIT/Apache-2.0 license
   - Complete documentation

2. **Baltimore Airbnb Implementation** (Opinionated)
   - Pre-configured for 912 South Clinton St
   - Baltimore-centric RAG sources enabled
   - Guest mode default ON
   - Twilio/SMTP configured
   - Monitoring integrated to existing Grafana

### Repository Structure (New)

```
project-athena/
├── apps/
│   ├── gateway/                  # OpenAI-compatible API
│   ├── langgraph_orchestrator/   # Graph: classify→route→tools→guard
│   ├── rag/                      # Connectors, embeddings, indices
│   ├── validators/               # Anti-hallucination + cross-model vote
│   ├── ha_bridge/                # Optional: advanced HA actions
│   ├── share/                    # Twilio/SMS/email services
│   └── webui/                    # Status UI (health, logs)
├── charts/                       # Helm (optional)
├── deploy/
│   ├── docker/                   # Dockerfiles
│   ├── compose/                  # docker-compose.*.yml
│   └── k8s/                      # manifests (optional)
├── infra/
│   ├── grafana_dashboards/
│   └── prom_rules/
├── docs/
│   ├── quickstart.md
│   ├── config.md
│   ├── ha_integration.md
│   ├── pipelines.md
│   ├── rag_sources.md
│   ├── guardrails.md
│   ├── dev_guide.md
│   ├── ops_runbook.md
│   └── contribution.md
├── scripts/
│   ├── bootstrap.sh
│   ├── seed_vectors.py
│   └── smoke_test.sh
├── licenses/
│   └── THIRD_PARTY.md
├── .env.example
├── LICENSE
└── README.md
```

## New Implementation Phases

### Phase 0: HA Migration (Same as Before)
- HA VM @ 192.168.10.168 (restore backup)
- Add Faster-Whisper + Piper add-ons (Wyoming)
- Create **Control** and **Knowledge** pipelines
- Add OpenAI Conversation (point to placeholder gateway)

**Done when:** HA working, voice satellites test OK (TTS/STT loopback)

### Phase 1: Core Services (Mac Studio + Mac mini)

**Mac Studio (192.168.10.20):**
- OpenAI-compatible gateway (LiteLLM/proxy)
- LangGraph orchestrator
- Local models (Ollama/vLLM: small, medium, large)
- RAG services (embeddings + connectors)
- Validators (policy + retrieval + cross-model)
- Twilio/SMS + email integration
- Wire OpenAI Conversation (HA) → gateway

**Mac mini (192.168.10.181):**
- Vector DB (Qdrant/Weaviate)
- Job queue (RQ/Celery) + cache (Redis)
- Monitoring exporter

**Validation:**
- `curl` → `/v1/chat/completions` returns answers
- HA "Knowledge" pipeline produces real answers via satellites
- Cross-model validation works on high-stakes prompts

### Phase 2: Location, Learning & Guest UX
- Occupancy mapping (Dining = audio-only)
- Property context (Baltimore address + hotspots)
- Guest flow: "text me this" end-to-end
- Caching + freshness labels
- Real-time categories: airports/sports/streaming with citations

### Phase 3: Optimization & Polish
- Latency tuning (model size/quant, prompt optimization, caching)
- Add more streaming providers/favorites
- Scene macros ("movie night")
- Voice ID (owner mode) optional later

## LangGraph Orchestrator Details

### Node Flow:
```
classify → route_control / route_info → retrieve → synthesize → validate → share_opt → finalize
```

### Nodes:

1. **classify:** Determine control vs info vs complex; attach room, guest_mode, location
2. **route_control:** If "control", handoff to HA (or call HA API for multi-step scenes)
3. **route_info:** Select small/medium/large model by complexity + token estimate
4. **retrieve:** Fetch category data (weather/news/events/etc.); merge with property context
5. **synthesize:** Compose answer with sources + freshness tags
6. **validate:** Run policy guard, retrieval guard; if needed, cross_model_vote
7. **share_opt:** If user requested, enqueue Twilio/email job
8. **finalize:** Return JSON `{answer, citations, used_models, validation}`

### Configuration:
- Latency budget thresholds
- Token count limits
- Complexity scoring
- Category routing map
- Per-category freshness TTLs
- Web domain allowlist

### Telemetry:
- Per-node latency + failures
- Category hit rate
- RAG coverage percentage
- Validation pass rate
- Cross-model usage percentage

## Security & Privacy

**Guest Mode (Default):**
- No long-term memory
- Redact PII
- Purge SMS/email logs after stay
- Limited memory retention

**Owner Mode (Future):**
- Longer memory
- Preference learning
- Voice profile identification

**Security Measures:**
- Secrets in macOS Keychain or encrypted `.env`
- Vector DB entries with TTLs (auto-GC)
- Tool allowlists + strict schemas
- HTTP client blocks unknown domains
- mTLS on internal APIs (or API keys + IP allowlists)
- Sandboxed tools with explicit function schemas

## Monitoring & SLOs

### Golden Signals:
- Voice E2E simple control: **≤2.5s p95**
- Knowledge answers: **≤4.0s p95** (cross-model adds ~0.7-1.2s)
- STT/TTS each: **≤0.8s p95**
- Success rate: **≥90%** first-try commands; **≥85%** info queries with high-confidence retrieval

### Dashboards:
- Per-stage latency breakdown
- Model usage distribution
- RAG coverage percentage
- Validator pass rates
- Wake-word counts (Jarvis vs Athena)
- Satellite health
- HA API status

### Alerts:
- Pipeline down
- Latency exceeds targets
- Success below thresholds
- Connector failures
- Vector DB errors

## RAG Sources (Baltimore Defaults)

All sources have configurable providers, TTLs, and freshness labels:

| Category | Provider | Refresh | Baltimore Config |
|----------|----------|---------|-----------------|
| Weather | Open-Meteo/NWS | 48h cache | Baltimore coords |
| News | RSS/NewsAPI | Hourly | Local + national |
| Events | Ticketmaster/Meetup | Daily | Baltimore area |
| Transport | MTA MD/Transitland | Real-time | Baltimore region |
| Airports | cirium/aviationstack | Real-time | PHL,BWI,EWR,LGA,JFK,IAD,DCA |
| Flights | Airport APIs | Real-time | Same 7 airports |
| Sports | TheSportsDB/ESPN | Real-time | All leagues + Orioles/Ravens |
| Recipes | Spoonacular | Static/search | Pantry + shopping lists |
| Streaming | JustWatch/TMDB | Daily | 8 services with deep links |
| Dining | Yelp/Places | 24h cache | Nearby with distance/time |

## Cross-Model Validation Strategy

**When to Use:**
- High-stakes domains (travel timing, airport gates, live scores)
- Low retrieval confidence
- Conflicting sources detected

**Process:**
1. Generate N=3 paraphrased prompts (semantic diversity)
2. Query 2-3 diverse instruction models
3. Accept if ≥2 agree (cosine similarity threshold)
4. Else: hedge response "I found conflicting info; here are the sources..."

**Models:**
- Use diverse model families (e.g., Llama + Mistral + Phi)
- Small models OK for validation (speed matters)
- Rate-limit during peak times

## Next Steps

1. **Archive old implementation:** Move `athena-lite/` and old docs to `deprecated/`
2. **Create new directory structure:** As outlined above
3. **Start with Phase 0:** HA migration (already planned, keep same approach)
4. **Build gateway + orchestrator:** Core LangGraph implementation
5. **Deploy to Mac Studio:** Docker Compose with Metal acceleration
6. **Integrate vector DB:** Mac mini setup
7. **Wire HA pipelines:** Connect OpenAI Conversation to gateway
8. **Test end-to-end:** Simple command → control, complex question → knowledge
9. **Add RAG sources:** One category at a time (weather first)
10. **Implement validators:** Policy + retrieval + cross-model
11. **Add share services:** Twilio + email
12. **Deploy monitoring:** Grafana dashboards
13. **Optimize latency:** Model quant, caching, prompt tuning
14. **Document for open-source:** Generic configs, docs, examples

## Open Questions

1. **Hardware availability:** Mac Studio M4/64GB + Mac mini M4/16GB - need to confirm purchase/delivery timeline
2. **HA Voice preview devices:** Availability and ordering process - are these production-ready?
3. **Wyoming satellite setup:** PoE network ports available in all 10 rooms?
4. **API keys needed:** Full list for all RAG sources (weather, news, events, airports, flights, sports, recipes, streaming, dining)
5. **Twilio account:** Setup and phone number acquisition
6. **SMTP/SendGrid:** Email configuration and sender verification
7. **Guest mode triggers:** How to automatically enable/disable based on Airbnb booking calendar?
8. **License choice:** MIT or Apache-2.0 for open-source release?
9. **Model selection:** Specific models for small/medium/large tiers (Phi-3, Llama-3.1, Mistral variants)?
10. **Vector DB choice:** Qdrant vs Weaviate vs Chroma - which fits best on Mac mini?

## Migration Path for Existing Work

**Athena Lite (Jetson implementation):**
- Status: **DEPRECATED**
- Location: Currently at `/mnt/nvme/athena-lite/` on jetson-01
- Action: Archive code and docs to `deprecated/athena-lite/`
- Learnings to keep:
  - Wake word optimization insights
  - STT/TTS performance benchmarks
  - Home Assistant API integration patterns
  - Voice pipeline latency measurements

**Old deployment plans:**
- Phase 0: Keep same HA migration approach ✅
- Phase 1-4: Replace with new phases above ❌

**Hardware:**
- Jetson units: Repurpose for other projects or keep as backup
- Wyoming devices (not ordered yet): Cancel if generic; order HA Voice preview devices instead

**Network:**
- HA IP (192.168.10.168): Keep same ✅
- Gateway IP (192.168.10.20): New allocation for Mac Studio ✅
- Vector DB IP (192.168.10.181): New allocation for Mac mini ✅
- Satellite IPs (192.168.10.50-59): New range ✅

## Success Criteria

**Phase 1 Complete When:**
- Gateway responds to `/v1/chat/completions`
- LangGraph orchestrator routes queries correctly
- Small + medium models inference locally
- HA "Knowledge" pipeline returns real answers
- Basic RAG working (weather at minimum)
- Latency: control ≤3.5s, knowledge ≤5.5s (pre-optimization)

**Phase 2 Complete When:**
- All RAG categories enabled and tested
- Guest mode enforced (no PII retention)
- SMS/email sharing works end-to-end
- Cross-model validation tested on high-stakes queries
- Latency: control ≤2.5s, knowledge ≤4.0s (optimized)

**Phase 3 Complete When:**
- Success rates: ≥90% control, ≥85% info
- Monitoring dashboards live in Grafana
- Documentation complete for open-source release
- Baltimore implementation deployed and guest-tested
- Owner mode (voice ID) optional feature available

---

## Conclusion

This is a **complete architectural reboot** of Project Athena. The previous Jetson-based implementation served its purpose as a proof-of-concept but is now deprecated in favor of a far more sophisticated, scalable, and feature-rich architecture centered on Mac Studio/mini hardware and LangGraph orchestration.

**Key takeaway:** We're building two things simultaneously:
1. A generic, open-source voice assistant platform
2. A production-ready Airbnb guest experience for the Baltimore property

The new design prioritizes guest UX, real-time information accuracy, anti-hallucination, and seamless integration with existing Home Assistant infrastructure while maintaining the privacy-first, local-processing philosophy of the original vision.

**Next immediate action:** Archive old work, create new directory structure, begin Phase 0 (HA migration).
