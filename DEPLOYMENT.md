# Project Athena - Deployment Guide

**Last Updated:** 2025-11-11
**Status:** Phase 1 - Production Ready
**Version:** 1.0.0

---

## Overview

This guide covers deploying and operating Project Athena voice assistant system.

## Architecture

**Mac Studio M4 (192.168.10.167):**
- LiteLLM Gateway (port 8000)
- Orchestrator (port 8001)
- 11 RAG Services (ports 8010-8020)
- Validators Service (port 8030)
- Ollama LLMs (port 11434)

**Mac mini M4 (192.168.10.181):**
- Qdrant Vector DB (port 6333) - NOT YET DEPLOYED
- Redis Cache (port 6379) - NOT YET DEPLOYED

**Home Assistant (192.168.10.168):**
- Voice pipeline integration
- Wyoming protocol (STT/TTS)
- Assist Pipelines

---

## Quick Start

### Check Service Status

```bash
# SSH to Mac Studio
ssh jstuart@192.168.10.167

# Check all Docker containers
/Applications/Docker.app/Contents/Resources/bin/docker ps

# Should see 13 containers running:
# - athena-litellm
# - athena-orchestrator
# - athena-weather-rag
# - athena-airports-rag
# - athena-flights-rag
# - athena-events-rag
# - athena-streaming-rag
# - athena-news-rag
# - athena-stocks-rag
# - athena-sports-rag
# - athena-websearch-rag
# - athena-dining-rag
# - athena-recipes-rag
```

### Test End-to-End

```bash
# Simple query
curl -s http://192.168.10.167:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"what is 2+2?"}]}' \
  | jq -r '.choices[0].message.content'

# Weather query
curl -s http://192.168.10.167:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"what is the weather in Baltimore?"}]}' \
  | jq -r '.choices[0].message.content'
```

---

## Service Management

### Start All Services

```bash
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d
```

### Stop All Services

```bash
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
/Applications/Docker.app/Contents/Resources/bin/docker compose down
```

### Restart Specific Service

```bash
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
/Applications/Docker.app/Contents/Resources/bin/docker compose restart orchestrator
```

### View Logs

```bash
# All services
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f

# Specific service
/Applications/Docker.app/Contents/Resources/bin/docker logs -f athena-orchestrator

# Last 50 lines
/Applications/Docker.app/Contents/Resources/bin/docker logs --tail 50 athena-weather-rag
```

### Health Checks

```bash
# Check all service health
for port in 8001 8010 8011 8012 8013 8014 8015 8016 8017 8018 8019 8020 8030; do
  echo -n "Port $port: "
  curl -s http://192.168.10.167:$port/health | jq -r '.service // .status'
done

# Gateway health (requires auth)
curl -s http://192.168.10.167:8000/health \
  -H "Authorization: Bearer sk-athena-9fd1ef6c8ed1eb0278f5133095c60271"
```

---

## Configuration

### Environment Variables

Located at: `~/dev/project-athena/config/env/.env` on Mac Studio

**Key variables:**
```bash
HA_URL=https://192.168.10.168:8123
HA_TOKEN=<long-lived-token>
OLLAMA_URL=http://localhost:11434
LITELLM_MASTER_KEY=sk-athena-9fd1ef6c8ed1eb0278f5133095c60271
QDRANT_URL=http://192.168.10.181:6333
REDIS_URL=redis://192.168.10.181:6379/0
OPENWEATHER_API_KEY=<key>
FLIGHTAWARE_API_KEY=<key>
THESPORTSDB_API_KEY=123
```

### Docker Compose

Located at: `~/dev/project-athena/docker-compose.yml`

**To modify:**
1. Edit docker-compose.yml
2. Validate: `/Applications/Docker.app/Contents/Resources/bin/docker compose config`
3. Redeploy: `/Applications/Docker.app/Contents/Resources/bin/docker compose up -d`

---

## Ollama Models

### Check Models

```bash
ssh jstuart@192.168.10.167
curl http://localhost:11434/api/tags | jq '.models[] | {name, size}'
```

### Pull New Model

```bash
# Small model (fast)
ollama pull phi3:mini

# Medium model (balanced)
ollama pull llama3.1:8b

# Large model (accurate)
ollama pull llama3.1:13b
```

### Update Gateway Config

Edit `~/dev/project-athena/apps/gateway/config.yaml`:
```yaml
model_list:
  - model_name: athena-large
    litellm_params:
      model: ollama/llama3.1:13b
      api_base: http://host.docker.internal:11434
```

Then restart gateway:
```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose restart litellm
```

---

## Monitoring

### Prometheus Metrics

All services expose `/metrics` endpoints:

```bash
curl http://192.168.10.167:8001/metrics  # Orchestrator
curl http://192.168.10.167:8010/metrics  # Weather RAG
curl http://192.168.10.167:8030/metrics  # Validators
```

### Check Resource Usage

```bash
# Container stats
/Applications/Docker.app/Contents/Resources/bin/docker stats

# Mac Studio resources
ssh jstuart@192.168.10.167 "top -l 1 | head -20"
```

---

## Testing

### Run Integration Tests

```bash
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
python3 -m pytest tests/integration/test_full_system.py -v

# Specific test class
python3 -m pytest tests/integration/test_full_system.py::TestOrchestratorIntegration -v

# With output
python3 -m pytest tests/integration/test_full_system.py -v -s
```

### Manual Testing

```bash
# Test weather RAG directly
curl http://192.168.10.167:8010/weather/current?location=Baltimore

# Test orchestrator
curl -X POST http://192.168.10.167:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}]}'

# Test validators
curl -X POST http://192.168.10.167:8030/validate \
  -H "Content-Type: application/json" \
  -d '{
    "answer": "The temperature is 32°F",
    "query": "what is the weather?",
    "sources": [{"type":"weather"}]
  }'
```

---

## Backup & Recovery

### Backup Configuration

```bash
# Backup docker-compose and env files
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
tar czf athena-config-$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  config/env/.env \
  apps/gateway/config.yaml

# Copy to safe location
scp jstuart@192.168.10.167:~/dev/project-athena/athena-config-*.tar.gz ~/backups/
```

### Restore from Backup

```bash
# Extract backup
tar xzf athena-config-YYYYMMDD.tar.gz

# Review and apply
less docker-compose.yml
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d
```

---

## Updating Services

### Update Code

```bash
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
git pull
```

### Rebuild and Restart

```bash
# Rebuild specific service
/Applications/Docker.app/Contents/Resources/bin/docker compose build orchestrator

# Restart with new image
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d orchestrator

# Or rebuild all
/Applications/Docker.app/Contents/Resources/bin/docker compose build
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d
```

---

## Performance Tuning

### Current Performance (as of 2025-11-11)

- **Weather Query:** 0.83s average
- **Simple Query:** <1s
- **P95 Latency:** <2s (far exceeds 5.5s target)

### Optimization Tips

1. **Model Selection:**
   - Use phi3:mini for simple queries
   - Use llama3.1:8b for complex reasoning
   - Reserve large models for critical tasks

2. **Caching:**
   - Deploy Redis on Mac mini for response caching
   - Reduces API calls and improves latency

3. **Resource Allocation:**
   - Monitor `docker stats` for bottlenecks
   - Adjust container resources in docker-compose.yml

---

## Common Operations

### Add New RAG Service

1. Create service directory:
   ```bash
   mkdir -p apps/rag-services/myservice
   ```

2. Create main.py (see existing services as template)

3. Create Dockerfile:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["python", "main.py"]
   ```

4. Add to docker-compose.yml:
   ```yaml
   myservice-rag:
     build:
       context: apps/rag-services/myservice
     ports:
       - "8021:8021"
     environment:
       - MYSERVICE_PORT=8021
     networks:
       - athena-network
   ```

5. Deploy:
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose up -d myservice-rag
   ```

---

## Security

### API Keys

- Never commit API keys to git
- Store in ~/dev/project-athena/config/env/.env
- Backup .env file securely (encrypted)

### LiteLLM Master Key

- Current key: `sk-athena-9fd1ef6c8ed1eb0278f5133095c60271`
- Rotate periodically
- Update in config/env/.env and apps/gateway/config.yaml

### Network Access

- Mac Studio services: Local network only (192.168.10.0/24)
- No public internet exposure
- Use VPN (Headscale) for remote access

---

## Support

### Documentation
- This file: DEPLOYMENT.md
- Troubleshooting: TROUBLESHOOTING.md
- Architecture: docs/ARCHITECTURE.md
- Plan: thoughts/shared/plans/

### Tracking
- Implementation status: IMPLEMENTATION_TRACKING_LIVE.md
- Test results: Run pytest for latest results

---

**Questions? Check TROUBLESHOOTING.md or review service logs.**
