#!/bin/bash
# Test script to verify LLM metrics are being logged to database
#
# Usage:
#   ./scripts/test_metrics_logging.sh
#
# Requirements:
#   - Gateway service running on localhost:8000
#   - Admin backend running on localhost:8080 or k8s

set -e

echo "🧪 Testing LLM Metrics Database Logging"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
ADMIN_URL="${ADMIN_URL:-http://localhost:8080}"

echo "📍 Gateway URL: $GATEWAY_URL"
echo "📍 Admin URL: $ADMIN_URL"
echo ""

# Step 1: Check if services are running
echo "1️⃣  Checking service health..."

if curl -s -f "$GATEWAY_URL/health" > /dev/null; then
    echo -e "${GREEN}✓${NC} Gateway is healthy"
else
    echo -e "${RED}✗${NC} Gateway is not responding at $GATEWAY_URL"
    exit 1
fi

if curl -s -f "$ADMIN_URL/health" > /dev/null; then
    echo -e "${GREEN}✓${NC} Admin backend is healthy"
else
    echo -e "${RED}✗${NC} Admin backend is not responding at $ADMIN_URL"
    exit 1
fi

echo ""

# Step 2: Get initial metric count
echo "2️⃣  Getting initial metric count..."

METRICS_BEFORE=$(curl -s "$ADMIN_URL/api/llm-backends/metrics?limit=1000" | jq 'length')
echo -e "${GREEN}✓${NC} Current metrics in database: $METRICS_BEFORE"
echo ""

# Step 3: Make a test LLM request
echo "3️⃣  Making test LLM request via Gateway..."

TEST_QUERY="Hello, this is a test query for metric logging"

RESPONSE=$(curl -s -X POST "$GATEWAY_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"gpt-3.5-turbo\",
    \"messages\": [{\"role\": \"user\", \"content\": \"$TEST_QUERY\"}]
  }")

if [ -z "$RESPONSE" ]; then
    echo -e "${RED}✗${NC} No response from Gateway"
    exit 1
fi

ANSWER=$(echo "$RESPONSE" | jq -r '.choices[0].message.content' 2>/dev/null)

if [ -z "$ANSWER" ] || [ "$ANSWER" = "null" ]; then
    echo -e "${RED}✗${NC} Invalid response from Gateway"
    echo "Response: $RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓${NC} LLM request succeeded"
echo "   Query: $TEST_QUERY"
echo "   Answer: ${ANSWER:0:100}..."
echo ""

# Step 4: Wait for metric to be persisted
echo "4️⃣  Waiting for metric to be persisted..."

sleep 2  # Give it 2 seconds for async metric logging

echo -e "${GREEN}✓${NC} Waited 2 seconds"
echo ""

# Step 5: Check if new metric was created
echo "5️⃣  Checking for new metric in database..."

METRICS_AFTER=$(curl -s "$ADMIN_URL/api/llm-backends/metrics?limit=1000" | jq 'length')
echo "   Metrics before: $METRICS_BEFORE"
echo "   Metrics after: $METRICS_AFTER"

if [ "$METRICS_AFTER" -gt "$METRICS_BEFORE" ]; then
    echo -e "${GREEN}✓${NC} New metric was logged! (+$((METRICS_AFTER - METRICS_BEFORE)))"
else
    echo -e "${YELLOW}⚠${NC}  No new metric found (may have been logged before test started)"
fi

echo ""

# Step 6: Get the latest metric
echo "6️⃣  Fetching latest metric..."

LATEST_METRIC=$(curl -s "$ADMIN_URL/api/llm-backends/metrics?limit=1" | jq '.[0]')

if [ -z "$LATEST_METRIC" ] || [ "$LATEST_METRIC" = "null" ]; then
    echo -e "${YELLOW}⚠${NC}  No metrics in database"
else
    echo -e "${GREEN}✓${NC} Latest metric details:"
    echo "$LATEST_METRIC" | jq '{
        model: .model,
        backend: .backend,
        latency_seconds: .latency_seconds,
        tokens_generated: .tokens_generated,
        tokens_per_second: .tokens_per_second,
        timestamp: .timestamp
    }'
fi

echo ""

# Step 7: Test Orchestrator via HA conversation endpoint
echo "7️⃣  Testing Orchestrator via HA conversation endpoint..."

HA_RESPONSE=$(curl -s -X POST "$GATEWAY_URL/ha/conversation" \
  -H "Content-Type: application/json" \
  -d "{
    \"text\": \"What is the weather?\",
    \"device_id\": \"test-device\",
    \"language\": \"en\"
  }")

if [ -z "$HA_RESPONSE" ]; then
    echo -e "${RED}✗${NC} No response from HA conversation endpoint"
else
    HA_ANSWER=$(echo "$HA_RESPONSE" | jq -r '.response.speech.plain.speech' 2>/dev/null)

    if [ -z "$HA_ANSWER" ] || [ "$HA_ANSWER" = "null" ]; then
        echo -e "${YELLOW}⚠${NC}  Unexpected HA response format"
        echo "Response: $HA_RESPONSE"
    else
        echo -e "${GREEN}✓${NC} HA conversation request succeeded"
        echo "   Answer: ${HA_ANSWER:0:100}..."
    fi
fi

echo ""

# Step 8: Final verification
echo "8️⃣  Final verification..."

sleep 2  # Wait for orchestrator metric

METRICS_FINAL=$(curl -s "$ADMIN_URL/api/llm-backends/metrics?limit=1000" | jq 'length')
TOTAL_NEW_METRICS=$((METRICS_FINAL - METRICS_BEFORE))

echo "   Total new metrics logged: $TOTAL_NEW_METRICS"

if [ "$TOTAL_NEW_METRICS" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Metrics are being logged successfully!"
else
    echo -e "${YELLOW}⚠${NC}  No new metrics detected"
    echo ""
    echo "Possible causes:"
    echo "  - ADMIN_API_URL not configured correctly"
    echo "  - Admin backend database connection issues"
    echo "  - Metric logging disabled in LLM router"
    echo ""
    echo "Check logs:"
    echo "  docker logs athena-gateway | grep -i metric"
    echo "  docker logs athena-orchestrator | grep -i metric"
fi

echo ""
echo "========================================"
echo "✨ Test complete!"
echo ""

# Show recent logs from Gateway
echo "📋 Recent Gateway logs (metric-related):"
docker logs athena-gateway --tail 20 2>/dev/null | grep -i metric || echo "  (no metric logs found)"
echo ""

exit 0
