# Home Assistant LLM Integration Guide

**Date:** November 3, 2025
**Purpose:** Configure Home Assistant to route complex voice commands to Jetson LLM webhook service
**Status:** Manual configuration required

## Overview

This guide configures Home Assistant to automatically detect complex voice commands and route them to the Jetson LLM webhook service for intelligent processing, while keeping simple commands local for faster response.

## Integration Architecture

```
Voice Command → HA Voice Assistant → Command Analysis → Route Decision
                                                          ↓
    Simple Commands (lights, switches) ←─────────────────┴─────→ Complex Commands
           ↓                                                         ↓
    HA Native Processing                                    Jetson LLM Webhook
           ↓                                                         ↓
    Immediate Response                                      Enhanced AI Response
```

## Prerequisites

✅ **Jetson LLM Webhook Service Running:**
- Service: `http://192.168.10.62:5000`
- Status: Active and tested
- Endpoints: `/health`, `/process_command`, `/simple_command`

✅ **HA Voice Assistant Configured:**
- Location: Office
- Status: Working for basic commands

## Home Assistant Configuration

### Step 1: Add REST Command

Add this to your `configuration.yaml` file:

```yaml
rest_command:
  athena_llm_complex:
    url: "http://192.168.10.62:5000/process_command"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: >
      {
        "command": "{{ command }}",
        "source": "ha_voice_assistant",
        "timestamp": "{{ now().isoformat() }}"
      }
    timeout: 30

  athena_llm_simple:
    url: "http://192.168.10.62:5000/simple_command"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: >
      {
        "command": "{{ command }}",
        "source": "ha_voice_assistant",
        "timestamp": "{{ now().isoformat() }}"
      }
    timeout: 10
```

### Step 2: Create Input Text Helper

Add this to store the last voice command:

```yaml
input_text:
  last_voice_command:
    name: "Last Voice Command"
    max: 255
    initial: ""
```

### Step 3: Create Template Sensor for Command Classification

```yaml
template:
  - sensor:
      - name: "Voice Command Type"
        state: >
          {% set command = states('input_text.last_voice_command') | lower %}
          {% set complex_indicators = [
            'help', 'explain', 'how', 'what', 'why', 'when', 'where',
            'scene', 'mood', 'routine', 'schedule', 'please', 'can you',
            'turn off all', 'goodnight', 'good morning', 'movie', 'dinner',
            'set up', 'optimize', 'adjust', 'configure', 'create'
          ] %}
          {% if complex_indicators | select('in', command) | list | length > 0 %}
            complex
          {% else %}
            simple
          {% endif %}
        attributes:
          command: "{{ states('input_text.last_voice_command') }}"
          indicators_found: >
            {% set command = states('input_text.last_voice_command') | lower %}
            {% set complex_indicators = [
              'help', 'explain', 'how', 'what', 'why', 'when', 'where',
              'scene', 'mood', 'routine', 'schedule', 'please', 'can you',
              'turn off all', 'goodnight', 'good morning', 'movie', 'dinner',
              'set up', 'optimize', 'adjust', 'configure', 'create'
            ] %}
            {{ complex_indicators | select('in', command) | list }}
```

### Step 4: Create Automation for LLM Routing

Add this automation to `automations.yaml` or via the UI:

```yaml
- id: 'voice_command_llm_routing'
  alias: 'Route Voice Commands to Athena LLM'
  description: 'Automatically route complex voice commands to Jetson LLM service'
  trigger:
    - platform: state
      entity_id: input_text.last_voice_command
  condition:
    - condition: template
      value_template: "{{ trigger.to_state.state != '' and trigger.to_state.state != 'unknown' }}"
  action:
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ states('sensor.voice_command_type') == 'complex' }}"
          sequence:
            - service: rest_command.athena_llm_complex
              data:
                command: "{{ states('input_text.last_voice_command') }}"
            - service: notify.persistent_notification
              data:
                title: "Athena LLM Processing"
                message: "Complex command sent to Jetson LLM: {{ states('input_text.last_voice_command') }}"
        - conditions:
            - condition: template
              value_template: "{{ states('sensor.voice_command_type') == 'simple' }}"
          sequence:
            - service: rest_command.athena_llm_simple
              data:
                command: "{{ states('input_text.last_voice_command') }}"
      default:
        - service: notify.persistent_notification
          data:
            title: "Voice Command"
            message: "Unclassified command: {{ states('input_text.last_voice_command') }}"
  mode: single
```

### Step 5: Capture Voice Commands (Intent Script)

Create an intent script to capture voice commands. Add to `configuration.yaml`:

```yaml
intent_script:
  AthenaComplexCommand:
    speech:
      text: "Processing your request with Athena..."
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.last_voice_command
        data:
          value: "{{ slots.command }}"

  AthenaSimpleCommand:
    speech:
      text: "Executing command..."
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.last_voice_command
        data:
          value: "{{ slots.command }}"
```

### Step 6: Add Custom Sentences (Optional)

Create `custom_sentences/en/athena.yaml`:

```yaml
language: en
intents:
  AthenaComplexCommand:
    data:
      - sentences:
          - "help me {command}"
          - "can you {command}"
          - "please {command}"
          - "explain {command}"
          - "how do I {command}"
          - "set up {command}"
          - "optimize {command}"
  AthenaSimpleCommand:
    data:
      - sentences:
          - "turn on {command}"
          - "turn off {command}"
          - "set {command}"
          - "dim {command}"
```

## Manual Testing

### Test the REST Commands

1. **Go to Developer Tools → Services**
2. **Test Complex Command:**
   ```
   Service: rest_command.athena_llm_complex
   Service Data:
   command: "help me set up the office for a productive work session"
   ```

3. **Test Simple Command:**
   ```
   Service: rest_command.athena_llm_simple
   Service Data:
   command: "turn on office lights"
   ```

### Test Command Classification

1. **Set a test command:**
   ```
   Service: input_text.set_value
   Target: input_text.last_voice_command
   Service Data:
   value: "help me optimize the lighting"
   ```

2. **Check the classification:**
   - Go to Developer Tools → States
   - Find `sensor.voice_command_type`
   - Should show "complex" for the test command above

## Configuration Files to Modify

### Method 1: File System Access

**If you have SSH or file system access to the HA server:**

1. **Main configuration:** `/config/configuration.yaml`
2. **Automations:** `/config/automations.yaml`
3. **Custom sentences:** `/config/custom_sentences/en/athena.yaml`

### Method 2: Home Assistant UI

**If using the web interface:**

1. **Settings → Devices & Services → Helpers**
   - Add "Text" helper named "Last Voice Command"

2. **Settings → Automations & Scenes → Automations**
   - Create new automation using YAML mode
   - Paste the automation code above

3. **Configuration → YAML Configuration**
   - Edit `configuration.yaml` to add REST commands and template sensor

## Verification Steps

### 1. Service Health Check

```bash
# Test webhook service health
curl http://192.168.10.62:5000/health

# Expected response: {"status": "healthy", "service": "athena-llm-webhook"}
```

### 2. HA Configuration Check

```bash
# In HA, go to Developer Tools → Check Configuration
# Should show no errors after adding the YAML above
```

### 3. End-to-End Test

1. **Say to HA Voice Assistant:** "Help me set up the office for work"
2. **Expected flow:**
   - HA captures voice command
   - Command gets stored in `input_text.last_voice_command`
   - Automation detects it as "complex"
   - REST command sent to Jetson LLM
   - Jetson processes with AI and returns result

## Troubleshooting

### Common Issues

**1. REST Command Timeout:**
```yaml
# Increase timeout in configuration.yaml
rest_command:
  athena_llm_complex:
    timeout: 60  # Increase from 30 to 60 seconds
```

**2. Command Not Classified:**
- Check `sensor.voice_command_type` in Developer Tools → States
- Verify `input_text.last_voice_command` contains the expected text
- Add more complex indicators to the template if needed

**3. Webhook Service Not Responding:**
```bash
# Check if service is running on Jetson
ssh jstuart@192.168.10.62 "ps aux | grep llm_webhook"

# Restart if needed
ssh jstuart@192.168.10.62 "cd /mnt/nvme/athena-lite && python3 llm_webhook_service.py"
```

### Debug Commands

**Check HA logs:**
```bash
# In HA web interface: Settings → System → Logs
# Look for errors related to rest_command or automations
```

**Test direct webhook:**
```bash
curl -X POST http://192.168.10.62:5000/process_command \
  -H "Content-Type: application/json" \
  -d '{"command": "help me with the lights"}'
```

## Current Status

- ✅ **Jetson LLM Service:** Running and tested
- ✅ **HA Voice Assistant:** Working for basic commands
- ⏸️ **HA Configuration:** Requires manual setup (this guide)
- ⏸️ **End-to-End Testing:** Pending HA configuration

## Next Steps

1. **Apply HA Configuration:** Use this guide to modify HA configuration files
2. **Test Integration:** Verify voice commands route correctly to Jetson LLM
3. **Optimize Classification:** Fine-tune complex command detection as needed
4. **Monitor Performance:** Track response times and accuracy

---

**Integration Ready:** All Jetson components working
**Action Required:** Apply HA configuration using this guide
**Expected Result:** Full voice → LLM → HA pipeline operational