#!/bin/bash
#
# Setup isolated Redis instance for benchmarking.
#
# Creates a Docker container running Redis on port 6380 (separate from production port 6379).
# This ensures benchmark results are not affected by production cache.
#

set -e

CONTAINER_NAME="athena-benchmark-redis"
REDIS_PORT="6380"
REDIS_IMAGE="redis:7-alpine"

echo "================================================"
echo "Project Athena - Benchmark Redis Setup"
echo "================================================"
echo "Container: $CONTAINER_NAME"
echo "Port:      $REDIS_PORT"
echo "Image:     $REDIS_IMAGE"
echo "================================================"
echo

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "✗ Error: Docker is not running"
    echo "  Please start Docker Desktop and try again"
    exit 1
fi

echo "✓ Docker is running"

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container '$CONTAINER_NAME' already exists"

    # Check if it's running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "✓ Container is already running"
    else
        echo "Starting existing container..."
        docker start "$CONTAINER_NAME"
        echo "✓ Container started"
    fi
else
    echo "Creating new Redis container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$REDIS_PORT:6379" \
        --restart unless-stopped \
        "$REDIS_IMAGE"

    echo "✓ Container created and started"
fi

# Wait for Redis to be ready
echo
echo "Waiting for Redis to be ready..."
sleep 2

# Test connection
if docker exec "$CONTAINER_NAME" redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis is responding to PING"
else
    echo "✗ Error: Redis is not responding"
    exit 1
fi

# Show container status
echo
echo "Container Status:"
echo "----------------"
docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo
echo "================================================"
echo "Benchmark Redis Setup Complete!"
echo "================================================"
echo
echo "Connection details:"
echo "  URL:  redis://localhost:$REDIS_PORT/0"
echo "  URL:  redis://192.168.10.181:$REDIS_PORT/0 (network)"
echo
echo "Useful commands:"
echo "  docker exec $CONTAINER_NAME redis-cli PING"
echo "  docker exec $CONTAINER_NAME redis-cli FLUSHDB"
echo "  docker logs $CONTAINER_NAME"
echo "  docker stop $CONTAINER_NAME"
echo "  docker start $CONTAINER_NAME"
echo "  docker rm -f $CONTAINER_NAME  # Remove container"
echo
