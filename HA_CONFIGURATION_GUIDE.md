# Home Assistant Configuration Guide - Project Athena

## Overview

This guide provides step-by-step instructions for configuring Home Assistant to work with Project Athena. These steps must be completed via the Home Assistant UI and cannot be automated via the API.

**Prerequisites:**
- Phase 1 services running on Mac Studio (192.168.10.167)
- Home Assistant accessible at https://ha.xmojo.net
- Admin access to Home Assistant

**What you'll configure:**
1. Wyoming Protocol add-ons (STT + TTS)
2. OpenAI Conversation integration (pointing to Mac Studio)
3. Two Assist Pipelines (Control + Knowledge)
4. HA Voice preview devices (when hardware available)

---

## Step 1: Install Wyoming Protocol Add-ons

Wyoming is Home Assistant's protocol for voice assistant services. We'll install two add-ons: Faster-Whisper (speech-to-text) and Piper (text-to-speech).

### Install Faster-Whisper (Speech-to-Text)

1. **Navigate to Settings**
   - Open Home Assistant: https://ha.xmojo.net
   - Click **Settings** in the sidebar
   - Click **Add-ons**

2. **Add Wyoming Faster-Whisper**
   - Click **Add-on Store** (bottom right)
   - Search for "Wyoming Faster-Whisper"
   - Click on **Whisper** add-on
   - Click **Install**

3. **Configure Faster-Whisper**
   - After installation, click the **Configuration** tab
   - Set these options:
     ```yaml
     language: en
     model: tiny-int8
     ```
   - Click **Save**

4. **Start the Add-on**
   - Go to the **Info** tab
   - Enable **Start on boot**
   - Enable **Watchdog**
   - Click **Start**
   - Wait for it to show "Running" status

5. **Verify**
   - Check the **Log** tab for any errors
   - Should see: "Faster-Whisper server started"

### Install Piper (Text-to-Speech)

1. **Add Piper TTS**
   - Still in **Add-on Store**
   - Search for "Wyoming Piper"
   - Click on **Piper** add-on
   - Click **Install**

2. **Configure Piper**
   - After installation, click the **Configuration** tab
   - Set these options:
     ```yaml
     voice: en_US-lessac-medium
     ```
   - Click **Save**

3. **Start the Add-on**
   - Go to the **Info** tab
   - Enable **Start on boot**
   - Enable **Watchdog**
   - Click **Start**
   - Wait for it to show "Running" status

4. **Verify**
   - Check the **Log** tab for any errors
   - Should see: "Piper server started"

**Checkpoint:** You should now have two running add-ons visible in Settings > Add-ons

---

## Step 2: Configure OpenAI Conversation Integration

This integration connects Home Assistant to your Athena orchestrator running on Mac Studio.

### Add OpenAI Conversation Integration

1. **Navigate to Integrations**
   - Click **Settings** in the sidebar
   - Click **Devices & Services**
   - Click **Integrations** tab

2. **Add Integration**
   - Click **+ Add Integration** (bottom right)
   - Search for "OpenAI Conversation"
   - Click on **OpenAI Conversation**

3. **Configure the Integration**
   - **API Key**: Enter any text (e.g., "not-used")
     - Note: Your Mac Studio orchestrator doesn't require auth
   - **Base URL**: `http://192.168.10.167:8001/v1`
     - This points to your orchestrator service
   - **Model**: `athena-small`
     - This uses the phi3:mini model via LiteLLM
   - Click **Submit**

4. **Verify Configuration**
   - You should see "OpenAI Conversation" in your integrations list
   - Click on it to see configuration details

### Test the Integration (Optional)

1. **Use Developer Tools**
   - Click **Developer Tools** in the sidebar
   - Click the **Services** tab

2. **Test Conversation**
   - Service: `conversation.process`
   - Service Data:
     ```yaml
     text: "what is 2+2?"
     ```
   - Click **Call Service**

3. **Check Response**
   - Should return a response with "4" in the text
   - If you get an error, check:
     - Mac Studio services are running
     - Network connectivity to 192.168.10.167
     - Orchestrator logs: `docker compose logs -f orchestrator`

**Checkpoint:** OpenAI Conversation integration working and tested

---

## Step 3: Create Assist Pipelines

You'll create two pipelines:
1. **Control Pipeline**: Quick commands using phi3:mini (fast)
2. **Knowledge Pipeline**: Complex queries using llama3.1:8b (detailed)

### Create Control Pipeline (Fast Commands)

1. **Navigate to Voice Assistants**
   - Click **Settings** in the sidebar
   - Click **Voice assistants**

2. **Add a New Pipeline**
   - Click **+ Add Pipeline** (bottom right)
   - Name: `Athena Control`

3. **Configure Control Pipeline**
   - **Speech-to-text**: Select `faster-whisper`
   - **Conversation agent**: Select `OpenAI Conversation`
   - **Text-to-speech**: Select `piper`
   - Click **Create**

4. **Edit OpenAI Settings** (Important!)
   - Click on the newly created "Athena Control" pipeline
   - Click the **gear icon** next to "OpenAI Conversation"
   - **Model**: `athena-small`
   - **Prompt Template**: Use this:
     ```
     You are Athena, a helpful voice assistant. Answer concisely and naturally.

     Current devices and states:
     {{ states | map(attribute='entity_id') | join(', ') }}

     User question: {{ text }}

     Provide a brief, natural response suitable for voice output.
     ```
   - **Max Tokens**: `150`
   - **Temperature**: `0.7`
   - Click **Save**

### Create Knowledge Pipeline (Complex Queries)

1. **Add Another Pipeline**
   - Still in **Voice assistants**
   - Click **+ Add Pipeline** again
   - Name: `Athena Knowledge`

2. **Configure Knowledge Pipeline**
   - **Speech-to-text**: Select `faster-whisper`
   - **Conversation agent**: Select `OpenAI Conversation`
   - **Text-to-speech**: Select `piper`
   - Click **Create**

3. **Edit OpenAI Settings**
   - Click on the "Athena Knowledge" pipeline
   - Click the **gear icon** next to "OpenAI Conversation"
   - **Model**: `athena-medium`
     - This uses llama3.1:8b for more detailed reasoning
   - **Prompt Template**: Use this:
     ```
     You are Athena, an intelligent voice assistant with access to real-time information.

     You can answer questions about:
     - Weather and climate
     - Flights and airports
     - Movies and entertainment
     - Sports scores and schedules
     - Stock prices
     - News and current events
     - Wikipedia information
     - And more

     Current smart home devices:
     {{ states | map(attribute='entity_id') | join(', ') }}

     User question: {{ text }}

     Provide a detailed, informative response. Include relevant data when available.
     Use your RAG capabilities to fetch real-time information when needed.
     ```
   - **Max Tokens**: `500`
   - **Temperature**: `0.7`
   - Click **Save**

**Checkpoint:** You should now see two pipelines:
- Athena Control (for quick commands)
- Athena Knowledge (for detailed queries)

---

## Step 4: Set Default Pipeline

1. **Choose Your Default**
   - In **Settings > Voice assistants**
   - Find "Athena Control" or "Athena Knowledge"
   - Click the **star icon** to set as default
   - Recommended: Set "Athena Control" as default for faster responses

2. **Verify**
   - The default pipeline should show a yellow star
   - This pipeline will be used when you say "Hey Jarvis" or "Hey Athena"

---

## Step 5: Test the Pipelines

### Test via Home Assistant UI

1. **Open Assist**
   - Look for the **microphone icon** in the top-right of HA
   - Click it to open the Assist interface

2. **Test a Simple Command**
   - Click the microphone and say:
     - "What is 2 plus 2?"
   - You should hear Piper TTS respond: "4"

3. **Test a Complex Query**
   - Switch to "Athena Knowledge" pipeline in the Assist dropdown
   - Ask: "What is the weather in Baltimore?"
   - Should get a detailed response with current weather

4. **Test Home Control**
   - Switch back to "Athena Control"
   - Say: "Turn on the kitchen lights"
   - Should control your HA devices

### Troubleshooting Pipeline Issues

**If you get errors:**

1. **Check Wyoming add-ons are running**
   - Settings > Add-ons
   - Both Faster-Whisper and Piper should show "Running"

2. **Check OpenAI integration**
   - Settings > Devices & Services > Integrations
   - OpenAI Conversation should be active
   - Check base URL: `http://192.168.10.167:8001/v1`

3. **Check Mac Studio services**
   ```bash
   ssh jstuart@192.168.10.167
   cd ~/dev/project-athena
   docker compose ps
   ```
   - All services should show "Up"

4. **Check orchestrator logs**
   ```bash
   docker compose logs -f orchestrator
   ```
   - Look for incoming requests when you test

5. **Test orchestrator directly**
   ```bash
   curl http://192.168.10.167:8001/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "test"}]}'
   ```
   - Should return a response

---

## Step 6: Configure HA Voice Preview Devices

**Note:** This step requires HA Voice preview hardware, which may not be available yet.

### When you have HA Voice devices:

1. **Power on the Device**
   - Connect HA Voice preview device to power
   - Wait for it to show "Ready to pair" status
   - Usually indicated by a pulsing light

2. **Put Device in Pairing Mode**
   - Press and hold the pairing button
   - Hold until you hear "Ready to pair" announcement

3. **Add to Home Assistant**
   - In HA, go to **Settings > Devices & Services**
   - Click **+ Add Integration**
   - Search for "ESPHome" or "Wyoming"
   - Device should appear automatically
   - Click on it and follow pairing instructions

4. **Configure the Device**
   - **Name**: Give it a zone name (e.g., "Office Voice")
   - **Pipeline**: Select "Athena Control" or "Athena Knowledge"
   - **Wake Word**: Choose from available options
   - Click **Submit**

5. **Test Voice Device**
   - Say the wake word: "Hey Jarvis" or "Hey Athena"
   - Device should chime and light up
   - Ask a question: "What time is it?"
   - Should respond via TTS

### Repeat for All Zones

**Planned 10 zones:**
1. Office
2. Kitchen
3. Living Room
4. Master Bedroom
5. Master Bath
6. Main Bath
7. Alpha (Guest Bedroom 1)
8. Beta (Guest Bedroom 2)
9. Basement Bathroom
10. Dining Room

For each device:
- Assign a descriptive name
- Choose appropriate pipeline (Control for most, Knowledge for office/living room)
- Set wake word preference

---

## Step 7: Advanced Configuration (Optional)

### Create Dual Wake Word Routing

If you want different behavior for "Jarvis" vs "Athena":

1. **Create Automation**
   - Settings > Automations & Scenes
   - Click **+ Create Automation**

2. **Trigger: Wake Word Detected**
   ```yaml
   trigger:
     - platform: event
       event_type: wyoming_wake_word_detected
   ```

3. **Condition: Check Wake Word**
   ```yaml
   condition:
     - condition: template
       value_template: "{{ trigger.event.data.wake_word == 'jarvis' }}"
   ```

4. **Action: Switch Pipeline**
   ```yaml
   action:
     - service: assist_pipeline.run
       data:
         pipeline_id: athena_control  # Fast pipeline
   ```

5. **Create Second Automation for "Athena" wake word**
   - Same structure but use "athena_knowledge" pipeline

### Configure Response Validation

Add validation step to pipelines:

1. **Edit Pipeline**
   - Settings > Voice assistants
   - Click on a pipeline
   - Click **gear icon**

2. **Add Post-Processing** (if available in future HA versions)
   ```yaml
   post_process:
     - service: rest_command.validate_response
       url: http://192.168.10.167:8030/validate
       method: POST
   ```

### Add Context to Queries

Enhance prompts with more context:

1. **Edit Pipeline Prompt**
   - Include recent conversation history
   - Add user preferences
   - Add location/time context

Example enhanced prompt:
```
You are Athena, an intelligent voice assistant.

Current time: {{ now().strftime('%I:%M %p') }}
Current date: {{ now().strftime('%A, %B %d, %Y') }}
Location: {{ state_attr('zone.home', 'friendly_name') }}

Recent device changes:
{{ states | selectattr('last_changed') | map(attribute='entity_id') | list }}

User question: {{ text }}

Provide a natural, conversational response.
```

---

## Step 8: Testing and Validation

### End-to-End Voice Test Checklist

Once everything is configured:

- [ ] Wake word detection works
- [ ] Speech-to-text accurately transcribes commands
- [ ] Simple queries route to Control pipeline
- [ ] Complex queries route to Knowledge pipeline
- [ ] Responses are accurate and natural
- [ ] Text-to-speech sounds clear
- [ ] Device controls work (lights, switches, etc.)
- [ ] Response time is acceptable (<5 seconds)
- [ ] Multiple zones work independently
- [ ] No cross-talk between zones

### Performance Testing

**Test response times:**
1. Simple query ("what time is it?"): Target <2s
2. Weather query: Target <3s
3. Complex query: Target <5s
4. Device control: Target <2s

**If responses are slow:**
- Check network latency to Mac Studio
- Check Mac Studio CPU usage (`top`)
- Review orchestrator logs for bottlenecks
- Consider switching Knowledge pipeline to phi3:mini

### Quality Testing

**Test accuracy:**
- Weather queries return current data
- Device states are correct
- Calculations are accurate
- General knowledge is correct

**If responses are inaccurate:**
- Check RAG service health
- Verify API keys are valid
- Review validator logs
- Check prompt templates

---

## Configuration Summary

After completing all steps, you should have:

**Wyoming Add-ons:**
- ✅ Faster-Whisper (STT) running
- ✅ Piper (TTS) running

**Integrations:**
- ✅ OpenAI Conversation connected to Mac Studio

**Pipelines:**
- ✅ Athena Control (fast commands, phi3:mini)
- ✅ Athena Knowledge (complex queries, llama3.1:8b)

**Devices:**
- ✅ Voice devices paired and configured (when hardware available)

**Testing:**
- ✅ End-to-end voice pipeline working
- ✅ Response times meet targets
- ✅ Accuracy validated

---

## Troubleshooting Common Issues

### Issue: "Could not connect to OpenAI"

**Check:**
1. Mac Studio services running: `ssh jstuart@192.168.10.167 "docker compose ps"`
2. Orchestrator accessible: `curl http://192.168.10.167:8001/health`
3. Base URL correct in integration: `http://192.168.10.167:8001/v1`
4. Network connectivity: `ping 192.168.10.167`

**Fix:**
```bash
# Restart Mac Studio services
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
docker compose restart orchestrator gateway
```

### Issue: "Wake word not detected"

**Check:**
1. HA Voice device paired
2. Microphone working
3. Wake word service enabled
4. Volume levels appropriate

**Fix:**
- Re-pair device
- Check device logs in ESPHome
- Test microphone with manual recording

### Issue: "Speech-to-text not working"

**Check:**
1. Faster-Whisper add-on running
2. Logs show no errors
3. Model downloaded successfully

**Fix:**
```
Settings > Add-ons > Faster-Whisper
- Click "Restart"
- Check logs for errors
- Reinstall if needed
```

### Issue: "Text-to-speech silent"

**Check:**
1. Piper add-on running
2. Voice model downloaded
3. Audio output device selected

**Fix:**
```
Settings > Add-ons > Piper
- Click "Restart"
- Check configuration
- Test with HA developer tools
```

### Issue: "Responses are slow"

**Check:**
1. Mac Studio CPU usage
2. Network latency
3. Model selection (llama3.1:8b is slower than phi3:mini)

**Fix:**
- Use "athena-small" model for both pipelines
- Check network performance
- Review orchestrator logs for bottlenecks

### Issue: "Responses are inaccurate"

**Check:**
1. RAG service health
2. API keys valid
3. Prompt templates appropriate

**Fix:**
- Run integration tests: `python3 tests/integration/test_full_system.py`
- Check specific RAG service logs
- Update prompt templates for clarity

---

## Next Steps After Configuration

Once HA is fully configured:

1. **Fine-tune prompts** based on actual usage patterns
2. **Add custom intents** for frequently used commands
3. **Create automations** triggered by voice commands
4. **Monitor performance** and adjust model selection
5. **Expand to all 10 zones** as hardware becomes available

---

## Reference

### Key URLs
- **Home Assistant**: https://ha.xmojo.net
- **Mac Studio Orchestrator**: http://192.168.10.167:8001
- **Ollama**: http://192.168.10.167:11434

### Key Files
- **DEPLOYMENT.md**: Service management
- **TROUBLESHOOTING.md**: Problem resolution
- **PHASE1_COMPLETE.md**: System overview
- **admin/k8s/README.md**: Admin interface

### API Endpoints
- **Health Check**: `http://192.168.10.167:8001/health`
- **Chat**: `http://192.168.10.167:8001/v1/chat/completions`
- **Metrics**: `http://192.168.10.167:8001/metrics`

---

**Last Updated:** November 11, 2025
**Prerequisites:** Phase 1 services running on Mac Studio
**Required Access:** Home Assistant admin UI
**Estimated Time:** 30-45 minutes
