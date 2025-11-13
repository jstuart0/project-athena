#!/bin/bash

set -e

echo "Deploying Orchestrator and Gateway services..."

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found, using defaults"
fi

# Build images
echo "Building Docker images..."
docker build -t athena-gateway:latest src/gateway/
docker build -t athena-orchestrator:latest src/orchestrator/

# Stop existing containers
echo "Stopping existing containers..."
docker stop athena-gateway athena-orchestrator 2>/dev/null || true
docker rm athena-gateway athena-orchestrator 2>/dev/null || true

# Start services
echo "Starting services..."

# Start orchestrator first (gateway depends on it)
docker run -d \
    --name athena-orchestrator \
    --restart unless-stopped \
    -p 8001:8001 \
    -e HA_URL="${HA_URL:-https://192.168.10.168:8123}" \
    -e HA_TOKEN="${HA_TOKEN}" \
    -e OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}" \
    -e LLM_SERVICE_URL="${LLM_SERVICE_URL:-http://host.docker.internal:11434}" \
    -e REDIS_URL="${REDIS_URL:-redis://192.168.10.181:6379}" \
    -e RAG_WEATHER_URL="${RAG_WEATHER_URL:-http://host.docker.internal:8010}" \
    -e RAG_AIRPORTS_URL="${RAG_AIRPORTS_URL:-http://host.docker.internal:8011}" \
    -e RAG_SPORTS_URL="${RAG_SPORTS_URL:-http://host.docker.internal:8012}" \
    --add-host=host.docker.internal:host-gateway \
    athena-orchestrator:latest

# Wait for orchestrator to be ready
echo "Waiting for orchestrator to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8001/health &>/dev/null; then
        echo "Orchestrator is ready"
        break
    fi
    sleep 1
done

# Start gateway
docker run -d \
    --name athena-gateway \
    --restart unless-stopped \
    -p 8000:8000 \
    -e ORCHESTRATOR_SERVICE_URL="${ORCHESTRATOR_SERVICE_URL:-http://host.docker.internal:8001}" \
    -e LLM_SERVICE_URL="${LLM_SERVICE_URL:-http://host.docker.internal:11434}" \
    -e GATEWAY_API_KEY="${GATEWAY_API_KEY:-dummy-key}" \
    --add-host=host.docker.internal:host-gateway \
    athena-gateway:latest

# Wait for gateway to be ready
echo "Waiting for gateway to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health &>/dev/null; then
        echo "Gateway is ready"
        break
    fi
    sleep 1
done

# Run health checks
echo "Running health checks..."
echo "Gateway health:"
curl -s http://localhost:8000/health | python3 -m json.tool || echo "Failed to get gateway health"

echo ""
echo "Orchestrator health:"
curl -s http://localhost:8001/health | python3 -m json.tool || echo "Failed to get orchestrator health"

echo ""
echo "✅ Orchestrator and Gateway deployed successfully!"
echo ""
echo "Next steps:"
echo "1. Test gateway OpenAI endpoint:"
echo "   curl -X POST http://localhost:8000/v1/chat/completions \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -H 'Authorization: Bearer dummy-key' \\"
echo "        -d '{\"model\":\"gpt-3.5-turbo\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'"
echo ""
echo "2. Test orchestrator directly:"
echo "   curl -X POST http://localhost:8001/query \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"query\":\"What is the weather?\"}'"
echo ""
echo "3. Configure Home Assistant to use http://192.168.10.167:8000/v1 as OpenAI endpoint"
echo ""
echo "4. Run integration tests:"
echo "   cd /Users/jaystuart/dev/project-athena"
echo "   pytest tests/integration/test_orchestrator_gateway.py"
echo ""
echo "5. View logs:"
echo "   docker logs -f athena-gateway"
echo "   docker logs -f athena-orchestrator"