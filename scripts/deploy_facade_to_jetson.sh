#!/bin/bash
# Deploy facade code from src/jetson to Jetson at /mnt/nvme/athena-lite

set -e

JETSON_USER="jstuart"
JETSON_HOST="192.168.10.62"
JETSON_PATH="/mnt/nvme/athena-lite"
LOCAL_SRC="src/jetson"

echo "🚀 Deploying facade to Jetson..."

# 1. Create facade directory structure on Jetson
echo "📁 Creating directory structure..."
ssh ${JETSON_USER}@${JETSON_HOST} "mkdir -p ${JETSON_PATH}/facade/handlers ${JETSON_PATH}/facade/config ${JETSON_PATH}/facade/utils"

# 2. Copy facade module
echo "📦 Copying facade module..."
scp -r ${LOCAL_SRC}/facade/* ${JETSON_USER}@${JETSON_HOST}:${JETSON_PATH}/facade/

# 3. Copy main integration file
echo "📄 Copying main facade integration..."
scp ${LOCAL_SRC}/facade_integration.py ${JETSON_USER}@${JETSON_HOST}:${JETSON_PATH}/

# 4. Copy requirements.txt
echo "📋 Copying requirements..."
scp ${LOCAL_SRC}/requirements.txt ${JETSON_USER}@${JETSON_HOST}:${JETSON_PATH}/

# 5. Install dependencies on Jetson
echo "📦 Installing dependencies on Jetson..."
ssh ${JETSON_USER}@${JETSON_HOST} "cd ${JETSON_PATH} && pip3 install -r requirements.txt"

# 6. Set executable permissions
echo "🔐 Setting permissions..."
ssh ${JETSON_USER}@${JETSON_HOST} "chmod +x ${JETSON_PATH}/facade_integration.py"

# 7. Restart facade service (if running as systemd service)
echo "🔄 Restarting facade service..."
ssh ${JETSON_USER}@${JETSON_HOST} "sudo systemctl restart ollama-facade || echo '⚠️  Service not configured yet, skip restart'"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📍 Next steps:"
echo "1. Verify .env file has API keys: ssh ${JETSON_USER}@${JETSON_HOST} 'cat ${JETSON_PATH}/.env'"
echo "2. Test health endpoint: curl http://192.168.10.62:11434/health"
echo "3. Test a weather query via facade"
echo ""
echo "🔑 Required API keys in .env:"
echo "   - OPENWEATHER_API_KEY (Phase 1)"
echo "   - TMDB_API_KEY (Phase 3)"
echo "   - EVENTBRITE_API_KEY (Phase 2)"
echo "   - TICKETMASTER_API_KEY (Phase 2)"
echo "   - NEWSAPI_KEY (Phase 4)"
echo "   - ALPHAVANTAGE_KEY (Phase 4)"
echo "   - FLIGHTAWARE_API_KEY (Phase 2)"
echo ""
