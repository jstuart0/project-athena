# Project Athena - Mac Studio Deployment

AI Processing Layer services for Project Athena voice assistant system.

## Hardware

- **Server**: Mac Studio M4 64GB
- **IP Address**: 192.168.10.167
- **Role**: AI processing layer (STT, TTS, LLM, Gateway, Orchestrator)
- **Network**: Connected via 10GbE to homelab infrastructure

## Services

This deployment includes the following containerized services:

### 1. Piper TTS (Text-to-Speech)
- **Port**: 10200
- **Protocol**: Wyoming
- **Image**: rhasspy/wyoming-piper
- **Voice Model**: en_US-lessac-medium (default, configurable)
- **Purpose**: Convert text to natural-sounding speech

### 2. Faster-Whisper STT (Speech-to-Text)
- **Port**: 10300
- **Protocol**: Wyoming
- **Image**: rhasspy/wyoming-faster-whisper
- **Model**: tiny.en (fast, low-resource)
- **Purpose**: Convert speech to text transcription

### 3. Gateway Service
- **Port**: 8000
- **Purpose**: Main API entry point, request routing
- **Endpoints**: `/voice/transcribe`, `/voice/synthesize`, `/voice/query`

### 4. Orchestrator Service
- **Port**: 8001
- **Purpose**: Coordinate LLM queries, RAG lookups, policy enforcement
- **Features**: Intent classification, context management

## Quick Start

### Prerequisites

1. **Docker installed** on Mac Studio
2. **Project code** cloned to `/Users/jstuart/dev/project-athena/`
3. **Ollama running** on host (for LLM processing)
4. **Mac mini services** running (Qdrant, Redis at 192.168.10.181)

### Installation

```bash
# On Mac Studio (192.168.10.167)
cd ~/dev/project-athena/deployment/mac-studio

# Create required directories
mkdir -p piper/{data,models}
mkdir -p whisper/{data,models}
mkdir -p gateway/config
mkdir -p orchestrator/config

# Download Piper voice model (optional - auto-downloaded on first run)
# docker run --rm -v $(pwd)/piper/models:/models \
#   rhasspy/wyoming-piper:latest \
#   python3 -m wyoming_piper.download --voice en_US-lessac-medium

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Check service health
curl http://localhost:8000/health  # Gateway
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:10200/health # Piper TTS (if health endpoint available)
curl http://localhost:10300/health # Whisper STT (if health endpoint available)
```

### Verify Deployment

```bash
# Check running containers
docker compose ps

# Test Piper TTS (example - actual Wyoming protocol is different)
# This will be tested via the Gateway /voice/synthesize endpoint

# Test Whisper STT (example - actual Wyoming protocol is different)
# This will be tested via the Gateway /voice/transcribe endpoint

# Test Gateway
curl http://localhost:8000/health

# Test Orchestrator
curl http://localhost:8001/health
```

## Configuration

### Piper Voice Models

Available voice models (configured via `PIPER_VOICE` environment variable):

- `en_US-lessac-medium` - Default, balanced quality/speed
- `en_US-lessac-high` - Higher quality, slower
- `en_US-lessac-low` - Faster, lower quality
- `en_GB-alan-medium` - British English
- `en_US-libritts-high` - Alternative high-quality voice

To change voice:
1. Edit `docker-compose.yml`
2. Set `PIPER_VOICE` environment variable
3. Restart: `docker compose restart piper-tts`

### Whisper Models

Available models (configured via `WHISPER_MODEL` environment variable):

- `tiny.en` - Default, fastest (73MB)
- `base.en` - Better accuracy (142MB)
- `small.en` - Good balance (466MB)
- `medium.en` - High accuracy, slower (1.5GB)

To change model:
1. Edit `docker-compose.yml`
2. Set `WHISPER_MODEL` environment variable
3. Restart: `docker compose restart whisper-stt`

### Environment Variables

Key configuration options in `docker-compose.yml`:

**Piper TTS:**
- `PIPER_VOICE` - Voice model to use
- `PIPER_LENGTH_SCALE` - Speech speed (1.0 = normal, 0.5 = 2x speed, 2.0 = half speed)
- `PIPER_NOISE_SCALE` - Variation in speech (0.667 = default)
- `PIPER_NOISE_W` - Variation in timing (0.8 = default)

**Whisper STT:**
- `WHISPER_MODEL` - Model size
- `WHISPER_BEAM_SIZE` - Decoding beam size (5 = default)
- `WHISPER_LANGUAGE` - Language code (en = English)

**Gateway/Orchestrator:**
- `STT_SERVICE_URL` - Whisper STT endpoint
- `TTS_SERVICE_URL` - Piper TTS endpoint
- `LLM_SERVICE_URL` - Ollama endpoint (on host)
- `QDRANT_URL` - Vector database (Mac mini)
- `REDIS_URL` - Cache service (Mac mini)
- `RAG_*_URL` - RAG connector endpoints

## Service URLs

### From External Network
- Gateway API: `http://192.168.10.167:8000`
- Orchestrator API: `http://192.168.10.167:8001`
- Piper TTS (Wyoming): `tcp://192.168.10.167:10200`
- Whisper STT (Wyoming): `tcp://192.168.10.167:10300`

### From Within Docker Network
- Gateway: `http://gateway:8000`
- Orchestrator: `http://orchestrator:8001`
- Piper TTS: `http://piper-tts:10200`
- Whisper STT: `http://whisper-stt:10300`

### Host Services (via host.docker.internal)
- Ollama LLM: `http://host.docker.internal:11434`
- RAG Weather: `http://host.docker.internal:8010`
- RAG Airports: `http://host.docker.internal:8011`
- RAG Flights: `http://host.docker.internal:8012`

### Mac mini Services (via IP)
- Qdrant: `http://192.168.10.181:6333`
- Redis: `redis://192.168.10.181:6379`

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs <service-name>

# Check if ports are in use
lsof -i :8000  # Gateway
lsof -i :8001  # Orchestrator
lsof -i :10200 # Piper
lsof -i :10300 # Whisper

# Restart service
docker compose restart <service-name>

# Rebuild from scratch
docker compose down
docker compose up -d --build
```

### Voice Model Download Issues

```bash
# Manually download Piper voice model
docker run --rm -v $(pwd)/piper/models:/models \
  rhasspy/wyoming-piper:latest \
  python3 -m wyoming_piper.download --voice en_US-lessac-medium

# Check model files
ls -lh piper/models/
```

### Network Connectivity Issues

```bash
# Test connection to Mac mini services
curl http://192.168.10.181:6333/healthz  # Qdrant
redis-cli -h 192.168.10.181 PING         # Redis

# Test connection to host services
curl http://host.docker.internal:11434/api/version  # Ollama
```

### Container Resource Issues

```bash
# Check resource usage
docker stats

# View container logs
docker compose logs -f --tail=100 <service-name>

# Adjust memory limits in docker-compose.yml if needed
```

## Maintenance

### Update Services

```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d

# Clean up old images
docker image prune -f
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f piper-tts
docker compose logs -f whisper-stt
docker compose logs -f gateway
docker compose logs -f orchestrator

# Last 50 lines
docker compose logs --tail=50
```

### Backup Configuration

```bash
# Backup voice models and configuration
tar -czf ~/athena-backup-$(date +%Y%m%d).tar.gz \
  piper/ whisper/ gateway/config orchestrator/config docker-compose.yml

# Restore from backup
tar -xzf ~/athena-backup-YYYYMMDD.tar.gz
```

## Integration with Home Assistant

Piper and Whisper services use the Wyoming protocol, making them compatible with Home Assistant voice pipeline.

### Home Assistant Configuration

Add to `/config/configuration.yaml`:

```yaml
# Wyoming protocol integration
wyoming:
  # Piper TTS on Mac Studio
  - platform: piper
    host: 192.168.10.167
    port: 10200

  # Whisper STT on Mac Studio
  - platform: faster-whisper
    host: 192.168.10.167
    port: 10300
```

Then restart Home Assistant and configure in Settings → Voice Assistants.

## Performance

**Expected Performance (Mac Studio M4):**
- **STT Latency**: <500ms (tiny.en model)
- **TTS Latency**: <200ms (lessac-medium voice)
- **Memory Usage**:
  - Piper: ~512MB
  - Whisper: ~1GB (tiny.en), ~2GB (base.en)
  - Gateway: ~256MB
  - Orchestrator: ~256MB

**Concurrent Requests:**
- Piper: 5-10 concurrent TTS requests
- Whisper: 3-5 concurrent STT requests

## Development

### Local Development

```bash
# Run services in foreground for debugging
docker compose up

# Rebuild after code changes
docker compose up -d --build gateway orchestrator

# Access container shell
docker compose exec gateway bash
docker compose exec orchestrator bash
```

### Adding New Services

1. Add service definition to `docker-compose.yml`
2. Create volume directories if needed
3. Update service URLs in dependent services
4. Test with `docker compose config`
5. Deploy with `docker compose up -d`

## License

Project Athena is released under MIT License (or your chosen license).

## Contributing

Contributions welcome! Please submit issues and pull requests to the main repository.

## Support

For issues and questions:
- GitHub Issues: (link to repo)
- Wiki Documentation: https://wiki.xmojo.net/homelab/projects/project-athena
- Discord/Community: (if applicable)

---

**Last Updated**: November 12, 2025
**Maintained By**: Jay Stuart
**Repository**: https://github.com/your-org/project-athena (or actual repo link)
