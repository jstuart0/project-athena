# CLAUDE.md - Project Athena

This file provides guidance to Claude Code (claude.ai/code) when working with Project Athena - the AI voice assistant system.

## 📚 Reference Documentation

**This CLAUDE.md coordinates Project Athena development. Related documentation:**

- **[Homelab Infrastructure CLAUDE.md](../kubernetes/k8s-home-lab/CLAUDE.md)** - Infrastructure commands and credentials
- **[Project Athena Wiki](https://wiki.xmojo.net/homelab/projects/project-athena)** - Complete project documentation
- **[Architecture Documentation](docs/ARCHITECTURE.md)** - Athena system architecture and design
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Phase-by-phase deployment instructions

## Project Overview

**Project Athena** is a next-generation AI voice assistant system designed for complete smart home integration. Unlike commercial assistants (Alexa, Google Home), Athena prioritizes privacy, speed, and local processing while delivering advanced AI capabilities.

### Core Goals

- **Fast Response Times:** Target 2-5 second end-to-end response
- **100% Local Processing:** All AI inference runs on local hardware - zero cloud dependencies
- **Privacy-Focused:** No data leaves your network
- **Dual Wake Words:** "Jarvis" for quick commands, "Athena" for complex reasoning
- **RAG Capabilities:** Access to live data sources, documentation, and contextual knowledge
- **Multi-Zone Coverage:** 10 zones throughout the entire home

## ⚠️ CRITICAL: Project Boundaries

**This repository is ONLY for Project Athena voice assistant system.**

### What Belongs Here

**Project Athena Components:**
- ✅ Wake word detection (OpenWakeWord on Jetson)
- ✅ Speech-to-Text (Faster-Whisper)
- ✅ Text-to-Speech (Piper TTS)
- ✅ Large Language Models (Phi-3, Llama-3.1)
- ✅ RAG system (vector database, knowledge retrieval)
- ✅ Wyoming protocol integration
- ✅ Home Assistant voice integration
- ✅ Multi-zone voice devices
- ✅ Orchestration and coordination services

**Deployment Artifacts:**
- ✅ Kubernetes manifests for Athena services
- ✅ Jetson configuration and setup scripts
- ✅ Wyoming device configurations
- ✅ Model management and storage
- ✅ Monitoring and observability
- ✅ Backup and recovery procedures

### What Does NOT Belong Here

**Infrastructure Services:**
- ❌ Homelab infrastructure (lives in `/Users/jaystuart/dev/kubernetes/k8s-home-lab/`)
- ❌ Kubernetes cluster management
- ❌ Network configuration (handled by homelab infrastructure)
- ❌ SSL certificates, DNS, ingress (handled by homelab)

**Other Projects:**
- ❌ Smart Benefit Wallet application (lives in `/Users/jaystuart/dev/Monarch/`)
- ❌ General homelab services
- ❌ Non-voice assistant applications

**Directory Reference:**
- **Project Athena**: `/Users/jaystuart/dev/project-athena/` (this repository)
- **Homelab Infrastructure**: `/Users/jaystuart/dev/kubernetes/k8s-home-lab/` (infrastructure)
- **Smart Benefit Wallet**: `/Users/jaystuart/dev/Monarch/` (separate application)

## Current Implementation Status

### ✅ Completed Components

**Athena Lite (Proof-of-Concept):**
- **Location:** `/mnt/nvme/athena-lite/` on jetson-01 (192.168.10.62)
- **Status:** 90% complete, ready for testing
- **Features:** Dual wake words, optimized response times (2.5-5s), local processing

**Infrastructure Integration:**
- **Home Assistant:** Accessible at https://ha.xmojo.net
- **API Token:** Stored in thor cluster (`automation/home-assistant-credentials`)
- **Network:** Jetson accessible at 192.168.10.62
- **Integration:** Athena Lite configured to use HA's conversation API

### ⏸️ Pending Components

**Phase 0:** Home Assistant migration to Proxmox (not started)
**Phase 1:** Wyoming protocol integration (planned)
**Phase 2:** Full 10-zone deployment (planned)

## Architecture Overview

### Current Architecture (Athena Lite)
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
```

### Planned Architecture (Full Project Athena)
```
┌─────────────────────────────────────────────────────────┐
│                  Wyoming Devices                        │
│  (10 zones: Office, Kitchen, Bedrooms, etc.)           │
├─────────────────────────────────────────────────────────┤
│ Jetson Cluster (Wake Word + Routing)                   │
│   ├─> jetson-01 (192.168.10.62) - Wake word detection │
│   └─> jetson-02 (192.168.10.63) - Load balancing      │
├─────────────────────────────────────────────────────────┤
│ Proxmox Cluster Services (thor)                        │
│   ├─> athena-stt (Faster-Whisper)                      │
│   ├─> athena-tts (Piper TTS)                           │
│   ├─> athena-intent (Intent Classification)            │
│   ├─> athena-command (LLM Processing)                  │
│   ├─> athena-rag (Knowledge Retrieval)                 │
│   └─> athena-orchestration (Coordination)              │
├─────────────────────────────────────────────────────────┤
│ Home Assistant (Wyoming Integration)                   │
│   └─> Device Control & Automation Hub                  │
└─────────────────────────────────────────────────────────┘
```

## Network Configuration

### Key Athena IPs

**Jetson Devices:**
- 192.168.10.62 - jetson-01 (Athena Lite, wake word detection)
- 192.168.10.63 - jetson-02 (planned, load balancing)

**Home Assistant:**
- https://ha.xmojo.net - Home Assistant (domain-based access)

**Planned Wyoming Devices:**
- 192.168.10.71-80 - Wyoming voice devices (10 zones)

**Proxmox Services (thor cluster):**
- 192.168.10.11-13 - Proxmox nodes hosting Athena services
- 192.168.10.222 - Kubernetes API Server

**Storage:**
- 192.168.10.159 - Synology DS1821+ (model storage, backups)

### Zone Coverage Plan

The system will provide complete home coverage across these zones:

1. **Office** - Primary testing zone, high-traffic
2. **Kitchen** - Cooking assistance, noisy environment testing
3. **Living Room** - Entertainment control, general queries
4. **Master Bedroom** - Sleep routines, climate control
5. **Master Bath** - Morning routines, music
6. **Main Bath** - Guest use, basic commands
7. **Alpha (Guest Bedroom 1)** - Guest-friendly commands
8. **Beta (Guest Bedroom 2)** - Guest-friendly commands
9. **Basement Bathroom** - Basic commands
10. **Dining Room** - Meal-time assistance, music

## Credentials and Access

### Home Assistant Integration

```bash
# Get Home Assistant API token (stored in thor cluster)
kubectl config use-context thor
kubectl -n automation get secret home-assistant-credentials -o jsonpath='{.data.long-lived-token}' | base64 -d

# Get HA instance URL
kubectl -n automation get secret home-assistant-credentials -o jsonpath='{.data.instance-url}' | base64 -d
# Output: https://192.168.10.168:8123
```

### Jetson Access

**Primary Device:** jetson-01 (192.168.10.62)
- **SSH Access:** `ssh jstuart@192.168.10.62` (passwordless access configured)
- **Project Location:** `/mnt/nvme/athena-lite/`
- **Storage:** 1.8TB NVMe for AI models and data
- **Models:** Jarvis + Athena wake words, Whisper tiny.en (73MB)
- **Status:** Athena Lite implementation ready for testing

### Infrastructure Credentials

**For homelab infrastructure access:** See `/Users/jaystuart/dev/kubernetes/k8s-home-lab/CLAUDE.md`

**Home Assistant Server Access:**
```bash
# SSH to HA server (requires specific key)
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168

# HA config location: /config/
# Purpose: Modify HA configuration for Jetson LLM integration
```

**Quick infrastructure commands:**
```bash
# Switch to thor cluster
kubectl config use-context thor

# Check cluster status
kubectl get nodes

# View all credentials
kubectl -n automation get secrets

# Get HA server SSH credentials (stored in thor)
kubectl -n automation get secret ha-server-ssh-key -o yaml
```

## Development Phases

### Phase 0: Home Assistant Migration

**Status:** ⏸️ Not Started
**Goal:** Move Home Assistant from current hardware to Proxmox VM

**Key Tasks:**
- [ ] Create Proxmox VM for Home Assistant
- [ ] Migrate HA configuration
- [ ] Verify all integrations work
- [ ] Configure Wyoming protocol support

### Phase 1: Core Voice Pipeline (3 Test Zones)

**Status:** 🔄 Partially Complete (Athena Lite ready)
**Goal:** Build complete voice pipeline in 3 zones

**Test Zones:** Office, Kitchen, Master Bedroom

**Key Tasks:**
- [x] Athena Lite proof-of-concept (90% complete)
- [ ] Order Wyoming Voice devices (3 units)
- [ ] Deploy Wyoming devices in test zones
- [ ] Configure multi-zone routing on Jetson
- [ ] Deploy Proxmox services (STT, TTS, LLM)
- [ ] Test end-to-end pipeline

### Phase 2: Full System + RAG (All 10 Zones)

**Status:** 📋 Planned
**Goal:** Scale to all zones and add advanced RAG capabilities

**Key Tasks:**
- [ ] Deploy remaining 7 Wyoming devices
- [ ] Configure second Jetson (jetson-02)
- [ ] Deploy RAG vector database
- [ ] Integrate multiple LLMs (Phi-3, Llama-3.1)
- [ ] Add context-aware responses

### Phase 3: Learning & Optimization

**Status:** 📋 Planned
**Goal:** Add learning capabilities and usage pattern optimization

### Phase 4: Voice Identification

**Status:** 📋 Planned
**Goal:** Multi-user voice profiles and personalized responses

## Technical Specifications

### Hardware Requirements

**Jetson Orin Nano Super:**
- **AI Performance:** 40 TOPS
- **RAM:** 8GB LPDDR5
- **Storage:** 1.8TB NVMe (models + data)
- **Network:** 1GbE connection

**Wyoming Voice Devices:**
- **Quantity:** 10 (one per zone)
- **Features:** Far-field microphones, speakers, PoE powered
- **Network:** Ethernet or WiFi connectivity

**Proxmox Cluster Resources:**
- **vCPU:** 28 total across services
- **RAM:** 52GB total across services
- **GPU:** Required for STT and LLM inference

### Software Stack

**AI Models:**
- **Wake Words:** OpenWakeWord (Jarvis + Athena)
- **STT:** Faster-Whisper (tiny.en optimized)
- **TTS:** Piper TTS (natural voice synthesis)
- **LLM:** Phi-3-mini (quick), Llama-3.1-8B (complex)

**Protocols:**
- **Wyoming Protocol:** Voice assistant communication
- **Home Assistant API:** Device control
- **WebSocket:** Real-time communication

## Repository Structure

```
project-athena/
├── CLAUDE.md                    # This file
├── README.md                    # Project overview
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # System architecture
│   ├── DEPLOYMENT.md            # Deployment procedures
│   └── TROUBLESHOOTING.md       # Common issues
├── config/                      # Configuration files
│   ├── zones.yaml               # Zone definitions
│   ├── models.yaml              # AI model configurations
│   └── network.yaml             # Network configuration
├── scripts/                     # Automation scripts
│   ├── jetson-setup.sh          # Jetson configuration
│   ├── model-download.sh        # Model management
│   └── deployment.sh            # Service deployment
├── manifests/                   # Kubernetes manifests
│   ├── athena-stt/              # Speech-to-Text service
│   ├── athena-tts/              # Text-to-Speech service
│   ├── athena-intent/           # Intent classification
│   ├── athena-command/          # LLM processing
│   ├── athena-rag/              # Knowledge retrieval
│   └── athena-orchestration/    # Coordination service
├── phase0/                      # Phase 0 implementation files
├── phase1/                      # Phase 1 implementation files
├── phase2/                      # Phase 2 implementation files
└── athena-lite/                 # Athena Lite documentation and configs
```

## Common Operations

### Test Athena Lite

```bash
# Check if Jetson is accessible
ping 192.168.10.62

# SSH to Jetson and check project
ssh jstuart@192.168.10.62 "ls -la /mnt/nvme/athena-lite/"

# Check Athena Lite status
ssh jstuart@192.168.10.62 "cd /mnt/nvme/athena-lite && python3 athena_lite.py --test"

# Access Home Assistant API
curl -k -H "Authorization: Bearer $(kubectl -n automation get secret home-assistant-credentials -o jsonpath='{.data.long-lived-token}' | base64 -d)" https://ha.xmojo.net/api/
```

### Deploy Athena Services

```bash
# Verify context
kubectl config current-context  # Should be "thor"

# Create Athena namespace
kubectl create namespace athena

# Deploy services
kubectl apply -f manifests/athena-orchestration/
kubectl apply -f manifests/athena-stt/
kubectl apply -f manifests/athena-tts/

# Check deployment status
kubectl -n athena get all
```

### Monitor System

```bash
# Check service health
kubectl -n athena get pods

# View logs
kubectl -n athena logs -f deployment/athena-orchestration

# Check resource usage
kubectl top pods -n athena
```

## Known Issues and Limitations

### Current Blockers

**Athena Lite Testing:**
- ⚠️ Jetson SSH access not configured
- ⚠️ Audio device testing needed
- ⚠️ End-to-end voice test pending

**Infrastructure Dependencies:**
- ⚠️ Phase 0 (HA migration) not started
- ⚠️ Wyoming devices not ordered
- ⚠️ Proxmox services not deployed

### Performance Considerations

**Response Time Optimization:**
- Current: 2.5-5 seconds (Athena Lite)
- Target: 2-3 seconds (full system)
- Critical path: Wake word → STT → LLM → TTS

**Resource Usage:**
- Jetson: ~60% capacity (single zone)
- Proxmox: TBD (needs testing)
- Network: Minimal bandwidth required

## Task Management

### Thoughts Directory

**Purpose:** Capture research, implementation plans, and decision-making process

**Location:** `thoughts/` directory in this repository

**Structure:**
```
thoughts/
├── shared/              # Version-controlled team documentation
│   ├── research/        # Technical investigations and findings
│   ├── plans/           # Implementation plans and specifications
│   ├── decisions/       # Architecture Decision Records (ADRs)
│   └── prs/             # Pull request summaries and analysis
├── local/               # Personal notes (gitignored)
└── searchable/          # Hard links for fast searching (gitignored)
```

**When to use thoughts directory:**

1. **Research documents** (`shared/research/`):
   - Document how components work
   - Findings from codebase exploration
   - Technical investigations
   - Naming: `RESEARCH_<topic>.md` or `YYYY-MM-DD-topic.md`

2. **Implementation plans** (`shared/plans/`):
   - Technical specifications before implementation
   - Step-by-step implementation plans
   - Success criteria and verification steps
   - Naming: `YYYY-MM-DD-feature-name.md`

3. **Architecture decisions** (`shared/decisions/`):
   - Major architectural choices
   - Alternatives considered
   - Trade-offs and consequences
   - Naming: `YYYY-MM-DD-decision-title.md`

4. **Personal notes** (`local/`):
   - Scratch notes during debugging
   - Personal TODO lists
   - Experimental ideas not ready to share

**Complete documentation:** See `thoughts/README.md` for full conventions

### Wiki Documentation

**Primary Documentation:** https://wiki.xmojo.net/homelab/projects/project-athena

**Update Wiki when:**
- Architecture changes
- New components deployed
- Performance benchmarks completed
- Issues discovered/resolved

### Plane Integration

**Instance:** https://plane.xmojo.net
**Project:** Use dedicated Athena project or "smartwallet-infrastructure" module

**Track progress for:**
- Phase completions
- Hardware orders
- Testing milestones
- Integration tasks

## Quick Reference Commands

### Infrastructure Access

```bash
# Switch to homelab infrastructure context
kubectl config use-context thor

# Get credentials
kubectl -n automation get secrets

# Check cluster health
kubectl get nodes
kubectl get pods -A
```

### Athena-Specific Commands

```bash
# Check Athena services
kubectl -n athena get all

# View Athena logs
kubectl -n athena logs -f -l app=athena-orchestration

# Test Home Assistant API
HA_TOKEN=$(kubectl -n automation get secret home-assistant-credentials -o jsonpath='{.data.long-lived-token}' | base64 -d)
curl -k -H "Authorization: Bearer $HA_TOKEN" https://192.168.10.168:8123/api/states | jq '.[] | select(.entity_id | contains("conversation"))'
```

### Network Testing

```bash
# Test Jetson connectivity
ping 192.168.10.62

# Test Home Assistant
curl -k https://192.168.10.168:8123/api/

# Check DNS resolution
nslookup wiki.xmojo.net
```

## Related Resources

**AI/ML Documentation:**
- OpenWakeWord: https://github.com/dscripka/openWakeWord
- Faster-Whisper: https://github.com/guillaumekln/faster-whisper
- Piper TTS: https://github.com/rhasspy/piper
- Wyoming Protocol: https://github.com/rhasspy/wyoming

**Home Automation:**
- Home Assistant: https://www.home-assistant.io/
- Home Assistant Voice: https://www.home-assistant.io/voice_control/

**Hardware Documentation:**
- NVIDIA Jetson: https://developer.nvidia.com/embedded/jetson-orin-nano-super-developer-kit
- JetPack SDK: https://developer.nvidia.com/embedded/jetpack

**Infrastructure (for reference):**
- Homelab CLAUDE.md: `/Users/jaystuart/dev/kubernetes/k8s-home-lab/CLAUDE.md`
- Kubernetes: https://kubernetes.io/docs/
- Proxmox: https://pve.proxmox.com/pve-docs/

---

**Last Updated:** November 3, 2025
**Maintained By:** Jay Stuart
**Repository:** `/Users/jaystuart/dev/project-athena/`
**Related Infrastructure:** `/Users/jaystuart/dev/kubernetes/k8s-home-lab/`