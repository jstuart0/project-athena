#!/bin/bash
# Deploy Ollama Proxy to Jetson with rollback capability

set -e  # Exit on error

JETSON_HOST="192.168.10.62"
JETSON_USER="jstuart"
DEPLOY_DIR="/mnt/nvme/athena-lite"
BACKUP_DIR="${DEPLOY_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 Deploying Ollama Proxy to ${JETSON_HOST}..."

# Step 1: Create backup of current deployment
echo "📦 Creating backup..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    mkdir -p ${BACKUP_DIR}
    if [ -f ${DEPLOY_DIR}/ollama_proxy.py ]; then
        tar -czf ${BACKUP_DIR}/proxy_backup_${TIMESTAMP}.tar.gz \
            -C ${DEPLOY_DIR} \
            ollama_proxy.py \
            validation.py \
            caching.py \
            config/ \
            .env 2>/dev/null || true
        echo '✅ Backup created: proxy_backup_${TIMESTAMP}.tar.gz'
    fi
"

# Step 2: Copy new files to Jetson
echo "📤 Copying new files..."
scp -r src/jetson/* ${JETSON_USER}@${JETSON_HOST}:${DEPLOY_DIR}/

# Step 3: Install Python dependencies
echo "📦 Installing dependencies..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    cd ${DEPLOY_DIR}
    pip3 install -r requirements.txt --user
"

# Step 4: Install systemd service files
echo "⚙️  Installing systemd services..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    sudo cp ${DEPLOY_DIR}/systemd/ollama-proxy.service /etc/systemd/system/
    sudo mkdir -p /etc/systemd/system/ollama.service.d/
    sudo cp ${DEPLOY_DIR}/systemd/ollama.service.d/override.conf /etc/systemd/system/ollama.service.d/
    sudo systemctl daemon-reload
"

# Step 5: Restart services
echo "🔄 Restarting services..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    # Restart Ollama with new port configuration
    sudo systemctl restart ollama
    sleep 5

    # Enable and start proxy service
    sudo systemctl enable ollama-proxy
    sudo systemctl restart ollama-proxy
    sleep 3

    # Check service status
    sudo systemctl status ollama-proxy --no-pager
"

# Step 6: Verify deployment
echo "✅ Verifying deployment..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://${JETSON_HOST}:11434/health | grep -q "healthy"; then
        echo "✅ Deployment successful! Service is healthy."

        # Show health status
        echo ""
        echo "📊 Service Health:"
        curl -s http://${JETSON_HOST}:11434/health | jq '.'

        exit 0
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⏳ Waiting for service to be healthy (attempt ${RETRY_COUNT}/${MAX_RETRIES})..."
    sleep 2
done

echo "❌ Deployment verification failed! Service is not healthy."
echo "🔄 Run './scripts/rollback-proxy.sh ${TIMESTAMP}' to rollback."
exit 1
