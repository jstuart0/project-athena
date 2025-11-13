#!/bin/bash

# Deploy RAG Services on Mac Studio
set -e

echo "==========================================="
echo "Deploying RAG Services on Mac Studio"
echo "==========================================="

# Configuration
MAC_STUDIO_IP="192.168.10.167"
MAC_STUDIO_USER="jstuart"

# RAG services to deploy
declare -A SERVICES=(
    ["weather"]=8010
    ["airports"]=8011
    ["sports"]=8012
    ["events"]=8013
    ["streaming"]=8014
    ["news"]=8015
    ["stocks"]=8016
    ["flights"]=8017
)

echo "Deploying to Mac Studio at ${MAC_STUDIO_IP}..."

# Copy RAG service files
echo "Copying RAG service files..."
scp -r src/rag ${MAC_STUDIO_USER}@${MAC_STUDIO_IP}:~/dev/project-athena/src/

# Create deployment script on Mac Studio
ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} << 'DEPLOY_SCRIPT'
#!/bin/bash

cd ~/dev/project-athena

# Set environment variables
export DATABASE_URL="postgresql://psadmin:Ibucej1!@postgres-01.xmojo.net:5432/athena"
export REDIS_URL="redis://192.168.10.181:6379"
export PYTHONPATH="/Users/jstuart/dev/project-athena/src:/Users/jstuart/dev/project-athena"

# Kill existing RAG services
echo "Stopping existing RAG services..."
for port in {8010..8017}; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done
sleep 2

# Start each RAG service
echo "Starting RAG services..."

# Weather Service
export RAG_SERVICE_NAME="weather"
nohup python3 -m uvicorn rag.service:app --host 0.0.0.0 --port 8010 > logs/rag_weather.log 2>&1 &
echo "Started Weather RAG service on port 8010 (PID: $!)"

# Airports Service
export RAG_SERVICE_NAME="airports"
nohup python3 -m uvicorn rag.service:app --host 0.0.0.0 --port 8011 > logs/rag_airports.log 2>&1 &
echo "Started Airports RAG service on port 8011 (PID: $!)"

# Sports Service
export RAG_SERVICE_NAME="sports"
nohup python3 -m uvicorn rag.service:app --host 0.0.0.0 --port 8012 > logs/rag_sports.log 2>&1 &
echo "Started Sports RAG service on port 8012 (PID: $!)"

echo ""
echo "RAG Services deployed!"
echo ""
echo "Service endpoints:"
echo "  • Weather:  http://192.168.10.167:8010"
echo "  • Airports: http://192.168.10.167:8011"
echo "  • Sports:   http://192.168.10.167:8012"
echo ""
echo "Check health:"
echo "  curl http://192.168.10.167:8010/health"
echo ""
echo "View logs:"
echo "  tail -f ~/dev/project-athena/logs/rag_weather.log"
echo "  tail -f ~/dev/project-athena/logs/rag_airports.log"
echo "  tail -f ~/dev/project-athena/logs/rag_sports.log"

DEPLOY_SCRIPT

echo ""
echo "==========================================="
echo "RAG Services Deployment Complete!"
echo "==========================================="
echo ""
echo "Test the services:"
echo '  curl -X POST http://192.168.10.167:8010/query \'
echo '    -H "Content-Type: application/json" \'
echo '    -d "{\"query\": \"What is the weather today?\"}"'
echo ""