#!/bin/bash
# Rollback to previous Ollama Proxy deployment

set -e

JETSON_HOST="192.168.10.62"
JETSON_USER="jstuart"
DEPLOY_DIR="/mnt/nvme/athena-lite"
BACKUP_DIR="${DEPLOY_DIR}/backups"

BACKUP_TIMESTAMP=$1

if [ -z "$BACKUP_TIMESTAMP" ]; then
    echo "❌ Error: Backup timestamp required"
    echo "Usage: $0 <timestamp>"
    echo ""
    echo "Available backups:"
    ssh ${JETSON_USER}@${JETSON_HOST} "ls -lh ${BACKUP_DIR}/"
    exit 1
fi

BACKUP_FILE="${BACKUP_DIR}/proxy_backup_${BACKUP_TIMESTAMP}.tar.gz"

echo "🔄 Rolling back Ollama Proxy to backup: ${BACKUP_TIMESTAMP}..."

# Step 1: Verify backup exists
echo "📦 Checking backup..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    if [ ! -f ${BACKUP_FILE} ]; then
        echo '❌ Backup not found: ${BACKUP_FILE}'
        exit 1
    fi
    echo '✅ Backup found'
"

# Step 2: Stop service
echo "⏸️  Stopping service..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    sudo systemctl stop ollama-proxy
"

# Step 3: Restore backup
echo "📥 Restoring backup..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    cd ${DEPLOY_DIR}
    tar -xzf ${BACKUP_FILE}
    echo '✅ Backup restored'
"

# Step 4: Restart service
echo "🔄 Restarting service..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    sudo systemctl start ollama-proxy
    sleep 3
    sudo systemctl status ollama-proxy --no-pager
"

# Step 5: Verify rollback
echo "✅ Verifying rollback..."
if curl -s http://${JETSON_HOST}:11434/health | grep -q "healthy"; then
    echo "✅ Rollback successful! Service is healthy."
    curl -s http://${JETSON_HOST}:11434/health | jq '.'
else
    echo "❌ Rollback verification failed!"
    exit 1
fi
