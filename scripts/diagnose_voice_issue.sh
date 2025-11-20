#!/bin/bash
# Diagnostic script for voice pipeline issues

set -e

HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4NjNhNWIwMDM3OTE0ODE1YTVlODkyZWUwNTMxMmIwZCIsImlhdCI6MTc2MjE4MzY0MiwiZXhwIjoyMDc3NTQzNjQyfQ.M-vSeDlQl3NvGrpeZ35QKat8OjTXA2z3559Hy96EC4A"

echo "======================================"
echo "Voice Pipeline Diagnostic"
echo "======================================"
echo ""

echo "1. Checking Voice PE Device Status..."
curl -sk -H "Authorization: Bearer $HA_TOKEN" \
    "https://192.168.10.168:8123/api/states/assist_satellite.home_assistant_voice_0a2296_assist_satellite" 2>&1 | \
    jq -r '{state: .state, pipeline: .attributes.pipeline_entity_id, last_changed: .last_changed}' 2>/dev/null || echo "Failed to query device"
echo ""

echo "2. Checking configured assistants..."
curl -sk -H "Authorization: Bearer $HA_TOKEN" \
    "https://192.168.10.168:8123/api/states/select.home_assistant_voice_0a2296_assistant" 2>&1 | \
    jq -r '{current: .state, options: .attributes.options}' 2>/dev/null || echo "Failed to query assistants"
echo ""

echo "3. Testing Wyoming STT (Whisper) connectivity..."
if nc -z 192.168.10.167 10300 2>/dev/null; then
    echo "✓ Can reach Whisper STT on 192.168.10.167:10300"
else
    echo "✗ Cannot reach Whisper STT"
fi
echo ""

echo "4. Testing Wyoming TTS (Piper) connectivity..."
if nc -z 192.168.10.167 10200 2>/dev/null; then
    echo "✓ Can reach Piper TTS on 192.168.10.167:10200"
else
    echo "✗ Cannot reach Piper TTS"
fi
echo ""

echo "5. Checking if Wyoming processes are running on Mac Studio..."
ssh jstuart@192.168.10.167 "ps aux | grep -E 'wyoming-(faster-whisper|piper)' | grep -v grep" 2>/dev/null || echo "No Wyoming processes found"
echo ""

echo "6. Checking recent HA logs for voice/wyoming activity..."
echo "(This requires SSH access to HA server)"
echo ""

echo "======================================"
echo "Next Steps"
echo "======================================"
echo ""
echo "If Wyoming services are running but device isn't using them:"
echo "1. In HA UI, go to Settings → Voice assistants"
echo "2. Check if there's a pipeline that uses Wyoming STT/TTS"
echo "3. If not, create one with:"
echo "   - STT: Wyoming (Whisper)"
echo "   - Conversation: Extended OpenAI Conversation"
echo "   - TTS: Wyoming (Piper)"
echo "4. Then assign this pipeline to your Voice PE device"
echo ""
