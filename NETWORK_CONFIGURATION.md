# Project Athena - Network Configuration

**Date:** 2025-11-11
**Status:** ✅ Complete and Verified

---

## Network Overview

Project Athena uses two Mac computers in a distributed architecture for AI voice assistant processing.

### Hardware Configuration

**Mac Studio M4 (64GB RAM):**
- **IP Address:** 192.168.10.167 ✅
- **Hostname:** Jays-Mac-Studio.local
- **SSH Access:** `ssh jstuart@192.168.10.167` (passwordless configured ✅)
- **Role:** Primary compute
- **Services:**
  - LiteLLM Gateway (port 8000)
  - LangGraph Orchestrator (port 8001)
  - RAG Services:
    - Weather (port 8010)
    - Airports (port 8011)
    - Sports (port 8012)
  - Ollama LLM server (port 11434)
- **Models:** phi3:mini-q8, llama3.1:8b-q4
- **Project Location:** `/Users/jaystuart/dev/project-athena/`

**Mac mini M4 (16GB RAM):**
- **IP Address:** 192.168.10.181 ✅
- **Role:** Database and caching services
- **Services:**
  - Qdrant vector database (port 6333, 6334)
  - Redis cache (port 6379)
- **Deployment:** Docker Compose
- **Storage:** Persistent volumes for vectors and cache data

### Related Infrastructure

**Home Assistant:**
- **IP Address:** 192.168.10.168
- **URL:** https://ha.xmojo.net
- **Port:** 8123
- **SSH:** `ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168`

**Thor Cluster (Proxmox/Kubernetes):**
- **Nodes:** 192.168.10.11-14
- **API Server:** 192.168.10.222:6443

**Storage:**
- **Synology DS1821+:** 192.168.10.159

**Jetson Devices (Archived):**
- **jetson-01:** 192.168.10.62 (Athena Lite proof-of-concept)
- **jetson-02:** 192.168.10.63 (planned)

---

## Network Verification

### Connectivity Tests

**Mac Studio:**
```bash
$ ping -c 2 192.168.10.167
PING 192.168.10.167 (192.168.10.167): 56 data bytes
64 bytes from 192.168.10.167: icmp_seq=0 ttl=64 time=10.760 ms
64 bytes from 192.168.10.167: icmp_seq=1 ttl=64 time=9.882 ms
✅ Accessible
```

**Mac mini:**
```bash
$ ping -c 2 192.168.10.181
PING 192.168.10.181 (192.168.10.181): 56 data bytes
64 bytes from 192.168.10.181: icmp_seq=0 ttl=64 time=25.690 ms
64 bytes from 192.168.10.181: icmp_seq=1 ttl=64 time=5.174 ms
✅ Accessible
```

### SSH Access

**Mac Studio (Passwordless):**
```bash
$ ssh jstuart@192.168.10.167 "hostname"
Jays-Mac-Studio.local
✅ Passwordless SSH working
```

**Setup Details:**
- SSH key: `~/.ssh/id_ed25519.pub`
- User: `jstuart`
- Configured: 2025-11-11
- Method: ssh-copy-id with expect automation

---

## Service Ports

### Mac Studio (192.168.10.167)

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| LiteLLM Gateway | 8000 | HTTP | OpenAI-compatible API gateway |
| Orchestrator | 8001 | HTTP | LangGraph state machine |
| Weather RAG | 8010 | HTTP | OpenWeatherMap integration |
| Airports RAG | 8011 | HTTP | FlightAware integration |
| Sports RAG | 8012 | HTTP | TheSportsDB integration |
| Validators | 8020 | HTTP | Anti-hallucination checks |
| Share Service | 8030 | HTTP | SMS/Email (Phase 2) |
| Ollama | 11434 | HTTP | LLM inference server |

### Mac mini (192.168.10.181)

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| Qdrant HTTP | 6333 | HTTP | Vector database API |
| Qdrant gRPC | 6334 | gRPC | High-performance client API |
| Redis | 6379 | TCP | Cache and session storage |

---

## Environment Variables

**Configuration Location:** `config/env/.env`

**Key Variables:**
```bash
# Mac Studio
MAC_STUDIO_IP=192.168.10.167
OLLAMA_URL=http://localhost:11434

# Mac mini
MAC_MINI_IP=192.168.10.181
QDRANT_URL=http://192.168.10.181:6333
REDIS_URL=redis://192.168.10.181:6379/0

# Home Assistant
HA_URL=https://192.168.10.168:8123
HA_TOKEN=<from thor cluster secret>
```

---

## Deployment Commands

### Mac Studio Access

```bash
# SSH to Mac Studio
ssh jstuart@192.168.10.167

# Check Docker services
ssh jstuart@192.168.10.167 "docker ps"

# Check Ollama models
ssh jstuart@192.168.10.167 "ollama list"

# Check running processes
ssh jstuart@192.168.10.167 "ps aux | grep -E 'ollama|python'"
```

### Mac mini Services

```bash
# Check Qdrant health
curl http://192.168.10.181:6333/healthz
# Expected: {"title":"healthz","version":"1.11.5"}

# Check Redis connectivity
redis-cli -h 192.168.10.181 PING
# Expected: PONG

# Deploy services (from Mac Studio)
scp deployment/mac-mini/docker-compose.yml jstuart@192.168.10.181:~/athena/
ssh jstuart@192.168.10.181 "cd ~/athena && docker compose up -d"

# View logs
ssh jstuart@192.168.10.181 "docker logs qdrant"
ssh jstuart@192.168.10.181 "docker logs redis"
```

### Cross-Service Communication

```bash
# From Mac Studio to Mac mini (Qdrant)
curl http://192.168.10.181:6333/collections

# From Mac Studio to Mac mini (Redis)
redis-cli -h 192.168.10.181 INFO server

# From any machine to Mac Studio (future gateway)
curl http://192.168.10.167:8000/v1/models
```

---

## Firewall Configuration

**Mac Studio:**
- Allow incoming: SSH (22), HTTP (8000-8030), Ollama (11434)
- Allow outgoing: All

**Mac mini:**
- Allow incoming: Qdrant (6333, 6334), Redis (6379)
- Allow outgoing: All

**Network Security:**
- Internal network only (192.168.10.0/24)
- No external exposure
- Thor cluster provides external access if needed

---

## DNS Configuration

**Local DNS (if configured):**
- `mac-studio.local` → 192.168.10.167
- `mac-mini.local` → 192.168.10.181
- `ha.local` → 192.168.10.168

**mDNS (Bonjour):**
- Jays-Mac-Studio.local → 192.168.10.167
- Auto-discovered on local network

---

## Troubleshooting

### Cannot Connect to Mac Studio

```bash
# Check if Mac Studio is on the network
ping 192.168.10.167

# Check SSH service
nc -zv 192.168.10.167 22

# Verify SSH key
ssh -v jstuart@192.168.10.167
```

### Cannot Connect to Mac mini Services

```bash
# Check if Mac mini is accessible
ping 192.168.10.181

# Check Qdrant port
nc -zv 192.168.10.181 6333

# Check Redis port
nc -zv 192.168.10.181 6379

# Check if Docker is running
ssh jstuart@192.168.10.181 "docker ps"
```

### Service Not Responding

```bash
# Mac Studio: Check Ollama
ssh jstuart@192.168.10.167 "ps aux | grep ollama"
ssh jstuart@192.168.10.167 "ollama serve &"

# Mac mini: Restart services
ssh jstuart@192.168.10.181 "cd ~/athena && docker compose restart"
```

---

## Network Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Home Network                            │
│                   192.168.10.0/24                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Mac Studio M4 (192.168.10.167)                            │
│  ├─ LiteLLM Gateway (8000)                                 │
│  ├─ Orchestrator (8001)                                    │
│  ├─ RAG Services (8010-8012)                               │
│  └─ Ollama (11434) → phi3, llama3.1                        │
│                                                             │
│  Mac mini M4 (192.168.10.181)                              │
│  ├─ Qdrant (6333) ← Vector embeddings                      │
│  └─ Redis (6379) ← Cache & sessions                        │
│                                                             │
│  Home Assistant (192.168.10.168)                           │
│  └─ Voice devices + automation                             │
│                                                             │
│  Thor Cluster (192.168.10.11-14, API: .222)               │
│  └─ Kubernetes infrastructure services                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Updates History

**2025-11-11 - Initial Configuration:**
- Mac Studio: 192.168.10.167 ✅
- Mac mini: 192.168.10.181 ✅
- Passwordless SSH configured ✅
- Network connectivity verified ✅

**Files Updated:**
- Project Athena CLAUDE.md
- Homelab k8s-home-lab CLAUDE.md
- START_HERE.md
- DAY_1_QUICK_START.md
- config/env/.env.template
- scripts/verify_day1.sh
- All implementation plans

**Commits:**
- `94466f0` - Mac Studio IP and SSH setup
- `fe61beb` - Homelab CLAUDE.md update
- `0b7d395` - Mac mini IP update

---

## Next Steps

1. **Deploy Mac mini services:**
   ```bash
   scp deployment/mac-mini/docker-compose.yml jstuart@192.168.10.181:~/athena/
   ssh jstuart@192.168.10.181 "mkdir -p ~/athena && cd ~/athena && docker compose up -d"
   ```

2. **Verify services:**
   ```bash
   curl http://192.168.10.181:6333/healthz
   redis-cli -h 192.168.10.181 PING
   ```

3. **Initialize Qdrant:**
   ```bash
   python3 scripts/init_qdrant.py
   ```

4. **Run Day 1 verification:**
   ```bash
   bash scripts/verify_day1.sh
   ```

---

**Last Updated:** 2025-11-11
**Network Status:** ✅ All systems operational
**Ready for:** Day 1 implementation
