# Research: HA LLM Integration Facade Feature Set

**Date**: 2025-11-06T14:51:08+0000
**Researcher**: Claude Code
**Repository**: project-athena
**Topic**: Home Assistant LLM Integration Facade - Feature Set Documentation

## Research Question

Document the "facade" feature set in Project Athena, specifically focusing on the Home Assistant LLM integration system and the features that were recently added.

## Summary

The "facade" refers to the **Home Assistant LLM Integration system** - a command routing and classification layer that sits between Home Assistant voice input and backend processing services (Jetson LLM or direct HA commands). This system was configured on November 3, 2025, and consists of four main components that work together to provide intelligent voice command routing.

The facade acts as an abstraction layer that:
1. Captures voice commands from Home Assistant
2. Classifies commands as "complex" or "simple"
3. Routes commands to the appropriate processing backend
4. Returns responses back to Home Assistant for execution

## Detailed Findings

### The Facade: HA LLM Integration System

**What it is**: A multi-component system that provides intelligent routing of voice commands between Home Assistant and the Jetson LLM service.

**Location**: Configured in Home Assistant server at 192.168.10.168
**Configuration Files**:
- `/config/configuration.yaml` (on HA server)
- `/config/automations.yaml` (on HA server)

**Documentation**:
- [docs/HA_LLM_INTEGRATION_GUIDE.md](docs/HA_LLM_INTEGRATION_GUIDE.md:1) - Complete integration guide
- [docs/CONFIG_UPDATE_SUCCESS.md](docs/CONFIG_UPDATE_SUCCESS.md:1) - Configuration completion status

### Feature 1: REST Command Endpoints

**Purpose**: Provide HTTP endpoints to communicate with the Jetson LLM webhook service

**Implementation** (in `/config/configuration.yaml`):
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

**Features**:
- Two distinct endpoints for different command types
- Configurable timeout (30s for complex, 10s for simple)
- Structured JSON payload with command, source, and timestamp
- Template support for dynamic command injection

**Backend Service**: Jetson webhook service at `http://192.168.10.62:5000`
- `/process_command` - Processes complex commands with LLM (DialoGPT-small)
- `/simple_command` - Routes simple commands directly to HA API
- `/health` - Service health check endpoint

### Feature 2: Input Text Helper

**Purpose**: Capture and store the last voice command for processing

**Implementation** (in `/config/configuration.yaml`):
```yaml
input_text:
  last_voice_command:
    name: "Last Voice Command"
    max: 255
    initial: ""
```

**Features**:
- Entity ID: `input_text.last_voice_command`
- Maximum length: 255 characters
- Stores user's voice command text
- Acts as trigger for automation
- Provides visibility into what command was captured

**Usage Pattern**:
Voice Assistant → intent_script → `input_text.last_voice_command` → Automation

### Feature 3: Template Sensor for Command Classification

**Purpose**: Automatically classify voice commands as "complex" or "simple" based on keyword detection

**Implementation** (in `/config/configuration.yaml`):
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

**Features**:
- Entity ID: `sensor.voice_command_type`
- State values: "complex" or "simple"
- 15+ complex indicator keywords
- Real-time classification (<100ms response time)
- Debug attribute showing which indicators were found
- Stores original command in attributes

**Complex Indicators**:
- Question words: help, explain, how, what, why, when, where
- Context words: scene, mood, routine, schedule
- Polite phrases: please, can you
- Multi-action: turn off all
- Routine triggers: goodnight, good morning, movie, dinner
- Configuration: set up, optimize, adjust, configure, create

### Feature 4: Routing Automation

**Purpose**: Automatically route commands to the appropriate backend based on classification

**Implementation** (in `/config/automations.yaml`):
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

**Features**:
- Automation ID: `voice_command_llm_routing`
- Trigger: State change of `input_text.last_voice_command`
- Validation: Non-empty, non-unknown commands only
- Choose block with two paths:
  - Complex path: Calls `rest_command.athena_llm_complex` + notification
  - Simple path: Calls `rest_command.athena_llm_simple`
  - Default path: Notification for unclassified commands
- Mode: Single (prevents overlapping executions)
- Notifications: Optional persistent notifications for debugging

### Complete Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                         User Voice Input                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Home Assistant Voice Assistant                 │
│                  (Office - HA Blue Device)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Feature 2: Input Text Helper                   │
│           input_text.last_voice_command                     │
│              (Captures: "help me with lights")              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Feature 3: Template Sensor Classification           │
│              sensor.voice_command_type                      │
│         (Analyzes: Finds "help" → Returns: "complex")       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           Feature 4: Routing Automation                     │
│         automation.voice_command_llm_routing                │
│     (Triggers on input change, checks classification)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ├─ If "complex" ─────────────────────┐
                       │                                     │
                       ▼                                     ▼
┌───────────────────────────────────────┐   ┌──────────────────────────────┐
│  Feature 1: REST Command Complex      │   │  Feature 1: REST Command     │
│  rest_command.athena_llm_complex      │   │  rest_command.athena_llm...  │
│  POST /process_command (30s timeout)  │   │  POST /simple_command (10s)  │
└──────────────────┬────────────────────┘   └─────────────┬────────────────┘
                   │                                       │
                   ▼                                       ▼
┌───────────────────────────────────────┐   ┌──────────────────────────────┐
│      Jetson LLM Webhook Service       │   │  Jetson Webhook (Direct HA)  │
│    192.168.10.62:5000/process_cmd     │   │  192.168.10.62:5000/simple   │
│    - DialoGPT-small LLM Processing    │   │  - Direct HA API Call        │
│    - Enhanced AI Response             │   │  - Fast Device Control       │
└──────────────────┬────────────────────┘   └─────────────┬────────────────┘
                   │                                       │
                   └────────────────┬──────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────────────┐
                    │       Home Assistant API              │
                    │      Device Control & Response        │
                    └───────────────────────────────────────┘
```

### Backend: Jetson LLM Webhook Service

**Location**: `/mnt/nvme/athena-lite/llm_webhook_service.py` on jetson-01 (192.168.10.62)

**Features**:
- Flask-based HTTP server on port 5000
- DialoGPT-small model loaded for complex command processing
- Three endpoints:
  - `GET /health` - Service health check
  - `POST /process_command` - Complex command with LLM processing
  - `POST /simple_command` - Simple command direct to HA API

**Performance** (from [docs/CONFIG_UPDATE_SUCCESS.md](docs/CONFIG_UPDATE_SUCCESS.md:111)):
- Average response time: 1.56 seconds
- Classification accuracy: 100% in testing
- Template sensor latency: <100ms
- Webhook routing overhead: <200ms
- Total facade overhead: <300ms

### Configuration Status

**Configuration Date**: November 3, 2025
**Configuration Files Modified**: 2
- `/config/configuration.yaml` (backed up as configuration.yaml.backup-20251103-115523)
- `/config/automations.yaml` (backed up as automations.yaml.backup-20251103-115523)

**Components Added**: 4
1. REST commands (athena_llm_complex, athena_llm_simple)
2. Input text helper (input_text.last_voice_command)
3. Template sensor (sensor.voice_command_type)
4. Routing automation (automation.voice_command_llm_routing)

**Testing Status** (from [docs/CONFIG_UPDATE_SUCCESS.md](docs/CONFIG_UPDATE_SUCCESS.md:27)):
- ✅ Complex command test: "help me optimize the office lighting" → classified as "complex"
- ✅ Simple command test: "turn on office lights" → classified as "simple"
- ✅ Template sensor: Real-time updates working
- ✅ Syntax validation: All YAML passed checks
- ✅ Home Assistant restart: Successful

## Feature Dependencies

### Internal Dependencies
1. **Input Text Helper** → **Template Sensor** (sensor reads input value)
2. **Template Sensor** → **Automation** (automation checks sensor state)
3. **Automation** → **REST Commands** (automation calls REST services)
4. **REST Commands** → **Jetson Webhook** (REST commands invoke external service)

### External Dependencies
1. **Jetson LLM Webhook Service** must be running on 192.168.10.62:5000
2. **Home Assistant API** must be accessible for device control
3. **Network connectivity** between HA server and Jetson required
4. **Voice Assistant** must populate input_text.last_voice_command

## Configuration File Locations

**Home Assistant Configuration** (192.168.10.168):
- `/config/configuration.yaml` - REST commands, input helper, template sensor
- `/config/automations.yaml` - Routing automation
- Backups: `*.backup-20251103-115523`

**Jetson Implementation** (192.168.10.62):
- `/mnt/nvme/athena-lite/llm_webhook_service.py` - Webhook service
- `/mnt/nvme/athena-lite/athena_lite_llm.py` - Enhanced Athena Lite with LLM
- `/mnt/nvme/athena-lite/config/ha_config.py` - HA configuration

**Project Documentation** (/Users/jaystuart/dev/project-athena):
- [docs/HA_LLM_INTEGRATION_GUIDE.md](docs/HA_LLM_INTEGRATION_GUIDE.md:1) - Complete setup guide
- [docs/CONFIG_UPDATE_SUCCESS.md](docs/CONFIG_UPDATE_SUCCESS.md:1) - Configuration completion
- [docs/INTEGRATION_SETUP.md](docs/INTEGRATION_SETUP.md:1) - Initial setup procedures
- [docs/INTEGRATION_SUCCESS.md](docs/INTEGRATION_SUCCESS.md:1) - Integration validation
- [docs/CURRENT_FINDINGS.md](docs/CURRENT_FINDINGS.md:1) - Technical analysis

## Potential Reliability Issues

Based on the architecture and implementation, several areas could cause reliability issues:

### 1. State Synchronization
- **Issue**: Multiple components depend on state changes propagating correctly
- **Risk**: If template sensor doesn't update before automation triggers, wrong routing
- **Impact**: Commands might route to wrong endpoint or fail to route

### 2. Timing Dependencies
- **Issue**: Automation triggers on `input_text.last_voice_command` state change
- **Risk**: Race condition between input update and sensor classification
- **Impact**: Automation might read stale sensor value

### 3. Network Dependencies
- **Issue**: REST commands require stable connection to Jetson (192.168.10.62:5000)
- **Risk**: Network issues, Jetson service down, or timeout
- **Impact**: Commands fail silently or timeout

### 4. Classification Edge Cases
- **Issue**: Template sensor uses simple keyword matching
- **Risk**: False positives/negatives in classification
- **Examples**:
  - "turn off all lights" contains "turn off" (simple) but also "all" (might be complex)
  - "help turn on lights" contains both "help" (complex) and "turn on" (simple)
- **Impact**: Commands route to wrong backend

### 5. Timeout Mismatches
- **Issue**: Different timeout values (30s complex, 10s simple)
- **Risk**: Long-running LLM processing might exceed timeout
- **Impact**: User gets no response even if processing completes

### 6. Error Handling Gaps
- **Issue**: Automation has no error handling for REST command failures
- **Risk**: If webhook returns error or times out, no fallback
- **Impact**: User gets no feedback, command appears to fail silently

### 7. Missing Voice Integration
- **Issue**: Voice assistant not yet configured to populate `input_text.last_voice_command`
- **Status**: Per [docs/CONFIG_UPDATE_SUCCESS.md](docs/CONFIG_UPDATE_SUCCESS.md:132), voice integration is "ready" but not implemented
- **Impact**: Entire system may not activate from voice input

### 8. Single Mode Limitation
- **Issue**: Automation runs in "single" mode
- **Risk**: If command is still processing, new commands are ignored
- **Impact**: Users must wait for previous command to complete

## Related Components

### Athena Lite Voice Assistant
- **Location**: `/mnt/nvme/athena-lite/` on jetson-01
- **Status**: 90% complete, ready for testing
- **Components**: Wake word detection (Jarvis + Athena), STT (Whisper), TTS (Piper)
- **Integration**: Separate from HA LLM facade, complementary system

### Brightness Formula System
- **Location**: [brightness-formulas-code.js](brightness-formulas-code.js:1)
- **Purpose**: Automated light brightness based on lux sensors
- **Status**: Analysis complete, implementation pending
- **Relation**: Separate feature, not part of HA LLM facade

## Next Steps for Investigation

To diagnose reliability issues with the facade:

1. **Check HA Logs**:
   ```bash
   ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168
   tail -f /config/home-assistant.log
   ```

2. **Monitor Jetson Webhook Service**:
   ```bash
   ssh jstuart@192.168.10.62
   # Check if service is running
   ps aux | grep llm_webhook
   # Check logs if service has logging
   ```

3. **Test Individual Components**:
   ```bash
   # Test REST command directly
   # (from within HA Developer Tools → Services)
   service: rest_command.athena_llm_complex
   data:
     command: "test command"

   # Check sensor state
   # (from Developer Tools → States)
   # Look for: sensor.voice_command_type
   ```

4. **Verify State Propagation**:
   - Set `input_text.last_voice_command` manually
   - Immediately check `sensor.voice_command_type` state
   - Verify automation triggered
   - Check if REST command was called

5. **Test Classification**:
   - Try edge cases: "help turn on lights", "turn off all lights"
   - Verify which indicators are detected
   - Confirm routing decision is correct

6. **Check Network Connectivity**:
   ```bash
   # From HA server
   curl http://192.168.10.62:5000/health

   # Test endpoints
   curl -X POST http://192.168.10.62:5000/process_command \
     -H "Content-Type: application/json" \
     -d '{"command": "test"}'
   ```

## Conclusion

The "facade" is the **HA LLM Integration system** consisting of four interconnected features:
1. REST command endpoints (athena_llm_complex, athena_llm_simple)
2. Input text helper (last_voice_command)
3. Template sensor for classification (voice_command_type)
4. Routing automation (voice_command_llm_routing)

All features were configured on November 3, 2025, and passed initial testing. However, the system has multiple potential failure points including state synchronization, timing dependencies, network issues, classification edge cases, and missing error handling. The voice integration component may also not be fully connected, which could prevent the entire system from activating properly.

---

**Research Status**: Complete
**Next Action**: Diagnose specific reliability issues by testing components individually
**Key Files**: [docs/CONFIG_UPDATE_SUCCESS.md](docs/CONFIG_UPDATE_SUCCESS.md:1), [docs/HA_LLM_INTEGRATION_GUIDE.md](docs/HA_LLM_INTEGRATION_GUIDE.md:1)
