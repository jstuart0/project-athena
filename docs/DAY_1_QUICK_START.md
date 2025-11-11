# Day 1 Quick Start Guide - Project Athena Phase 1

**Date:** 2025-11-11
**Goal:** Get environment ready and start basic setup TODAY

---

## ✅ What You Have

- [x] Mac Studio M4 (64GB)
- [x] Mac mini M4 (16GB)
- [x] 2 HA Voice devices (Office + Master Bedroom)
- [x] Home Assistant @ 192.168.10.168

## 🔴 What You Need Today

### 1. Network Configuration (15 minutes)

**Assign Static IPs:**

**On Mac Studio:**
```bash
# Open System Settings → Network → Wi-Fi/Ethernet → Details → TCP/IP
# Set to Manual, assign: 192.168.10.20
# Subnet: 255.255.255.0
# Router: 192.168.10.1 (your gateway)
# DNS: 192.168.10.1 or 8.8.8.8
```

**On Mac mini:**
```bash
# Same process, assign: 192.168.10.29
```

**Verify connectivity:**
```bash
# From your laptop
ping 192.168.10.20
ping 192.168.10.29

# From Mac Studio
ping 192.168.10.29  # Should reach Mac mini
ping 192.168.10.168  # Should reach Home Assistant
```

### 2. Home Assistant Token (5 minutes)

**Get Long-Lived Access Token:**
1. Open Home Assistant: https://192.168.10.168:8123
2. Click your profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Name: "Athena Gateway"
6. Copy the token (starts with "eyJhbGci...")
7. **Save it securely** - you'll need it for .env file

### 3. API Keys - Start Gathering (Today: Get 1, Tomorrow: Get Rest)

**Priority 1 (Get Today): OpenWeatherMap**
- Go to: https://openweathermap.org/api
- Sign up (free tier, no credit card needed)
- Get API key (should be instant)
- **This unlocks weather queries for testing**

**Priority 2 (Get This Week):**
- **FlightAware:** https://www.flightaware.com/commercial/flightxml/
  - Sign up, get API key
  - Enables airport queries
- **TheSportsDB:** https://www.thesportsdb.com/api.php
  - Free tier available
  - Enables sports queries

**Defer to Phase 2 (Not needed today):**
- NewsAPI, Spoonacular, TMDB, Yelp - skip for now

---

## 🚀 Day 1 Tasks (Start Now)

### Task 1: Environment Setup (30 minutes)

**On Mac Studio @ 192.168.10.20:**

```bash
# 1. Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install essential tools
brew install git python@3.11 docker docker-compose curl jq

# 3. Start Docker Desktop
open /Applications/Docker.app
# Wait for Docker to start (check menu bar icon)

# 4. Clone repository
cd /Users/jaystuart/dev
# If not already cloned:
# git clone <your-repo-url> project-athena
cd project-athena

# 5. Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 6. Install Python tools
pip install --upgrade pip
pip install pytest pytest-asyncio black flake8
```

**On Mac mini @ 192.168.10.29:**

```bash
# 1. Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Docker
brew install docker docker-compose

# 3. Start Docker
open /Applications/Docker.app
# Wait for Docker to start

# 4. Verify Docker
docker ps
```

### Task 2: Install Ollama on Mac Studio (30 minutes)

**This is the longest step - models are large!**

```bash
# On Mac Studio
brew install ollama

# Start Ollama service
ollama serve &

# Pull models (this takes ~30 mins for all models)
echo "Pulling phi3:mini-q8 (~2.5GB)..."
ollama pull phi3:mini-q8

echo "Pulling llama3.1:8b-q4 (~4.7GB)..."
ollama pull llama3.1:8b-q4

# Optional: Skip large model for now
# ollama pull llama3.1:13b-q4  # ~7.3GB

# Verify models installed
ollama list
```

**While models download, move to Task 3!**

### Task 3: Create Environment Configuration (10 minutes)

**On Mac Studio:**

```bash
cd /Users/jaystuart/dev/project-athena

# Create config directory
mkdir -p config/env

# Create .env file
cat > config/env/.env <<'EOF'
# Home Assistant
HA_URL=https://192.168.10.168:8123
HA_TOKEN=PASTE_YOUR_TOKEN_HERE

# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_SMALL_MODEL=phi3:mini-q8
OLLAMA_MEDIUM_MODEL=llama3.1:8b-q4
OLLAMA_LARGE_MODEL=llama3.1:13b-q4

# Gateway
LITELLM_MASTER_KEY=sk-$(openssl rand -hex 16)

# Vector DB & Cache (Mac mini)
QDRANT_URL=http://192.168.10.29:6333
REDIS_URL=redis://192.168.10.29:6379/0

# RAG API Keys (Get these ASAP)
OPENWEATHER_API_KEY=GET_THIS_TODAY
FLIGHTAWARE_API_KEY=GET_THIS_WEEK
THESPORTSDB_API_KEY=GET_THIS_WEEK

# Feature Flags (Phase 1 - Keep these disabled)
ENABLE_GUEST_MODE=false
ENABLE_SHARE_SERVICE=false
ENABLE_CROSS_MODEL_VALIDATION=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

# Now edit and add your HA token
nano config/env/.env
# Find HA_TOKEN line
# Replace PASTE_YOUR_TOKEN_HERE with actual token
# Save: Ctrl+O, Enter, Ctrl+X
```

### Task 4: Deploy Mac mini Services (15 minutes)

**On Mac mini:**

```bash
# Create deployment directory
mkdir -p ~/athena/mac-mini
cd ~/athena/mac-mini

# Create docker-compose.yml
cat > docker-compose.yml <<'EOF'
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  qdrant_storage:
  redis_data:
EOF

# Start services
docker compose up -d

# Wait 30 seconds for startup
sleep 30

# Verify services
curl http://localhost:6333/healthz
redis-cli PING

# Should see:
# {"title":"healthz","version":"1.11.5"}
# PONG
```

**From Mac Studio, verify remote access:**

```bash
# Test Qdrant from Mac Studio
curl http://192.168.10.29:6333/healthz

# Test Redis from Mac Studio
redis-cli -h 192.168.10.29 PING
```

### Task 5: Initialize Qdrant Collection (5 minutes)

**On Mac Studio:**

```bash
cd /Users/jaystuart/dev/project-athena

# Create scripts directory
mkdir -p scripts

# Create initialization script
cat > scripts/init_qdrant.py <<'EOF'
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://192.168.10.29:6333")

# Create collection for knowledge vectors
client.create_collection(
    collection_name="athena_knowledge",
    vectors_config=VectorParams(
        size=384,  # sentence-transformers/all-MiniLM-L6-v2
        distance=Distance.COSINE
    )
)

print("✅ Qdrant collection 'athena_knowledge' created successfully")
EOF

# Install Qdrant client
source venv/bin/activate
pip install qdrant-client

# Run initialization
python scripts/init_qdrant.py
```

---

## 🎯 Day 1 Success Criteria

By end of today, you should have:

- [x] **Network:** Mac Studio @ 192.168.10.20, Mac mini @ 192.168.10.29
- [x] **Docker:** Running on both Macs
- [x] **Ollama:** Models downloaded on Mac Studio (`ollama list` shows phi3 and llama3.1)
- [x] **Mac mini services:** Qdrant + Redis running and accessible
- [x] **Environment:** .env file created with HA token
- [x] **API Keys:** At least OpenWeatherMap key obtained

**Verification Commands:**

```bash
# From Mac Studio
ping 192.168.10.29  # Mac mini reachable
ollama list  # Shows 2+ models
curl http://192.168.10.29:6333/healthz  # Qdrant healthy
redis-cli -h 192.168.10.29 PING  # Redis responds PONG
cat config/env/.env | grep HA_TOKEN  # Token present
cat config/env/.env | grep OPENWEATHER  # API key present (not "GET_THIS_TODAY")
```

---

## 📅 What's Next (Day 2 Tomorrow)

Tomorrow you'll:
1. Create repository structure (apps/ directories)
2. Deploy LiteLLM gateway
3. Test first OpenAI-compatible API call
4. Start migrating RAG handlers from Jetson code

**Estimated Time Tomorrow:** 3-4 hours

---

## 🆘 Troubleshooting Day 1

**Problem: Docker won't start**
```bash
# Check if Docker Desktop is running
ps aux | grep Docker

# Restart Docker Desktop
killall Docker
open /Applications/Docker.app
```

**Problem: Ollama serve hangs**
```bash
# Check if already running
ps aux | grep ollama

# Kill and restart
killall ollama
ollama serve &
```

**Problem: Can't reach Mac mini from Mac Studio**
```bash
# Check firewall on Mac mini
# System Settings → Network → Firewall
# Either disable or add exceptions for ports 6333, 6379

# Verify IPs
ifconfig | grep "inet "
```

**Problem: Qdrant won't start**
```bash
# Check Docker logs
docker logs qdrant

# Check port not in use
lsof -i :6333

# Restart container
docker restart qdrant
```

---

## 📞 Need Help?

If you get stuck on any step:
1. Check the error message carefully
2. Look at logs: `docker logs <container_name>`
3. Verify prerequisites completed
4. Ask me for help with specific error

---

**Good luck with Day 1! You've got this! 🚀**
