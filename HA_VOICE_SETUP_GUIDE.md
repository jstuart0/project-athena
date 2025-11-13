# Home Assistant Voice Setup Guide - Project Athena

Complete step-by-step guide for configuring OpenAI Conversation and Assist Pipelines in Home Assistant.

## Prerequisites ✅

Before starting, verify:
- ✅ Home Assistant is accessible at https://ha.xmojo.net
- ✅ Piper TTS add-on installed and running (v2.1.1)
- ✅ Faster Whisper add-on installed and running (v3.0.1)
- ✅ Mac Studio orchestrator running at http://192.168.10.167:8001

## Part 1: Configure OpenAI Conversation Integration

### Step 1: Access Home Assistant

1. Open your browser and go to: **https://ha.xmojo.net**
2. Log in with your credentials

### Step 2: Navigate to Integrations

1. Click on **Settings** (gear icon) in the left sidebar
2. Click on **Devices & Services**
3. You should see the "Integrations" tab

### Step 3: Add OpenAI Conversation Integration

1. Click the **+ ADD INTEGRATION** button (blue button, bottom right)
2. In the search box, type: `OpenAI Conversation`
3. Click on **OpenAI Conversation** when it appears

**Important:** If you don't see "OpenAI Conversation" in the list, make sure:
- Your Home Assistant is updated to version 2025.10.3 or later
- You're using the UI to add it (NOT YAML configuration)

### Step 4: Configure the Integration - First Instance (Fast Model)

A dialog will appear asking for configuration. Enter these values:

**Configuration for Athena Fast:**

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | `Athena Fast` | This will appear in your pipeline options |
| **API Key** | `sk-athena-9fd1ef6c8ed1eb0278f5133095c60271` | Custom API key for Mac Studio |
| **API Base URL** | `http://192.168.10.167:8001/v1` | Mac Studio orchestrator endpoint |
| **Model** | `athena-fast` | Fast model for quick commands |
| **Max Tokens** | `500` | Maximum response length |
| **Temperature** | `0.7` | Creativity level (0.0 = deterministic, 1.0 = creative) |
| **Top P** | `1.0` | Leave default |
| **Presence Penalty** | `0.0` | Leave default |
| **Frequency Penalty** | `0.0` | Leave default |

**Screenshot Reference:**
```
┌─────────────────────────────────────────────┐
│ Configure OpenAI Conversation               │
├─────────────────────────────────────────────┤
│ Name:                                       │
│ [Athena Fast                           ]    │
│                                             │
│ API Key:                                    │
│ [sk-athena-9fd1ef6c8ed1eb0278f5133095c... ]│
│                                             │
│ API Base URL (optional):                    │
│ [http://192.168.10.167:8001/v1         ]    │
│                                             │
│ Model:                                      │
│ [athena-fast                           ]    │
│                                             │
│ Max Tokens:                                 │
│ [500                                   ]    │
│                                             │
│ Temperature:                                │
│ [0.7                                   ]    │
│                                             │
│         [Cancel]            [Submit]        │
└─────────────────────────────────────────────┘
```

Click **Submit**

### Step 5: Add Second Instance (Medium Model)

1. Click **+ ADD INTEGRATION** again
2. Search for and select **OpenAI Conversation** again
3. Configure with these values:

**Configuration for Athena Medium:**

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | `Athena Medium` | For complex queries and reasoning |
| **API Key** | `sk-athena-9fd1ef6c8ed1eb0278f5133095c60271` | Same API key |
| **API Base URL** | `http://192.168.10.167:8001/v1` | Same orchestrator endpoint |
| **Model** | `athena-medium` | Medium model for complex tasks |
| **Max Tokens** | `500` | Maximum response length |
| **Temperature** | `0.7` | Creativity level |
| **Top P** | `1.0` | Leave default |
| **Presence Penalty** | `0.0` | Leave default |
| **Frequency Penalty** | `0.0` | Leave default |

Click **Submit**

### Step 6: Verify Integrations

After adding both, you should see:

```
Integrations
├─ OpenAI Conversation (Athena Fast)
│  └─ 1 device
└─ OpenAI Conversation (Athena Medium)
   └─ 1 device
```

Click on each integration to verify:
- Status shows as "Connected" or "Configured"
- No error messages appear

---

## Part 2: Create Assist Pipelines

Assist Pipelines combine STT (Speech-to-Text), Conversation Agent, and TTS (Text-to-Speech) into complete voice workflows.

### Step 1: Navigate to Voice Assistants

1. Click on **Settings** (gear icon) in the left sidebar
2. Click on **Voice assistants**
3. You should see the "Assist" section

### Step 2: Create Pipeline #1 - Athena Control (Fast)

1. Click **+ ADD PIPELINE** (or **Add** if no pipelines exist)

2. Fill in the configuration:

**Pipeline Configuration - Athena Control:**

| Field | Value | Purpose |
|-------|-------|---------|
| **Name** | `Athena Control` | Pipeline name |
| **Language** | `English (US)` or your preferred language | |
| **Speech-to-Text** | `faster-whisper` | Whisper add-on for STT |
| **Conversation agent** | `Athena Fast` | Fast model you just configured |
| **Text-to-Speech** | `piper` | Piper add-on for TTS |
| **Voice** | Select a Piper voice (e.g., `en_US-lessac-medium`) | Natural-sounding voice |

**Screenshot Reference:**
```
┌─────────────────────────────────────────────┐
│ Create Pipeline                             │
├─────────────────────────────────────────────┤
│ Name:                                       │
│ [Athena Control                        ]    │
│                                             │
│ Language:                                   │
│ [English (US)                    ▼]         │
│                                             │
│ Speech-to-Text:                             │
│ [faster-whisper                  ▼]         │
│                                             │
│ Conversation agent:                         │
│ [Athena Fast                     ▼]         │
│                                             │
│ Text-to-Speech:                             │
│ [piper                           ▼]         │
│                                             │
│ Voice:                                      │
│ [en_US-lessac-medium             ▼]         │
│                                             │
│         [Cancel]            [Create]        │
└─────────────────────────────────────────────┘
```

3. Click **Create**

**Usage Notes for Athena Control:**
- Use for: Quick commands, device control, simple queries
- Examples:
  - "Turn on the living room lights"
  - "Set thermostat to 72"
  - "What's the time?"
- Expected response time: 2-3 seconds

### Step 3: Create Pipeline #2 - Athena Knowledge (Medium)

1. Click **+ ADD PIPELINE** again

2. Fill in the configuration:

**Pipeline Configuration - Athena Knowledge:**

| Field | Value | Purpose |
|-------|-------|---------|
| **Name** | `Athena Knowledge` | Pipeline name |
| **Language** | `English (US)` or your preferred language | |
| **Speech-to-Text** | `faster-whisper` | Whisper add-on for STT |
| **Conversation agent** | `Athena Medium` | Medium model for complex queries |
| **Text-to-Speech** | `piper` | Piper add-on for TTS |
| **Voice** | Same voice as Pipeline #1 | Consistency |

3. Click **Create**

**Usage Notes for Athena Knowledge:**
- Use for: Complex queries, explanations, reasoning tasks
- Examples:
  - "Explain how my solar panels work"
  - "What's the weather forecast for this week?"
  - "Tell me about the history of this house"
- Expected response time: 3-5 seconds

### Step 4: Set Default Pipeline (Optional)

1. You'll see a list of your pipelines
2. You can set one as default by clicking the **star icon** next to it
3. Recommended: Set **Athena Control** as default for most common use

**Your pipeline list should now show:**
```
Pipelines
├─ ⭐ Athena Control (Default)
│  └─ STT: faster-whisper, Agent: Athena Fast, TTS: piper
└─ Athena Knowledge
   └─ STT: faster-whisper, Agent: Athena Medium, TTS: piper
```

---

## Part 3: Test Your Setup

### Test 1: Test the Conversation Agents Directly

Before testing voice, verify the conversation agents work:

1. Go to **Settings** → **Devices & Services**
2. Find **OpenAI Conversation (Athena Fast)**
3. Click on it
4. Look for a "Try it" or test button (if available)
5. Type a test message: "What's the weather?"
6. Verify you get a response

Repeat for **Athena Medium**

### Test 2: Test via Assist (Text)

1. Click the **Assist** icon in the Home Assistant UI (speech bubble icon, usually bottom right)
2. Or go to **Settings** → **Voice assistants** → **Assist**
3. Select **Athena Control** from the pipeline dropdown
4. Type a command: "Turn on the lights"
5. Verify:
   - You get a text response
   - The command executes (if you have devices)

### Test 3: Test Voice Input (if you have microphone)

1. Open Assist
2. Select **Athena Control** pipeline
3. Click the **microphone icon**
4. Say: "What time is it?"
5. Verify:
   - Your speech is transcribed
   - You get a spoken response
   - Response time is under 5 seconds

### Test 4: Test Both Pipelines

**Test Athena Control (Fast):**
```
You: "Turn on the kitchen lights"
Expected: Quick response, ~2-3 seconds
```

**Test Athena Knowledge (Medium):**
```
You: "Tell me about quantum computing"
Expected: Detailed response, ~3-5 seconds
```

---

## Troubleshooting

### Issue: "OpenAI Conversation" not appearing in integrations

**Solution:**
- Update Home Assistant to version 2025.10.3 or later
- Restart Home Assistant Core
- Clear browser cache

**Check HA version:**
```bash
ssh -i /tmp/ha_ssh_key2 -p 23 root@192.168.10.168
ha core info
```

### Issue: "Failed to connect" when adding integration

**Causes and solutions:**

1. **Mac Studio orchestrator not running**
   ```bash
   ssh jstuart@192.168.10.167
   docker ps | grep orchestrator
   ```

2. **Incorrect API Base URL**
   - Verify: `http://192.168.10.167:8001/v1` (with `/v1` at the end)
   - Test from HA server:
     ```bash
     ssh -i /tmp/ha_ssh_key2 -p 23 root@192.168.10.168
     curl http://192.168.10.167:8001/v1/models
     ```

3. **Firewall blocking connection**
   - Verify HA can reach Mac Studio on port 8001

### Issue: "Invalid API key" error

**Solution:**
- Double-check the API key: `sk-athena-9fd1ef6c8ed1eb0278f5133095c60271`
- Verify it's entered exactly (no extra spaces)
- Get from Kubernetes if needed:
  ```bash
  kubectl -n automation get secret project-athena-credentials -o jsonpath='{.data.openai-api-key}' | base64 -d
  ```

### Issue: Pipeline doesn't respond

**Check each component:**

1. **STT (Whisper):**
   ```bash
   ssh -i /tmp/ha_ssh_key2 -p 23 root@192.168.10.168
   ha addons info core_whisper
   ha addons logs core_whisper
   ```

2. **TTS (Piper):**
   ```bash
   ha addons info core_piper
   ha addons logs core_piper
   ```

3. **Conversation Agent:**
   - Check integration status in UI
   - Test with text input first
   - Check Mac Studio logs:
     ```bash
     ssh jstuart@192.168.10.167
     docker logs orchestrator
     ```

### Issue: Response too slow (>10 seconds)

**Causes:**

1. **Using wrong model**
   - Athena Fast should be 2-3 seconds
   - Athena Medium should be 3-5 seconds
   - Check which model is configured

2. **Mac Studio overloaded**
   - Check Mac Studio resources:
     ```bash
     ssh jstuart@192.168.10.167
     docker stats
     ```

3. **Network latency**
   - Ping test from HA to Mac Studio:
     ```bash
     ssh -i /tmp/ha_ssh_key2 -p 23 root@192.168.10.168
     ping -c 5 192.168.10.167
     ```

### Issue: Voice not recognized (Whisper)

**Solutions:**

1. **Check microphone permissions** in browser
2. **Speak clearly** with less background noise
3. **Check Whisper add-on:**
   ```bash
   ha addons restart core_whisper
   ha addons logs core_whisper
   ```

4. **Try different Whisper model** (if too slow/inaccurate):
   - Whisper settings → Model size
   - Options: tiny, base, small, medium, large
   - Current: tiny.en (fastest, good for English)

---

## Advanced Configuration

### Customize Voice (Piper TTS)

Available Piper voices:
- `en_US-lessac-medium` - Natural, clear (recommended)
- `en_US-amy-medium` - Friendly, casual
- `en_US-ryan-medium` - Male voice
- `en_GB-alba-medium` - British accent

To change:
1. Go to pipeline settings
2. Change **Voice** dropdown
3. Save

### Adjust Model Temperature

Temperature controls randomness:
- `0.0` - Very deterministic, consistent answers
- `0.7` - Balanced (recommended)
- `1.0` - Creative, varied responses

To adjust:
1. Go to **Settings** → **Devices & Services**
2. Find **OpenAI Conversation** integration
3. Click **Configure**
4. Adjust **Temperature** slider
5. Save

### Add More Models

You can add additional conversation agents:

1. Add another **OpenAI Conversation** integration
2. Use different model names:
   - `athena-mini` - Fastest, simplest queries
   - `athena-fast` - Quick commands
   - `athena-medium` - Complex reasoning
   - `athena-large` - Most capable (if deployed)

---

## Expected Results

### After Successful Setup

**Integrations page should show:**
```
✅ OpenAI Conversation (Athena Fast)
   Status: Configured

✅ OpenAI Conversation (Athena Medium)
   Status: Configured
```

**Voice Assistants page should show:**
```
✅ Athena Control (Default)
   STT: faster-whisper
   Agent: Athena Fast
   TTS: piper

✅ Athena Knowledge
   STT: faster-whisper
   Agent: Athena Medium
   TTS: piper
```

### Test Commands to Try

**Quick Commands (Athena Control):**
- "What time is it?"
- "Turn on the lights"
- "Set temperature to 72"
- "Is the garage door open?"

**Knowledge Queries (Athena Knowledge):**
- "What's the weather forecast?"
- "Tell me about solar energy"
- "Explain how my thermostat works"
- "What's the news today?"

**Expected Performance:**
- Speech recognition: Instant to 1 second
- LLM processing: 1-3 seconds (fast) or 2-4 seconds (medium)
- TTS generation: <1 second
- **Total end-to-end: 2-5 seconds**

---

## Summary Checklist

### OpenAI Conversation Setup ✅
- [ ] Accessed Settings → Devices & Services
- [ ] Added "OpenAI Conversation" integration
- [ ] Configured "Athena Fast" with athena-fast model
- [ ] Configured "Athena Medium" with athena-medium model
- [ ] Verified both integrations show as "Configured"

### Assist Pipeline Setup ✅
- [ ] Accessed Settings → Voice Assistants
- [ ] Created "Athena Control" pipeline (faster-whisper + Athena Fast + piper)
- [ ] Created "Athena Knowledge" pipeline (faster-whisper + Athena Medium + piper)
- [ ] Set "Athena Control" as default pipeline
- [ ] Both pipelines appear in the list

### Testing ✅
- [ ] Tested Athena Fast with text input
- [ ] Tested Athena Medium with text input
- [ ] Tested voice input with microphone
- [ ] Verified response times under 5 seconds
- [ ] Tested device control commands
- [ ] Tested knowledge queries

---

## Next Steps After Setup

Once both integrations and pipelines are configured:

1. **Test thoroughly** with various commands
2. **Adjust models** if needed (faster vs. more capable)
3. **Configure automation** to use voice commands
4. **Set up voice satellites** (Wyoming devices) for multi-room (Phase 2)
5. **Monitor performance** via admin interface at https://athena-admin.xmojo.net

---

**Need Help?**

Check the logs:
```bash
# Home Assistant logs
ssh -i /tmp/ha_ssh_key2 -p 23 root@192.168.10.168
ha core logs

# Whisper logs
ha addons logs core_whisper

# Piper logs
ha addons logs core_piper

# Mac Studio orchestrator logs
ssh jstuart@192.168.10.167
docker logs orchestrator
```

**Created:** November 12, 2025
**Status:** Ready for implementation
**Estimated Time:** 15-20 minutes
