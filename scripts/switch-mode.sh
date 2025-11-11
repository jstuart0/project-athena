#!/bin/bash
# Switch between Baltimore and General modes

set -e

JETSON_HOST="192.168.10.62"
JETSON_USER="jstuart"
DEPLOY_DIR="/mnt/nvme/athena-lite"

NEW_MODE=$1

if [ -z "$NEW_MODE" ]; then
    echo "❌ Error: Mode required"
    echo "Usage: $0 <baltimore|general>"
    exit 1
fi

if [ "$NEW_MODE" != "baltimore" ] && [ "$NEW_MODE" != "general" ]; then
    echo "❌ Error: Invalid mode. Use 'baltimore' or 'general'"
    exit 1
fi

echo "🔄 Switching to ${NEW_MODE} mode..."

# Update .env file
ssh ${JETSON_USER}@${JETSON_HOST} "
    cd ${DEPLOY_DIR}

    # Update ATHENA_MODE in .env
    sed -i 's/^ATHENA_MODE=.*/ATHENA_MODE=${NEW_MODE}/' .env

    echo '✅ Environment updated'

    # Restart service to pick up new mode
    sudo systemctl restart ollama-proxy
    sleep 3

    # Verify new mode
    sudo systemctl status ollama-proxy --no-pager
"

# Verify mode switch
echo "✅ Verifying mode switch..."
sleep 2

MODE_CHECK=$(curl -s http://${JETSON_HOST}:11434/health | jq -r '.mode')

if [ "$MODE_CHECK" == "$NEW_MODE" ]; then
    echo "✅ Mode successfully switched to: ${NEW_MODE}"
    echo ""
    echo "📊 Current configuration:"
    curl -s http://${JETSON_HOST}:11434/health | jq '{mode, features}'
else
    echo "❌ Mode switch failed! Expected: ${NEW_MODE}, Got: ${MODE_CHECK}"
    exit 1
fi
