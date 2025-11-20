#!/bin/bash
# Verification script for Voice PE device pipeline
# Tests Wyoming protocol services and Home Assistant integration

set -e

echo "======================================"
echo "Voice Pipeline Verification"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Home Assistant API token
HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4NjNhNWIwMDM3OTE0ODE1YTVlODkyZWUwNTMxMmIwZCIsImlhdCI6MTc2MjE4MzY0MiwiZXhwIjoyMDc3NTQzNjQyfQ.M-vSeDlQl3NvGrpeZ35QKat8OjTXA2z3559Hy96EC4A"
HA_URL="https://192.168.10.168:8123"

echo "1. Testing Gateway Health..."
if curl -s http://192.168.10.167:8000/health | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Gateway is healthy"
else
    echo -e "${RED}✗${NC} Gateway is not responding"
fi
echo ""

echo "2. Testing Whisper STT Service (Wyoming)..."
if nc -z 192.168.10.167 10300 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Whisper STT port 10300 is accessible"
else
    echo -e "${RED}✗${NC} Whisper STT port 10300 is not accessible"
fi
echo ""

echo "3. Testing Piper TTS Service (Wyoming)..."
if nc -z 192.168.10.167 10200 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Piper TTS port 10200 is accessible"
else
    echo -e "${RED}✗${NC} Piper TTS port 10200 is not accessible"
fi
echo ""

echo "4. Checking Home Assistant Wyoming integrations..."
WYOMING_COUNT=$(curl -sk -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_URL/api/config/config_entries" 2>/dev/null | \
    jq '[.[] | select(.domain == "wyoming")] | length' 2>/dev/null || echo "0")

if [ "$WYOMING_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found $WYOMING_COUNT Wyoming integration(s) in Home Assistant"

    # List Wyoming integrations
    curl -sk -H "Authorization: Bearer $HA_TOKEN" \
        "$HA_URL/api/config/config_entries" 2>/dev/null | \
        jq -r '.[] | select(.domain == "wyoming") | "  - \(.title) (\(.entry_id))"' 2>/dev/null || true
else
    echo -e "${YELLOW}⚠${NC}  No Wyoming integrations found in Home Assistant"
    echo "   You need to add Wyoming integrations manually in the HA UI"
    echo "   Go to: Settings → Devices & Services → Add Integration → Wyoming Protocol"
fi
echo ""

echo "5. Checking Voice Assistant Pipelines..."
PIPELINE_COUNT=$(curl -sk -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_URL/api/conversation/agent/info" 2>/dev/null | \
    jq 'length' 2>/dev/null || echo "0")

if [ "$PIPELINE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found $PIPELINE_COUNT voice assistant pipeline(s)"
else
    echo -e "${YELLOW}⚠${NC}  No voice assistant pipelines found"
fi
echo ""

echo "6. Checking for Voice PE devices (Wyoming satellites)..."
SATELLITE_COUNT=$(curl -sk -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_URL/api/config/device_registry" 2>/dev/null | \
    jq '[.[] | select(.model | contains("Voice") or contains("wyoming") or contains("satellite"))] | length' 2>/dev/null || echo "0")

if [ "$SATELLITE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found $SATELLITE_COUNT potential Voice PE device(s)"

    # List devices
    curl -sk -H "Authorization: Bearer $HA_TOKEN" \
        "$HA_URL/api/config/device_registry" 2>/dev/null | \
        jq -r '.[] | select(.model | contains("Voice") or contains("wyoming") or contains("satellite")) | "  - \(.name) (\(.model))"' 2>/dev/null || true
else
    echo -e "${YELLOW}⚠${NC}  No Voice PE devices found"
    echo "   Make sure your Voice PE devices are powered on and connected to the network"
fi
echo ""

echo "======================================"
echo "Summary"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. If Wyoming integrations are missing, add them in HA UI:"
echo "   Settings → Devices & Services → Add Integration → Wyoming Protocol"
echo "   - Add Whisper STT: 192.168.10.167:10300"
echo "   - Add Piper TTS: 192.168.10.167:10200"
echo ""
echo "2. Configure voice pipeline:"
echo "   Settings → Voice assistants → Create/Edit pipeline"
echo "   - STT: Whisper STT"
echo "   - Conversation: Extended OpenAI Conversation"
echo "   - TTS: Piper TTS"
echo ""
echo "3. Assign pipeline to your Voice PE devices"
echo ""
