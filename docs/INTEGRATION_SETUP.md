# Athena Lite - Home Assistant Integration Setup

**Date:** November 3, 2025
**Status:** Configured and ready for testing with valid HA token

## Current Configuration

### Athena Lite Setup (Completed)

**Location:** `/mnt/nvme/athena-lite/` on jetson-01 (192.168.10.62)
**SSH Access:** `ssh jstuart@192.168.10.62`

**Configuration Updates Made:**
1. ✅ Updated `HOME_ASSISTANT_URL` to use `https://ha.xmojo.net`
2. ✅ Added SSL verification bypass for HTTPS requests
3. ✅ Created HA configuration file at `/mnt/nvme/athena-lite/config/ha_config.py`
4. ✅ Backed up original code before modifications

**Current Athena Lite Configuration:**
```python
HOME_ASSISTANT_URL = "https://ha.xmojo.net"
HOME_ASSISTANT_TOKEN = os.environ.get('HA_TOKEN', '')
```

### Home Assistant Voice Assistant (Office)

**Setup:** HA Blue device with voice assistant configured for office zone
**Access:** https://ha.xmojo.net
**API Integration:** Ready for Athena Lite integration

### Integration Strategy

Since you don't have a physical microphone for the Jetson, the integration works as follows:

**Current Approach:**
```
[HA Voice Assistant] → [HA Conversation Processing] → [Device Control]
             ↓
[Manual Athena Lite Testing] → [Jetson Processing] → [HA API] → [Device Control]
```

**Integration Benefits:**
- HA voice provides immediate voice control capability
- Athena Lite demonstrates advanced AI processing
- Both systems can coexist and complement each other
- Testing can be done via direct API calls to validate the pipeline

## Testing Approach

### Phase 1: HA Token Validation

**Issue Identified:** API token returning 401 Unauthorized
**Next Steps:**
1. Generate new long-lived access token in HA interface
2. Update token in thor cluster secrets
3. Verify API access

**Command to update token:**
```bash
# After getting new token from HA
kubectl -n automation delete secret home-assistant-credentials
kubectl -n automation create secret generic home-assistant-credentials \
  --from-literal=long-lived-token='NEW_TOKEN_HERE' \
  --from-literal=instance-url='https://ha.xmojo.net' \
  --from-literal=api-base-url='https://ha.xmojo.net/api'
```

### Phase 2: Athena Lite Testing

**Without Microphone (Text-based testing):**
```bash
# SSH to Jetson
ssh jstuart@192.168.10.62

# Navigate to project
cd /mnt/nvme/athena-lite

# Set environment variable
export HA_TOKEN="your_new_token_here"

# Test HA connection
python3 -c "from athena_lite import AthenaLite; al = AthenaLite()"

# Test command processing (simulate voice input)
python3 -c "
from athena_lite import AthenaLite
al = AthenaLite()
al.send_to_home_assistant('turn on office lights')
"
```

**With HA Voice Assistant (Office testing):**
1. Use HA's voice assistant for immediate voice control
2. Test commands: "Turn on office lights", "Set office temperature to 72"
3. Verify both systems can control the same devices

### Phase 3: Integration Verification

**Test Cases:**
1. **Basic Device Control:**
   - Athena Lite API call: Turn on office lights
   - HA Voice command: Turn on office lights
   - Verify both work independently

2. **Complex Commands:**
   - Test HA's conversation processing capabilities
   - Compare with Athena Lite's future AI processing

3. **Response Time Comparison:**
   - HA Voice: Immediate (local processing)
   - Athena Lite: 2.5-5 seconds (when fully operational)

## HA VM Migration Preparation

**When migrating HA Blue to VM, repeat these steps:**

### 1. Update DNS/Network Configuration
```bash
# If HA IP changes, update Athena Lite
ssh jstuart@192.168.10.62
cd /mnt/nvme/athena-lite
# Update HOME_ASSISTANT_URL if needed (currently using ha.xmojo.net - should be fine)
```

### 2. Generate New API Token
- Access new HA VM interface
- Go to Profile → Long-Lived Access Tokens
- Create new token for "Athena Lite Integration"
- Update thor cluster secret

### 3. Re-test Integration
```bash
# Test API access
curl -k -H "Authorization: Bearer NEW_TOKEN" https://ha.xmojo.net/api/

# Test Athena Lite connection
ssh jstuart@192.168.10.62 "cd /mnt/nvme/athena-lite && HA_TOKEN='NEW_TOKEN' python3 -c 'from athena_lite import AthenaLite; al = AthenaLite()'"
```

### 4. Verify Voice Assistant Setup
- Reconfigure voice assistant in new HA VM
- Test office voice commands
- Ensure Wyoming protocol readiness for future phases

## Integration Architecture

### Current State
```
┌─────────────────────────────────────────────────────────┐
│                    Home Assistant                       │
│                   (ha.xmojo.net)                        │
├─────────────────────────────────────────────────────────┤
│ ├─> Voice Assistant (Office)                            │
│ ├─> Conversation API                                    │
│ ├─> Device Control                                      │
│ └─> API Endpoints                                       │
├─────────────────────────────────────────────────────────┤
│                      Athena Lite                        │
│                  (jetson-01: 192.168.10.62)            │
│ ├─> Wake Word Detection (Jarvis + Athena)              │
│ ├─> Speech Recognition (Whisper)                       │
│ ├─> HA API Integration                                  │
│ └─> Response Generation                                 │
└─────────────────────────────────────────────────────────┘
```

### Future Full Project Athena
```
Wyoming Devices → Jetson Cluster → Proxmox Services → HA (Wyoming) → Device Control
    (10 zones)      (Wake Word)      (STT/TTS/LLM)     (Enhanced)
```

## Documentation for HA VM Migration

**Track these changes for VM migration:**

1. **Athena Lite Configuration:**
   - File: `/mnt/nvme/athena-lite/athena_lite.py`
   - Changed: `HOME_ASSISTANT_URL` to use `https://ha.xmojo.net`
   - Added: SSL verification bypass (`verify=False`)

2. **Thor Cluster Secrets:**
   - Secret: `automation/home-assistant-credentials`
   - Contains: `long-lived-token`, `instance-url`, `api-base-url`
   - Will need: Fresh token after VM migration

3. **CLAUDE.md Updates:**
   - Updated SSH access info (`jstuart@192.168.10.62`)
   - Updated HA URL to use domain name
   - Added integration status

## Next Immediate Steps

1. **Generate Fresh HA API Token:**
   - Access HA interface
   - Create new long-lived access token
   - Update thor cluster secret

2. **Test Athena Lite Connection:**
   - Verify API connectivity
   - Test conversation API integration
   - Validate response processing

3. **Document Working Configuration:**
   - Successful command examples
   - Performance measurements
   - Integration patterns

## Success Criteria

**Integration Complete When:**
- ✅ Athena Lite can connect to HA API
- ✅ Commands successfully sent to HA conversation API
- ✅ HA responds with appropriate device control
- ✅ Both HA voice and Athena Lite can control same devices
- ✅ Response times measured and documented
- ✅ System stable for extended testing

**Ready for Phase 1 When:**
- ✅ Integration validated and working
- ✅ Wyoming devices ordered
- ✅ Multi-zone deployment strategy confirmed
- ✅ HA VM migration completed (if applicable)

---

**Last Updated:** November 3, 2025
**Next Action:** Generate fresh HA API token and test connection
**Migration Ready:** All changes documented for HA VM migration