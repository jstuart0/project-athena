#!/bin/bash
# Real-time monitoring of Ollama Proxy

JETSON_HOST="192.168.10.62"

echo "📊 Ollama Proxy Monitor - ${JETSON_HOST}"
echo "Press Ctrl+C to exit"
echo ""

while true; do
    clear

    echo "=== Health Status ==="
    curl -s http://${JETSON_HOST}:11434/health | jq '{
        status,
        mode,
        ollama_connected,
        features
    }'

    echo ""
    echo "=== Performance Metrics ==="
    curl -s http://${JETSON_HOST}:11434/metrics | jq '{
        latency_ms: .performance.latency_ms,
        requests: .performance.requests,
        models: .performance.models,
        cache_hit_rate: .cache.hit_rate
    }'

    echo ""
    echo "=== System Resources ==="
    ssh jstuart@${JETSON_HOST} "
        echo 'CPU Usage:'
        top -bn1 | grep 'Cpu(s)' | awk '{print \$2}' | awk -F'%' '{print \$1\"%\"}'

        echo 'Memory:'
        free -h | awk '/^Mem:/ {print \$3 \" / \" \$2}'

        echo 'Disk (NVMe):'
        df -h /mnt/nvme | awk 'NR==2 {print \$3 \" / \" \$2 \" (\" \$5 \" used)\"}'
    " 2>/dev/null

    echo ""
    echo "=== Service Status ==="
    ssh jstuart@${JETSON_HOST} "systemctl is-active ollama-proxy ollama" 2>/dev/null

    echo ""
    echo "Last updated: $(date)"

    sleep 5
done
