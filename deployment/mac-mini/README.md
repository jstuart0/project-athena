# Mac mini Deployment

This directory contains Docker Compose configuration for deploying Qdrant and Redis on the Mac mini (192.168.10.181).

## Services

### Qdrant Vector Database
- **Port:** 6333 (HTTP API), 6334 (gRPC API)
- **Purpose:** Stores semantic embeddings for RAG retrieval
- **Storage:** Persistent volume `qdrant_storage`
- **Health Check:** HTTP endpoint `/health`

### Redis Cache
- **Port:** 6379
- **Purpose:** Caches API responses and frequently accessed data
- **Configuration:**
  - Max Memory: 2GB
  - Eviction Policy: allkeys-lru
  - Persistence: AOF + RDB snapshots
- **Health Check:** Redis CLI ping

## Deployment Instructions

### Prerequisites

1. **Enable SSH on Mac mini:**
   ```bash
   # On Mac mini (requires physical access or Screen Sharing):
   sudo systemsetup -setremotelogin on
   ```

2. **Install Docker on Mac mini:**
   ```bash
   ssh jstuart@192.168.10.181

   # Install Homebrew
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   # Install Docker Desktop
   brew install --cask docker

   # Start Docker Desktop
   open -a Docker
   ```

### Deploy Services

```bash
# From Mac Studio or any machine with SSH access to Mac mini:
scp -r deployment/mac-mini jstuart@192.168.10.181:~/

# SSH to Mac mini
ssh jstuart@192.168.10.181

# Navigate to deployment directory
cd ~/mac-mini

# Start services
docker-compose up -d

# Verify services are running
docker-compose ps
docker-compose logs -f
```

### Verify Services

```bash
# Test Qdrant from Mac Studio
curl http://192.168.10.181:6333/health

# Test Redis from Mac Studio
redis-cli -h 192.168.10.181 ping
```

### Management Commands

```bash
# View logs
docker-compose logs -f qdrant
docker-compose logs -f redis

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Stop and remove volumes (⚠️  deletes data)
docker-compose down -v
```

## Troubleshooting

### Qdrant not accessible

1. Check if container is running:
   ```bash
   docker ps | grep qdrant
   ```

2. Check logs:
   ```bash
   docker-compose logs qdrant
   ```

3. Test locally on Mac mini:
   ```bash
   curl http://localhost:6333/health
   ```

### Redis not accessible

1. Check if container is running:
   ```bash
   docker ps | grep redis
   ```

2. Check logs:
   ```bash
   docker-compose logs redis
   ```

3. Test locally on Mac mini:
   ```bash
   redis-cli ping
   ```

## Monitoring

### Resource Usage

```bash
# View resource usage
docker stats

# View specific container stats
docker stats athena-qdrant athena-redis
```

### Health Checks

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' athena-qdrant
docker inspect --format='{{.State.Health.Status}}' athena-redis
```

## Backup and Recovery

### Backup Qdrant Data

```bash
# Create backup
docker exec athena-qdrant tar czf /tmp/qdrant-backup.tar.gz /qdrant/storage
docker cp athena-qdrant:/tmp/qdrant-backup.tar.gz ./qdrant-backup-$(date +%Y%m%d).tar.gz
```

### Backup Redis Data

```bash
# Trigger RDB snapshot
docker exec athena-redis redis-cli BGSAVE

# Copy dump file
docker cp athena-redis:/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb
```

### Restore from Backup

```bash
# Stop services
docker-compose down

# Restore volumes
# (specific steps depend on backup format)

# Start services
docker-compose up -d
```

## Network Configuration

The services are accessible from the Mac Studio at:
- **Qdrant:** http://192.168.10.181:6333
- **Redis:** redis://192.168.10.181:6379

These URLs are configured in the Mac Studio `.env` file:
```bash
QDRANT_URL=http://192.168.10.181:6333
REDIS_URL=redis://192.168.10.181:6379/0
```
