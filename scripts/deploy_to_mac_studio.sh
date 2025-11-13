#!/bin/bash

set -e

echo "=========================================="
echo "Deploy Project Athena to Mac Studio"
echo "=========================================="
echo ""

# Configuration
MAC_STUDIO_IP="192.168.10.167"
MAC_STUDIO_USER="jstuart"
PROJECT_PATH="/Users/jaystuart/dev/project-athena"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Step 1: Checking SSH access to Mac Studio...${NC}"

# Test SSH connection
if ssh -q -o ConnectTimeout=5 ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} "echo 'SSH connection successful'" &>/dev/null; then
    echo -e "${GREEN}✓ SSH connection to Mac Studio established${NC}"
else
    echo -e "${RED}✗ Cannot connect to Mac Studio via SSH${NC}"
    echo "Please ensure:"
    echo "  1. Mac Studio is running"
    echo "  2. SSH is enabled on Mac Studio"
    echo "  3. You have passwordless SSH set up"
    exit 1
fi

echo ""
echo -e "${GREEN}Step 2: Creating project structure on Mac Studio...${NC}"

ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} << 'EOF'
mkdir -p ~/dev/project-athena/{src,scripts,deployment}
mkdir -p ~/dev/project-athena/src/{gateway,orchestrator,shared}
echo "✓ Project directories created"
EOF

echo ""
echo -e "${GREEN}Step 3: Copying source files to Mac Studio...${NC}"

# Copy gateway files
echo "Copying gateway files..."
scp -r src/gateway/* ${MAC_STUDIO_USER}@${MAC_STUDIO_IP}:~/dev/project-athena/src/gateway/

# Copy orchestrator files
echo "Copying orchestrator files..."
scp -r src/orchestrator/* ${MAC_STUDIO_USER}@${MAC_STUDIO_IP}:~/dev/project-athena/src/orchestrator/

# Copy shared files
echo "Copying shared files..."
scp -r src/shared/* ${MAC_STUDIO_USER}@${MAC_STUDIO_IP}:~/dev/project-athena/src/shared/

echo -e "${GREEN}✓ Source files copied${NC}"

echo ""
echo -e "${GREEN}Step 4: Creating deployment script on Mac Studio...${NC}"

# Create deployment script on Mac Studio
cat << 'DEPLOY_SCRIPT' | ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} 'cat > ~/dev/project-athena/run_services.sh'
#!/bin/bash

# Kill any existing services on ports 8000 and 8001
echo "Stopping existing services..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
sleep 2

# Environment variables
export HA_URL="https://192.168.10.168:8123"
export HA_TOKEN="${HA_TOKEN}"
export OLLAMA_URL="http://localhost:11434"
export LLM_SERVICE_URL="http://localhost:11434"
export DATABASE_URL="postgresql://psadmin:Ibucej1!@postgres-01.xmojo.net:5432/athena"
export REDIS_URL="redis://192.168.10.181:6379"
export RAG_WEATHER_URL="http://localhost:8010"
export RAG_AIRPORTS_URL="http://localhost:8011"
export RAG_SPORTS_URL="http://localhost:8012"
export GATEWAY_API_KEY="athena-gateway-key-2024"
export PYTHONPATH="/Users/jstuart/dev/project-athena/src:/Users/jstuart/dev/project-athena"

echo "Starting Orchestrator on port 8001..."
cd ~/dev/project-athena/src/orchestrator
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 > orchestrator.log 2>&1 &
echo "Orchestrator PID: $!"

sleep 5

echo "Starting Gateway on port 8000..."
cd ~/dev/project-athena/src/gateway
export ORCHESTRATOR_SERVICE_URL="http://localhost:8001"
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > gateway.log 2>&1 &
echo "Gateway PID: $!"

echo ""
echo "Services started!"
echo "  • Gateway:      http://192.168.10.167:8000"
echo "  • Orchestrator: http://192.168.10.167:8001"
echo ""
echo "Check logs:"
echo "  • tail -f ~/dev/project-athena/src/gateway/gateway.log"
echo "  • tail -f ~/dev/project-athena/src/orchestrator/orchestrator.log"
DEPLOY_SCRIPT

ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} "chmod +x ~/dev/project-athena/run_services.sh"

echo -e "${GREEN}✓ Deployment script created${NC}"

echo ""
echo -e "${GREEN}Step 5: Installing Python dependencies on Mac Studio...${NC}"

# Install dependencies on Mac Studio
ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} << 'EOF'
cd ~/dev/project-athena

echo "Installing gateway dependencies..."
pip3 install --user fastapi uvicorn httpx pydantic prometheus-client redis structlog python-dotenv

echo "Installing orchestrator dependencies..."
pip3 install --user langgraph langchain redis httpx asyncpg

echo "✓ Dependencies installed"
EOF

echo ""
echo -e "${GREEN}Step 6: Starting services on Mac Studio...${NC}"

# Run the deployment script on Mac Studio
ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} "cd ~/dev/project-athena && ./run_services.sh"

echo ""
echo -e "${GREEN}Step 7: Waiting for services to be ready...${NC}"

# Function to check service health
check_service() {
    local service_name=$1
    local service_url=$2
    local max_attempts=30
    local attempt=1

    echo -n "Waiting for $service_name..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s $service_url > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e " ${RED}✗${NC}"
    return 1
}

# Check services
check_service "Orchestrator" "http://${MAC_STUDIO_IP}:8001/health"
check_service "Gateway" "http://${MAC_STUDIO_IP}:8000/health"

echo ""
echo -e "${GREEN}Step 8: Running integration test...${NC}"

# Test the gateway
response=$(curl -s -X POST http://${MAC_STUDIO_IP}:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer athena-gateway-key-2024" \
    -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello, test"}]}' \
    2>/dev/null)

if echo "$response" | grep -q "choices"; then
    echo -e "${GREEN}✓ Gateway test passed${NC}"
else
    echo -e "${YELLOW}⚠ Gateway test may have issues${NC}"
    echo "Response: $response"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Services running on Mac Studio (${MAC_STUDIO_IP}):"
echo "  • Gateway:      http://${MAC_STUDIO_IP}:8000"
echo "  • Orchestrator: http://${MAC_STUDIO_IP}:8001"
echo ""
echo "API Endpoints:"
echo "  • OpenAI API:   http://${MAC_STUDIO_IP}:8000/v1/chat/completions"
echo "  • Health:       http://${MAC_STUDIO_IP}:8000/health"
echo "  • Metrics:      http://${MAC_STUDIO_IP}:8001/metrics"
echo ""
echo "Configure Home Assistant:"
echo "  1. Go to Home Assistant settings"
echo "  2. Add OpenAI Conversation integration"
echo "  3. Use URL: http://${MAC_STUDIO_IP}:8000/v1"
echo "  4. API Key: athena-gateway-key-2024"
echo ""
echo "SSH to Mac Studio to check logs:"
echo "  ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP}"
echo "  tail -f ~/dev/project-athena/src/gateway/gateway.log"
echo "  tail -f ~/dev/project-athena/src/orchestrator/orchestrator.log"
echo ""
echo "Stop services:"
echo "  ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} 'pkill -f uvicorn'"