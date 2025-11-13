# Project Athena - Remaining Tasks

**Last Updated:** November 12, 2025 03:50 AM
**Status:** Infrastructure Complete, Awaiting User Configuration

---

## Priority 1: Voice Integration (USER ACTION REQUIRED)

These tasks require Home Assistant UI access and cannot be automated. Estimated total time: 20-30 minutes.

### Task 1: Configure OpenAI Conversation Integration

**Status:** ⏸️ Blocked - Requires HA UI Access
**Estimated Time:** 10 minutes
**Guide:** `HA_VOICE_SETUP_GUIDE.md` (Part 1)

**Description:**
Configure two OpenAI Conversation integrations in Home Assistant to enable Athena's AI capabilities.

**Steps:**
1. Navigate to HA Settings → Devices & Services → Add Integration
2. Search for "OpenAI Conversation"
3. Create first integration: "Athena Fast"
   - API Key: `sk-athena-9fd1ef6c8ed1eb0278f5133095c60271`
   - Base URL: `http://192.168.10.167:8001/v1`
   - Model: `athena-fast`
   - Max Tokens: 500, Temperature: 0.7
4. Create second integration: "Athena Medium"
   - Same API key and base URL
   - Model: `athena-medium`
   - Max Tokens: 500, Temperature: 0.7

**Success Criteria:**
- Both integrations show as "Configured" in Devices & Services
- No connection errors
- Test endpoint responds (documented in guide)

**Dependencies:** None
**Blocks:** Task 2, Task 3

---

### Task 2: Configure Wyoming Integration for External Whisper

**Status:** ⏸️ Blocked - Requires HA UI Access
**Estimated Time:** 5 minutes
**Guide:** `HA_VOICE_SETUP_GUIDE.md` (Part 1 - Wyoming section)

**Description:**
Add Wyoming Protocol integration to connect to the external Whisper STT service running on Mac Studio (solves the ODROID memory crash issue).

**Steps:**
1. Navigate to HA Settings → Devices & Services → Add Integration
2. Search for "Wyoming Protocol"
3. Configure:
   - Host: `192.168.10.167`
   - Port: `10300`
   - Name: `Wyoming Whisper (Mac Studio)`
4. Verify integration is added successfully

**Success Criteria:**
- Wyoming integration shows as connected
- Whisper service appears as option in Assist Pipeline STT dropdown
- No connection timeouts

**Dependencies:** External Whisper service running (✅ Complete)
**Blocks:** Task 3

**Note:** This replaces the crashed local Faster-Whisper add-on that was running out of memory on the ODROID.

---

### Task 3: Create Assist Pipelines

**Status:** ⏸️ Blocked - Requires HA UI Access
**Estimated Time:** 10 minutes
**Guide:** `HA_VOICE_SETUP_GUIDE.md` (Part 2)

**Description:**
Create two voice assistant pipelines combining STT (Whisper), AI (Athena), and TTS (Piper).

**Steps:**
1. Navigate to HA Settings → Voice Assistants → Add Pipeline

2. Create Pipeline #1: "Athena Control"
   - Language: English (US)
   - Speech-to-Text: `Wyoming Whisper (Mac Studio)`
   - Conversation Agent: `Athena Fast`
   - Text-to-Speech: `piper` (local)
   - Voice: `en_US-lessac-medium` (or preferred)
   - Purpose: Quick commands, device control

3. Create Pipeline #2: "Athena Knowledge"
   - Language: English (US)
   - Speech-to-Text: `Wyoming Whisper (Mac Studio)`
   - Conversation Agent: `Athena Medium`
   - Text-to-Speech: `piper` (local)
   - Voice: Same as Pipeline #1
   - Purpose: Complex queries, reasoning

4. Set "Athena Control" as default pipeline (star icon)

**Success Criteria:**
- Both pipelines created and visible
- Athena Control set as default
- Can select pipelines in Assist UI

**Dependencies:** Task 1 (OpenAI integrations), Task 2 (Wyoming)
**Blocks:** Task 4

---

### Task 4: Test Voice Integration End-to-End

**Status:** ⏸️ Blocked - Requires HA UI Access
**Estimated Time:** 10 minutes
**Guide:** `HA_VOICE_SETUP_GUIDE.md` (Part 3 - Testing)

**Description:**
Verify complete voice pipeline from speech recognition through AI processing to response.

**Test Cases:**

**Test 1: Text-only query**
- Open HA Assist interface
- Select "Athena Control" pipeline
- Type: "What time is it?"
- Expected: Text response with current time (<2s)

**Test 2: Voice query (if microphone available)**
- Click microphone icon
- Speak: "What time is it?"
- Expected: Spoken response with current time (2-5s total)

**Test 3: Complex query with RAG**
- Switch to "Athena Knowledge" pipeline
- Ask: "What is the weather in Baltimore?"
- Expected: Current weather data from live API (0.8-3s)

**Test 4: Device control**
- Select "Athena Control"
- Say/type: "Turn on the living room lights"
- Expected: Device control executed + confirmation

**Success Criteria:**
- All test queries complete successfully
- Response times within targets (2-5s end-to-end)
- No errors in HA logs
- Voice recognition working accurately

**Dependencies:** Task 3 (Pipelines configured)
**Blocks:** None - Phase 1 complete!

---

## Priority 2: Optional Enhancements

These tasks improve performance but system works without them.

### Task 5: Enable Mac mini SSH and Deploy Services

**Status:** ⏸️ Optional - Requires Physical Access
**Estimated Time:** 15 minutes
**Priority:** Low

**Description:**
Enable SSH on Mac mini and deploy Qdrant (vector DB) and Redis (cache) services.

**Benefits:**
- Faster query responses with Redis caching
- Vector similarity search with Qdrant for better RAG
- Historical conversation context

**Steps:**
1. Enable SSH on Mac mini (192.168.10.181)
   - System Settings → Sharing → Remote Login
   - Or via physical access

2. Deploy services:
   ```bash
   # Copy docker-compose file
   scp deployment/mac-mini/docker-compose.yml user@192.168.10.181:~/athena/

   # SSH and deploy
   ssh user@192.168.10.181
   cd ~/athena
   docker compose up -d
   ```

3. Verify in admin interface:
   - Navigate to https://athena-admin.xmojo.net
   - Check Mac mini services show as healthy
   - Should see 18/18 services healthy

**Success Criteria:**
- Qdrant accessible at http://192.168.10.181:6333
- Redis accessible at http://192.168.10.181:6379
- Admin interface shows both services healthy
- No impact to existing Mac Studio services

**Dependencies:** None (system works without this)
**Blocks:** None

**Current Workaround:** System gracefully degrades without these services

---

## Priority 3: Future Work (Phase 2)

These are planned for later phases.

### HA Voice Devices Deployment
- **Status:** Phase 2
- **Hardware:** 10x Wyoming voice devices
- **Zones:** Office, Kitchen, Bedrooms, Bathrooms, Living areas
- **Blocked by:** Hardware procurement
- **Guide:** Phase 2 documentation (to be created)

### Multi-User Voice Profiles
- **Status:** Phase 3/4
- **Features:** Voice identification, personalized responses
- **Blocked by:** Phase 2 completion

---

## Documentation Status

**✅ Complete:**
- `HA_VOICE_SETUP_GUIDE.md` - Step-by-step HA configuration
- `ADMIN_INTERFACE_DEPLOYED.md` - Admin interface details
- `PHASE1_COMPLETE.md` - Phase 1 implementation summary
- `PHASE1_VOICE_INTEGRATION_COMPLETE.md` - Voice integration status
- `DEPLOYMENT.md` - Operations guide
- `TROUBLESHOOTING.md` - Problem resolution

**⏸️ Pending:**
- Wiki documentation (if desired)
- Video walkthroughs (if desired)

---

## Quick Reference

**Admin Interface:** https://athena-admin.xmojo.net
- View all service status
- Test queries interactively
- Monitor Mac Studio and Mac mini services

**Key Services:**
- Orchestrator: http://192.168.10.167:8001
- Wyoming Whisper: http://192.168.10.167:10300
- Ollama: http://192.168.10.167:11434

**Credentials:**
Stored in thor cluster:
```bash
kubectl -n automation get secret project-athena-credentials -o yaml
```

---

## Timeline

**Completed (November 11-12, 2025):**
- ✅ Phase 1 core services deployment
- ✅ 14 Mac Studio services running
- ✅ Wyoming Whisper external deployment (fixed ODROID crash)
- ✅ Admin interface enhancement and deployment
- ✅ Comprehensive documentation

**Remaining (Est. 20-30 minutes user time):**
- ⏸️ Task 1: OpenAI Conversation (10 min)
- ⏸️ Task 2: Wyoming Integration (5 min)
- ⏸️ Task 3: Assist Pipelines (10 min)
- ⏸️ Task 4: Testing (10 min)

**Optional:**
- ⏸️ Task 5: Mac mini services (15 min)

---

## Next Steps

**When you're ready to complete voice integration:**

1. Read `HA_VOICE_SETUP_GUIDE.md` for detailed instructions
2. Follow Tasks 1-4 in order (dependencies listed above)
3. Each task has step-by-step instructions in the guide
4. Test after each task to catch issues early
5. Reference `TROUBLESHOOTING.md` if you encounter problems

**Total estimated time:** 20-30 minutes from start to finish

**You're 85% done!** All infrastructure is deployed and working. The remaining 15% is just HA UI configuration.
