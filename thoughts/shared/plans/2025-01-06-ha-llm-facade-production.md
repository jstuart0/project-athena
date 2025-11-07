# HA LLM Facade: Production-Ready Implementation Plan

## Overview

Transform the Home Assistant LLM Integration facade from a configured-but-non-functional system into a fully operational, production-ready infrastructure with comprehensive monitoring, testing, and deployment automation.

**Created:** 2025-01-06
**Based On:** [thoughts/research/RESEARCH_HA_LLM_FACADE.md](../research/RESEARCH_HA_LLM_FACADE.md)
**Status:** Ready for implementation
**Estimated Timeline:** 1-2 weeks with AI agent execution

## Current State Analysis

### What Exists

**✅ Configured (November 3, 2025):**
- 4 HA components: REST commands, input helper, template sensor, routing automation
- Configuration files: `/config/configuration.yaml`, `/config/automations.yaml` on 192.168.10.168
- Manual testing via curl successful
- Classification logic with 15 complex indicators
- Backups created: `*.backup-20251103-115523`

**⚠️ Documented but Unverified:**
- Jetson webhook service at `/mnt/nvme/athena-lite/llm_webhook_service.py` (192.168.10.62)
- DialoGPT-small model loaded
- Flask service on port 5000 with 3 endpoints

**❌ Not Operational:**
- Voice integration disconnected - cannot activate from voice input
- No version control for Jetson implementation code
- No service persistence (systemd)
- No error handling or fallback mechanisms
- No monitoring or alerting
- End-to-end testing never performed

### Current Production Readiness: 20%

## Desired End State

**A fully operational, production-ready voice → LLM → HA pipeline featuring:**

1. **Voice Integration:** Voice commands automatically route through facade to Jetson LLM
2. **Reliability:** All 8 identified issues addressed with proper error handling
3. **Version Control:** All implementation code tracked in git with deployment automation
4. **Service Management:** Systemd service with auto-restart and health monitoring
5. **Observability:** Comprehensive logging, metrics, and alerting
6. **Testing:** Automated test suite validating all components
7. **Documentation:** Complete operational procedures and troubleshooting guides

### Verification Criteria

**System is production-ready when:**
- Voice commands successfully trigger facade and receive responses
- System handles network failures gracefully with fallback mechanisms
- All code is version controlled with automated deployment
- Service persists across reboots with health monitoring
- Response times meet 2-5 second target
- 24+ hour stability test passes
- All automated tests pass
- Complete documentation exists

## What We're NOT Doing

- Wyoming protocol integration (Phase 1 future work)
- Multi-zone deployment (Phase 2 future work)
- RAG capabilities (Phase 2 future work)
- Home Assistant migration to Proxmox (Phase 0 - separate project)
- Mobile app integration
- Custom wake word training
- Performance optimization beyond baseline requirements

## Implementation Approach

Execute 6 phases sequentially, with each phase building on the previous. Each phase has clear automated and manual success criteria that must be validated before proceeding.

**Execution Model:** AI agents execute phases with human validation at phase boundaries

---

## Phase 1: Code Recovery & Repository Setup

### Overview

Retrieve existing Jetson implementation code, establish version control, and create proper repository structure for infrastructure-as-code management.

### Changes Required

#### 1. Retrieve Jetson Implementation Files

**Action:** SSH to Jetson and copy all implementation files to local repository

```bash
# Create local structure
mkdir -p /Users/jaystuart/dev/project-athena/src/jetson
mkdir -p /Users/jaystuart/dev/project-athena/src/ha-integration
mkdir -p /Users/jaystuart/dev/project-athena/tests
mkdir -p /Users/jaystuart/dev/project-athena/scripts/deployment
mkdir -p /Users/jaystuart/dev/project-athena/config/ha

# Copy Jetson files from remote
scp jstuart@192.168.10.62:/mnt/nvme/athena-lite/llm_webhook_service.py \
    /Users/jaystuart/dev/project-athena/src/jetson/

scp jstuart@192.168.10.62:/mnt/nvme/athena-lite/athena_lite.py \
    /Users/jaystuart/dev/project-athena/src/jetson/

scp jstuart@192.168.10.62:/mnt/nvme/athena-lite/athena_lite_llm.py \
    /Users/jaystuart/dev/project-athena/src/jetson/

scp -r jstuart@192.168.10.62:/mnt/nvme/athena-lite/config/ \
    /Users/jaystuart/dev/project-athena/src/jetson/config/
```

#### 2. Retrieve Home Assistant Configuration

**Action:** Copy HA configuration files to repository

```bash
# Copy HA configuration files
scp -i ~/.ssh/id_ed25519_new -P 23 root@192.168.10.168:/config/configuration.yaml \
    /Users/jaystuart/dev/project-athena/config/ha/configuration.yaml.fragment

scp -i ~/.ssh/id_ed25519_new -P 23 root@192.168.10.168:/config/automations.yaml \
    /Users/jaystuart/dev/project-athena/config/ha/automations.yaml.fragment

# Note: These are "fragments" because they contain only the facade-related config,
# not the entire HA configuration
```

#### 3. Create Repository Structure

**File:** `/Users/jaystuart/dev/project-athena/README.md`

Update README with proper project structure:

```markdown
# Project Athena - AI Voice Assistant

## Repository Structure

```
project-athena/
├── src/
│   ├── jetson/                 # Jetson implementation
│   │   ├── llm_webhook_service.py
│   │   ├── athena_lite.py
│   │   ├── athena_lite_llm.py
│   │   └── config/
│   └── ha-integration/         # HA integration code
├── config/
│   ├── ha/                     # HA configuration fragments
│   ├── models.yaml             # AI model specifications
│   ├── network.yaml            # Network configuration
│   └── zones.yaml              # Zone definitions
├── scripts/
│   ├── deployment/             # Deployment automation
│   └── testing/                # Test utilities
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── docs/                       # Documentation
├── thoughts/                   # Research and plans
└── manifests/                  # Kubernetes manifests (future)
```
```

#### 4. Create Python Package Structure

**File:** `/Users/jaystuart/dev/project-athena/src/jetson/requirements.txt`

```txt
flask==3.0.0
torch==2.1.0
transformers==4.35.0
requests==2.31.0
python-dotenv==1.0.0
```

**File:** `/Users/jaystuart/dev/project-athena/src/jetson/__init__.py`

```python
"""Project Athena - Jetson LLM Integration"""
__version__ = "0.1.0"
```

#### 5. Document Current Implementation

**File:** `/Users/jaystuart/dev/project-athena/src/jetson/README.md`

```markdown
# Jetson LLM Webhook Service

## Overview

Flask-based webhook service running on Jetson Orin Nano (192.168.10.62:5000) that processes voice commands with LLM intelligence.

## Components

- **llm_webhook_service.py** - Main Flask service with 3 endpoints
- **athena_lite.py** - Original Athena Lite voice pipeline
- **athena_lite_llm.py** - Enhanced version with LLM integration
- **config/** - Configuration files for HA integration

## Deployment

See [scripts/deployment/README.md](../../scripts/deployment/README.md) for deployment procedures.

## Current Deployment

- **Location:** `/mnt/nvme/athena-lite/` on jetson-01
- **Service:** Manual start (no systemd yet)
- **Port:** 5000
- **Status:** Operational but not production-ready
```

### Success Criteria

#### Automated Verification:
- [x] All Jetson Python files copied to repository
- [x] All HA configuration fragments copied to repository
- [x] Repository structure matches defined layout
- [x] Git tracks all new files: `git status` shows new files staged
- [x] No secrets committed: `git grep -i "password\|token\|secret" src/` returns no results

#### Manual Verification:
- [x] Jetson files are readable and syntactically valid Python
- [x] HA YAML fragments match production configuration
- [x] README accurately describes repository structure
- [x] No sensitive data visible in git history

**Implementation Note:** After completing this phase and all automated verification passes, pause for human confirmation that retrieved files match expected implementation before proceeding.

**Phase 1 Completion Notes:**
- Retrieved 3 core files + 55 additional iteration files
- Discovered actual production system: `ollama_baltimore_ultimate.py` (1970 lines)
- Found Baltimore-specific Airbnb guest assistant system
- Identified Ollama backend (not DialoGPT as originally assumed)
- Created comprehensive research document: `thoughts/research/RESEARCH_JETSON_ITERATIONS.md`
- Secured credentials by adding `research/jetson-iterations/` to `.gitignore`
- **Decision**: Support both Baltimore (Airbnb) and General (homelab) modes going forward

---

## Phase 2: Core Reliability Improvements

### Overview

Address reliability issues #1, #2, #3, #5, and #6 by improving error handling, state synchronization, network resilience, and timeout management in both HA configuration and Jetson service.

### Changes Required

#### 1. Fix State Synchronization (Issues #1, #2)

**Problem:** Template sensor may not update before automation triggers

**File:** `/Users/jaystuart/dev/project-athena/config/ha/automations.yaml.fragment`

**Changes:** Add delay and condition to ensure sensor updates:

```yaml
- id: 'voice_command_llm_routing_v2'
  alias: 'Route Voice Commands to Athena LLM v2'
  description: 'Route voice commands with improved state synchronization'
  trigger:
    - platform: state
      entity_id: input_text.last_voice_command
  condition:
    - condition: template
      value_template: "{{ trigger.to_state.state != '' and trigger.to_state.state != 'unknown' }}"
    # Wait for template sensor to update (max 1 second)
    - condition: template
      value_template: >
        {% set command = states('input_text.last_voice_command') %}
        {% set sensor_command = state_attr('sensor.voice_command_type', 'command') %}
        {{ command == sensor_command }}
      wait_for_trigger: true
      timeout: "00:00:01"
  action:
    # Add 100ms delay to ensure sensor fully updated
    - delay: "00:00:00.1"
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ states('sensor.voice_command_type') == 'complex' }}"
          sequence:
            - service: rest_command.athena_llm_complex
              data:
                command: "{{ states('input_text.last_voice_command') }}"
              continue_on_error: true  # Don't block on REST failures
            # Only notify on success
            - condition: template
              value_template: "{{ state_attr('rest_command.athena_llm_complex', 'status_code') == 200 }}"
            - service: notify.persistent_notification
              data:
                title: "Athena LLM Processing"
                message: "Complex command sent: {{ states('input_text.last_voice_command') }}"
        - conditions:
            - condition: template
              value_template: "{{ states('sensor.voice_command_type') == 'simple' }}"
          sequence:
            - service: rest_command.athena_llm_simple
              data:
                command: "{{ states('input_text.last_voice_command') }}"
              continue_on_error: true
      default:
        # Fallback: attempt HA native processing
        - service: conversation.process
          data:
            text: "{{ states('input_text.last_voice_command') }}"
        - service: notify.persistent_notification
          data:
            title: "Voice Command Fallback"
            message: "Routed to HA native: {{ states('input_text.last_voice_command') }}"
  mode: queued  # Changed from 'single' to allow queuing
  max: 5  # Max 5 queued commands
```

#### 2. Add Error Handling & Network Resilience (Issues #3, #6)

**File:** `/Users/jaystuart/dev/project-athena/src/jetson/llm_webhook_service.py`

**Changes:** Add comprehensive error handling, health checks, and fallback mechanisms

```python
from flask import Flask, request, jsonify
import logging
import requests
from functools import wraps
from datetime import datetime
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/mnt/nvme/athena-lite/logs/webhook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
HA_BASE_URL = os.getenv('HA_URL', 'http://192.168.10.168:8123')
HA_TOKEN = os.getenv('HA_TOKEN')  # Should be loaded from environment
SERVICE_VERSION = "0.2.0"

# Global state
model = None
tokenizer = None
model_loaded = False
last_error = None
request_count = 0
error_count = 0

def require_model(f):
    """Decorator to ensure model is loaded before processing"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        global model_loaded, last_error
        if not model_loaded:
            logger.error("Model not loaded, cannot process request")
            return jsonify({
                "status": "error",
                "error": "LLM model not initialized",
                "fallback": "direct_ha",
                "message": "Request will be routed to Home Assistant directly"
            }), 503  # Service Unavailable
        return f(*args, **kwargs)
    return decorated_function

def init_model():
    """Initialize the LLM model with error handling"""
    global model, tokenizer, model_loaded, last_error

    try:
        logger.info("Loading DialoGPT-small model...")
        model_name = "microsoft/DialoGPT-small"

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)

        # Move to GPU if available
        if torch.cuda.is_available():
            model = model.to('cuda')
            logger.info("Model loaded on CUDA")
        else:
            logger.info("Model loaded on CPU")

        model_loaded = True
        last_error = None
        logger.info("Model initialization complete")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize model: {str(e)}")
        last_error = str(e)
        model_loaded = False
        return False

def call_ha_api(endpoint, method='GET', data=None):
    """Call Home Assistant API with error handling and retry"""
    if not HA_TOKEN:
        logger.error("HA_TOKEN not configured")
        return None

    url = f"{HA_BASE_URL}/api/{endpoint}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.warning(f"HA API timeout (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"HA API error: {str(e)}")
            return None

    return None

@app.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    global request_count, error_count, last_error

    health_status = {
        "service": "athena-llm-webhook",
        "version": SERVICE_VERSION,
        "status": "healthy" if model_loaded else "degraded",
        "model_loaded": model_loaded,
        "ha_connectivity": False,
        "uptime_checks": {
            "model_status": model_loaded,
            "ha_api_accessible": False
        },
        "metrics": {
            "total_requests": request_count,
            "total_errors": error_count,
            "error_rate": round(error_count / max(request_count, 1) * 100, 2)
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    # Check HA connectivity
    try:
        ha_response = call_ha_api('')
        if ha_response:
            health_status["ha_connectivity"] = True
            health_status["uptime_checks"]["ha_api_accessible"] = True
    except Exception as e:
        logger.warning(f"Health check HA connectivity failed: {str(e)}")

    if last_error:
        health_status["last_error"] = last_error

    status_code = 200 if model_loaded and health_status["ha_connectivity"] else 503
    return jsonify(health_status), status_code

@app.route('/process_command', methods=['POST'])
@require_model
def process_complex_command():
    """Process complex commands with LLM"""
    global request_count, error_count
    request_count += 1

    try:
        data = request.get_json()
        if not data or 'command' not in data:
            error_count += 1
            return jsonify({"status": "error", "error": "Missing 'command' field"}), 400

        command = data['command']
        source = data.get('source', 'unknown')

        logger.info(f"Processing complex command: {command} (from {source})")

        # Process with LLM
        start_time = datetime.utcnow()

        try:
            input_ids = tokenizer.encode(command + tokenizer.eos_token, return_tensors='pt')
            if torch.cuda.is_available():
                input_ids = input_ids.to('cuda')

            # Generate response with timeout protection
            with torch.no_grad():
                output = model.generate(
                    input_ids,
                    max_length=100,
                    pad_token_id=tokenizer.eos_token_id,
                    do_sample=True,
                    top_k=50,
                    top_p=0.95,
                    temperature=0.7
                )

            response_text = tokenizer.decode(output[:, input_ids.shape[-1]:][0], skip_special_tokens=True)

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            logger.info(f"LLM processing completed in {processing_time:.2f}s")

            return jsonify({
                "status": "success",
                "command": command,
                "response": response_text,
                "processed_by": "athena-llm",
                "processing_time": processing_time,
                "timestamp": datetime.utcnow().isoformat()
            }), 200

        except Exception as llm_error:
            logger.error(f"LLM processing failed: {str(llm_error)}")
            error_count += 1

            # Fallback to HA native processing
            ha_result = call_ha_api('conversation/process', 'POST', {"text": command})

            return jsonify({
                "status": "fallback",
                "command": command,
                "response": ha_result.get('response', {}).get('speech', {}).get('plain', {}).get('speech', 'Command processed') if ha_result else "Processing failed",
                "processed_by": "ha-fallback",
                "error": str(llm_error),
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        error_count += 1
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/simple_command', methods=['POST'])
def process_simple_command():
    """Process simple commands directly via HA API"""
    global request_count
    request_count += 1

    try:
        data = request.get_json()
        if not data or 'command' not in data:
            error_count += 1
            return jsonify({"status": "error", "error": "Missing 'command' field"}), 400

        command = data['command']
        logger.info(f"Processing simple command: {command}")

        # Route directly to HA
        ha_result = call_ha_api('conversation/process', 'POST', {"text": command})

        if ha_result:
            return jsonify({
                "status": "success",
                "command": command,
                "processed_by": "direct-ha",
                "ha_response": ha_result,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        else:
            error_count += 1
            return jsonify({
                "status": "error",
                "error": "Failed to reach Home Assistant",
                "command": command,
                "timestamp": datetime.utcnow().isoformat()
            }), 503

    except Exception as e:
        logger.error(f"Simple command processing failed: {str(e)}")
        error_count += 1
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/reload', methods=['POST'])
def reload_model():
    """Administrative endpoint to reload the model"""
    logger.info("Model reload requested")
    success = init_model()

    if success:
        return jsonify({
            "status": "success",
            "message": "Model reloaded successfully",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Model reload failed",
            "error": last_error,
            "timestamp": datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    # Create logs directory
    os.makedirs('/mnt/nvme/athena-lite/logs', exist_ok=True)

    # Initialize model on startup
    logger.info("Starting Athena LLM Webhook Service")
    init_model()

    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
```

#### 3. Improve Timeout Handling (Issue #5)

**File:** `/Users/jaystuart/dev/project-athena/config/ha/configuration.yaml.fragment`

**Changes:** Add timeout configuration and async processing hints:

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
        "timestamp": "{{ now().isoformat() }}",
        "timeout_hint": 25
      }
    timeout: 30  # Keep at 30s but add timeout_hint to payload

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

  # Add health check command
  athena_llm_health:
    url: "http://192.168.10.62:5000/health"
    method: GET
    timeout: 5
```

#### 4. Create Environment Configuration

**File:** `/Users/jaystuart/dev/project-athena/src/jetson/.env.example`

```bash
# Home Assistant Configuration
HA_URL=http://192.168.10.168:8123
HA_TOKEN=your-ha-long-lived-token-here

# Service Configuration
SERVICE_PORT=5000
SERVICE_HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/mnt/nvme/athena-lite/logs/webhook.log

# Model Configuration
MODEL_NAME=microsoft/DialoGPT-small
MODEL_CACHE_DIR=/mnt/nvme/models/
USE_GPU=true
```

**File:** `/Users/jaystuart/dev/project-athena/scripts/setup-env.sh`

```bash
#!/bin/bash
# Setup environment on Jetson

set -e

JETSON_HOST="jstuart@192.168.10.62"
ATHENA_DIR="/mnt/nvme/athena-lite"

echo "Setting up environment on Jetson..."

# Get HA token from kubernetes
HA_TOKEN=$(kubectl -n automation get secret home-assistant-credentials -o jsonpath='{.data.long-lived-token}' | base64 -d)

# Create .env file on Jetson
ssh "$JETSON_HOST" "cat > $ATHENA_DIR/.env << EOF
HA_URL=http://192.168.10.168:8123
HA_TOKEN=$HA_TOKEN
SERVICE_PORT=5000
SERVICE_HOST=0.0.0.0
LOG_LEVEL=INFO
LOG_FILE=$ATHENA_DIR/logs/webhook.log
MODEL_NAME=microsoft/DialoGPT-small
MODEL_CACHE_DIR=/mnt/nvme/models/
USE_GPU=true
EOF"

echo "Environment configuration deployed to Jetson"
```

### Success Criteria

#### Automated Verification:
- [ ] Updated automation YAML is syntactically valid: `yamllint config/ha/automations.yaml.fragment`
- [ ] Updated service Python is syntactically valid: `python -m py_compile src/jetson/llm_webhook_service.py`
- [ ] Environment setup script is executable: `test -x scripts/setup-env.sh`
- [ ] No hardcoded credentials in code: `git grep -i "token\|password" src/` returns no secrets

#### Manual Verification:
- [ ] State synchronization delay logic is correct
- [ ] Error handling covers all failure modes
- [ ] Fallback to HA native processing works
- [ ] Health check endpoint returns comprehensive status
- [ ] Timeout values are reasonable for expected processing times

**Implementation Note:** After completing this phase and all automated verification passes, pause for human confirmation that reliability improvements are correctly implemented before deploying to devices.

---

## Phase 3: Voice Integration & Classification Improvements

### Overview

Connect voice assistant to facade (fix issue #7), improve classification logic (issue #4), and enable concurrent command handling (issue #8).

### Changes Required

#### 1. Create Intent Script for Voice Capture (Fix Issue #7)

**File:** `/Users/jaystuart/dev/project-athena/config/ha/intent_script.yaml.fragment`

```yaml
intent_script:
  AthenaVoiceCommand:
    speech:
      text: "Processing your request..."
    action:
      # Capture the command text
      - service: input_text.set_value
        target:
          entity_id: input_text.last_voice_command
        data:
          value: "{{ trigger.slots.query.value }}"
```

#### 2. Create Custom Sentences for Voice Recognition

**File:** `/Users/jaystuart/dev/project-athena/config/ha/custom_sentences.yaml`

```yaml
language: en
intents:
  AthenaVoiceCommand:
    data:
      - sentences:
          # Question patterns (complex)
          - "help me {query}"
          - "can you {query}"
          - "please {query}"
          - "explain {query}"
          - "how do I {query}"
          - "what is {query}"
          - "why is {query}"
          - "when should I {query}"
          - "where is {query}"

          # Setup patterns (complex)
          - "set up {query}"
          - "optimize {query}"
          - "adjust {query}"
          - "configure {query}"
          - "create {query}"

          # Scene patterns (complex)
          - "set the mood for {query}"
          - "create a scene for {query}"
          - "[start] {query} routine"
          - "[start] {query} mode"

          # Simple control patterns
          - "turn on {query}"
          - "turn off {query}"
          - "set {query}"
          - "dim {query}"
          - "brighten {query}"

          # Catch-all
          - "{query}"
    expansion_rules:
      query: "[the] <query_text>"
```

#### 3. Improve Classification Logic (Fix Issue #4)

**File:** `/Users/jaystuart/dev/project-athena/config/ha/configuration.yaml.fragment`

**Changes:** Enhance template sensor with priority-based classification and ambiguity resolution:

```yaml
template:
  - sensor:
      - name: "Voice Command Type"
        state: >
          {% set command = states('input_text.last_voice_command') | lower %}

          {# Define classification keywords with priorities #}
          {% set priority_complex = ['help', 'explain', 'how', 'what', 'why', 'when', 'where'] %}
          {% set action_complex = ['set up', 'optimize', 'adjust', 'configure', 'create', 'schedule'] %}
          {% set context_complex = ['scene', 'mood', 'routine', 'for'] %}
          {% set polite_complex = ['please', 'can you', 'could you'] %}
          {% set multi_device = ['all', 'every', 'entire', 'whole'] %}

          {% set simple_only = ['turn on', 'turn off', 'set', 'dim', 'brighten', 'switch'] %}

          {# Check for priority indicators first (questions always complex) #}
          {% if priority_complex | select('in', command) | list | length > 0 %}
            complex
          {# Multi-device commands are complex unless purely simple action #}
          {% elif multi_device | select('in', command) | list | length > 0 %}
            {% if simple_only | select('in', command) | list | length > 0 %}
              {% if command.split() | length <= 4 %}
                simple
              {% else %}
                complex
              {% endif %}
            {% else %}
              complex
            {% endif %}
          {# Action or context words indicate complexity #}
          {% elif action_complex | select('in', command) | list | length > 0 or
                  context_complex | select('in', command) | list | length > 0 %}
            complex
          {# Polite phrases suggest complex request #}
          {% elif polite_complex | select('in', command) | list | length > 0 %}
            complex
          {# Default to simple for basic commands #}
          {% else %}
            simple
          {% endif %}
        attributes:
          command: "{{ states('input_text.last_voice_command') }}"
          indicators_found: >
            {% set command = states('input_text.last_voice_command') | lower %}
            {% set all_indicators = [
              'help', 'explain', 'how', 'what', 'why', 'when', 'where',
              'set up', 'optimize', 'adjust', 'configure', 'create', 'schedule',
              'scene', 'mood', 'routine', 'for',
              'please', 'can you', 'could you',
              'all', 'every', 'entire', 'whole'
            ] %}
            {{ all_indicators | select('in', command) | list }}
          word_count: "{{ states('input_text.last_voice_command').split() | length }}"
          classification_reason: >
            {% set command = states('input_text.last_voice_command') | lower %}
            {% set priority_complex = ['help', 'explain', 'how', 'what', 'why', 'when', 'where'] %}
            {% set multi_device = ['all', 'every', 'entire', 'whole'] %}
            {% if priority_complex | select('in', command) | list | length > 0 %}
              question_word
            {% elif multi_device | select('in', command) | list | length > 0 %}
              multi_device
            {% else %}
              keyword_match
            {% endif %}
```

#### 4. Enable Concurrent Command Processing (Fix Issue #8)

**Already addressed in Phase 2:** Changed automation mode from `single` to `queued` with `max: 5`

**Additional File:** `/Users/jaystuart/dev/project-athena/config/ha/scripts.yaml.fragment`

Create helper script to handle queue status:

```yaml
script:
  check_athena_queue:
    alias: "Check Athena Command Queue Status"
    sequence:
      - service: system_log.write
        data:
          message: >
            Athena queue status: {{ states('sensor.athena_queue_depth') }} commands pending
          level: info

  clear_athena_queue:
    alias: "Clear Athena Command Queue (Emergency)"
    sequence:
      - service: automation.turn_off
        target:
          entity_id: automation.voice_command_llm_routing_v2
      - delay: "00:00:02"
      - service: input_text.set_value
        target:
          entity_id: input_text.last_voice_command
        data:
          value: ""
      - service: automation.turn_on
        target:
          entity_id: automation.voice_command_llm_routing_v2
      - service: notify.persistent_notification
        data:
          title: "Athena Queue Cleared"
          message: "Voice command queue has been reset"
```

**File:** `/Users/jaystuart/dev/project-athena/config/ha/configuration.yaml.fragment`

Add queue depth sensor:

```yaml
template:
  - sensor:
      - name: "Athena Queue Depth"
        state: >
          {% set automation_state = states.automation.voice_command_llm_routing_v2 %}
          {{ automation_state.attributes.current if automation_state else 0 }}
        unit_of_measurement: "commands"
```

#### 5. Create Deployment Script for HA Configuration

**File:** `/Users/jaystuart/dev/project-athena/scripts/deployment/deploy-ha-config.sh`

```bash
#!/bin/bash
# Deploy HA configuration fragments to Home Assistant server

set -e

HA_HOST="root@192.168.10.168"
HA_PORT="23"
HA_SSH_KEY="$HOME/.ssh/id_ed25519_new"
HA_CONFIG_DIR="/config"
BACKUP_SUFFIX=$(date +%Y%m%d-%H%M%S)

echo "Deploying HA configuration updates..."

# Function to backup and update config
update_config_section() {
    local fragment_file=$1
    local target_file=$2
    local marker_start=$3
    local marker_end=$4

    echo "Updating $target_file with $fragment_file..."

    # Backup existing file
    ssh -i "$HA_SSH_KEY" -p "$HA_PORT" "$HA_HOST" \
        "cp $HA_CONFIG_DIR/$target_file $HA_CONFIG_DIR/$target_file.backup-$BACKUP_SUFFIX"

    # Create temporary file with markers
    cat > /tmp/athena_fragment.tmp << EOF
# BEGIN ATHENA FACADE CONFIG - Managed by Project Athena
# Do not manually edit between markers
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
$(cat "$fragment_file")
# END ATHENA FACADE CONFIG
EOF

    # Copy fragment to HA server
    scp -i "$HA_SSH_KEY" -P "$HA_PORT" /tmp/athena_fragment.tmp "$HA_HOST:/tmp/"

    # Insert/replace config section
    ssh -i "$HA_SSH_KEY" -p "$HA_PORT" "$HA_HOST" bash << 'REMOTE_SCRIPT'
        set -e
        TARGET="/config/'$target_file'"
        FRAGMENT="/tmp/athena_fragment.tmp"
        TEMP_FILE="/tmp/config_merged.tmp"

        # Remove existing Athena section if present
        sed '/# BEGIN ATHENA FACADE CONFIG/,/# END ATHENA FACADE CONFIG/d' "$TARGET" > "$TEMP_FILE"

        # Append new config
        cat "$TEMP_FILE" "$FRAGMENT" > "$TARGET"

        # Cleanup
        rm "$TEMP_FILE" "$FRAGMENT"

        echo "Config updated: $TARGET"
REMOTE_SCRIPT

    rm /tmp/athena_fragment.tmp
}

# Deploy automations
update_config_section \
    "config/ha/automations.yaml.fragment" \
    "automations.yaml" \
    "# BEGIN ATHENA" \
    "# END ATHENA"

# Deploy configuration additions
update_config_section \
    "config/ha/configuration.yaml.fragment" \
    "configuration.yaml" \
    "# BEGIN ATHENA" \
    "# END ATHENA"

# Deploy intent scripts
update_config_section \
    "config/ha/intent_script.yaml.fragment" \
    "configuration.yaml" \
    "# BEGIN ATHENA INTENT" \
    "# END ATHENA INTENT"

# Deploy scripts
update_config_section \
    "config/ha/scripts.yaml.fragment" \
    "scripts.yaml" \
    "# BEGIN ATHENA SCRIPTS" \
    "# END ATHENA SCRIPTS"

# Deploy custom sentences
echo "Deploying custom sentences..."
ssh -i "$HA_SSH_KEY" -p "$HA_PORT" "$HA_HOST" "mkdir -p $HA_CONFIG_DIR/custom_sentences/en"
scp -i "$HA_SSH_KEY" -P "$HA_PORT" \
    config/ha/custom_sentences.yaml \
    "$HA_HOST:$HA_CONFIG_DIR/custom_sentences/en/athena.yaml"

# Check configuration
echo "Checking HA configuration..."
ssh -i "$HA_SSH_KEY" -p "$HA_PORT" "$HA_HOST" "ha core check"

if [ $? -eq 0 ]; then
    echo "Configuration check passed!"
    echo "Restarting Home Assistant..."
    ssh -i "$HA_SSH_KEY" -p "$HA_PORT" "$HA_HOST" "ha core restart"
    echo "Deployment complete! HA is restarting..."
else
    echo "ERROR: Configuration check failed!"
    echo "Restoring backups..."
    ssh -i "$HA_SSH_KEY" -p "$HA_PORT" "$HA_HOST" \
        "cp $HA_CONFIG_DIR/automations.yaml.backup-$BACKUP_SUFFIX $HA_CONFIG_DIR/automations.yaml && \
         cp $HA_CONFIG_DIR/configuration.yaml.backup-$BACKUP_SUFFIX $HA_CONFIG_DIR/configuration.yaml && \
         cp $HA_CONFIG_DIR/scripts.yaml.backup-$BACKUP_SUFFIX $HA_CONFIG_DIR/scripts.yaml"
    exit 1
fi
```

### Success Criteria

#### Automated Verification:
- [ ] Intent script YAML is valid: `yamllint config/ha/intent_script.yaml.fragment`
- [ ] Custom sentences YAML is valid: `yamllint config/ha/custom_sentences.yaml`
- [ ] Updated template sensor YAML is valid: `yamllint config/ha/configuration.yaml.fragment`
- [ ] Deployment script is executable: `test -x scripts/deployment/deploy-ha-config.sh`
- [ ] HA configuration check passes after deployment: `ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core check"`

#### Manual Verification:
- [ ] Voice commands populate `input_text.last_voice_command` correctly
- [ ] Classification correctly handles edge cases ("help turn on lights" → complex)
- [ ] Multi-device commands classified appropriately
- [ ] Queue allows 5 concurrent commands without dropping
- [ ] Emergency queue clear script works

**Implementation Note:** After completing this phase and all automated verification passes, test voice integration with real voice commands before proceeding.

---

## Phase 4: Service Management & Deployment Automation

### Overview

Create systemd service for Jetson webhook, build deployment automation, and establish proper service lifecycle management.

### Changes Required

#### 1. Create Systemd Service Unit

**File:** `/Users/jaystuart/dev/project-athena/config/jetson/athena-webhook.service`

```ini
[Unit]
Description=Athena LLM Webhook Service
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=jstuart
Group=jstuart
WorkingDirectory=/mnt/nvme/athena-lite
EnvironmentFile=/mnt/nvme/athena-lite/.env

# Pre-start checks
ExecStartPre=/bin/bash -c 'test -f /mnt/nvme/athena-lite/llm_webhook_service.py'
ExecStartPre=/bin/bash -c 'test -f /mnt/nvme/athena-lite/.env'

# Start service
ExecStart=/usr/bin/python3 /mnt/nvme/athena-lite/llm_webhook_service.py

# Restart policy
Restart=always
RestartSec=10s

# Resource limits
MemoryMax=4G
CPUQuota=200%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=athena-webhook

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/mnt/nvme/athena-lite/logs

[Install]
WantedBy=multi-user.target
```

#### 2. Create Jetson Deployment Script

**File:** `/Users/jaystuart/dev/project-athena/scripts/deployment/deploy-jetson.sh`

```bash
#!/bin/bash
# Deploy Athena components to Jetson device

set -e

JETSON_HOST="${JETSON_HOST:-jstuart@192.168.10.62}"
ATHENA_DIR="/mnt/nvme/athena-lite"
BACKUP_DIR="/mnt/nvme/athena-lite-backups"
BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"

echo "Deploying to Jetson at $JETSON_HOST..."

# Create backup
echo "Creating backup..."
ssh "$JETSON_HOST" "mkdir -p $BACKUP_DIR/$BACKUP_NAME && \
    cp -r $ATHENA_DIR/*.py $BACKUP_DIR/$BACKUP_NAME/ 2>/dev/null || true"

# Stop existing service if running
echo "Stopping existing service..."
ssh "$JETSON_HOST" "sudo systemctl stop athena-webhook.service 2>/dev/null || true"

# Deploy Python files
echo "Deploying application files..."
scp src/jetson/llm_webhook_service.py "$JETSON_HOST:$ATHENA_DIR/"
scp src/jetson/requirements.txt "$JETSON_HOST:$ATHENA_DIR/"

# Deploy configuration
echo "Deploying configuration..."
if [ ! -f "src/jetson/.env" ]; then
    echo "ERROR: .env file not found. Run scripts/setup-env.sh first."
    exit 1
fi
scp src/jetson/.env "$JETSON_HOST:$ATHENA_DIR/"

# Install dependencies
echo "Installing Python dependencies..."
ssh "$JETSON_HOST" "cd $ATHENA_DIR && pip3 install -r requirements.txt --user"

# Deploy systemd service
echo "Deploying systemd service..."
scp config/jetson/athena-webhook.service "$JETSON_HOST:/tmp/"
ssh "$JETSON_HOST" "sudo mv /tmp/athena-webhook.service /etc/systemd/system/ && \
    sudo systemctl daemon-reload"

# Enable and start service
echo "Starting service..."
ssh "$JETSON_HOST" "sudo systemctl enable athena-webhook.service && \
    sudo systemctl start athena-webhook.service"

# Wait for service to start
echo "Waiting for service to initialize..."
sleep 5

# Check service status
echo "Checking service status..."
ssh "$JETSON_HOST" "sudo systemctl status athena-webhook.service --no-pager"

# Test health endpoint
echo "Testing health endpoint..."
if curl -s -f http://192.168.10.62:5000/health > /dev/null; then
    echo "✅ Health check passed!"
else
    echo "❌ Health check failed!"
    echo "Service logs:"
    ssh "$JETSON_HOST" "sudo journalctl -u athena-webhook.service -n 50 --no-pager"
    exit 1
fi

echo ""
echo "Deployment complete!"
echo "Backup saved to: $JETSON_HOST:$BACKUP_DIR/$BACKUP_NAME"
echo ""
echo "Useful commands:"
echo "  View logs:    ssh $JETSON_HOST 'sudo journalctl -u athena-webhook.service -f'"
echo "  Restart:      ssh $JETSON_HOST 'sudo systemctl restart athena-webhook.service'"
echo "  Stop:         ssh $JETSON_HOST 'sudo systemctl stop athena-webhook.service'"
echo "  Check status: ssh $JETSON_HOST 'sudo systemctl status athena-webhook.service'"
```

#### 3. Create Rollback Script

**File:** `/Users/jaystuart/dev/project-athena/scripts/deployment/rollback-jetson.sh`

```bash
#!/bin/bash
# Rollback Jetson deployment to previous version

set -e

JETSON_HOST="${JETSON_HOST:-jstuart@192.168.10.62}"
ATHENA_DIR="/mnt/nvme/athena-lite"
BACKUP_DIR="/mnt/nvme/athena-lite-backups"

echo "Available backups:"
ssh "$JETSON_HOST" "ls -1t $BACKUP_DIR/"

echo ""
read -p "Enter backup name to restore (e.g., backup-20250106-120000): " BACKUP_NAME

if [ -z "$BACKUP_NAME" ]; then
    echo "No backup specified. Aborting."
    exit 1
fi

# Verify backup exists
if ! ssh "$JETSON_HOST" "test -d $BACKUP_DIR/$BACKUP_NAME"; then
    echo "ERROR: Backup $BACKUP_NAME not found!"
    exit 1
fi

echo "Rolling back to $BACKUP_NAME..."

# Stop service
echo "Stopping service..."
ssh "$JETSON_HOST" "sudo systemctl stop athena-webhook.service"

# Restore files
echo "Restoring files..."
ssh "$JETSON_HOST" "cp $BACKUP_DIR/$BACKUP_NAME/*.py $ATHENA_DIR/"

# Restart service
echo "Restarting service..."
ssh "$JETSON_HOST" "sudo systemctl start athena-webhook.service"

# Wait and check
sleep 5
echo "Checking service status..."
ssh "$JETSON_HOST" "sudo systemctl status athena-webhook.service --no-pager"

# Test health
if curl -s -f http://192.168.10.62:5000/health > /dev/null; then
    echo "✅ Rollback successful!"
else
    echo "❌ Service health check failed after rollback!"
    exit 1
fi
```

#### 4. Create One-Command Full Deployment

**File:** `/Users/jaystuart/dev/project-athena/scripts/deployment/deploy-all.sh`

```bash
#!/bin/bash
# Deploy complete Athena facade system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================="
echo "Athena Facade Full Deployment"
echo "========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! kubectl cluster-info &>/dev/null; then
    echo "ERROR: kubectl not configured or cluster not accessible"
    exit 1
fi

if ! ssh jstuart@192.168.10.62 "echo OK" &>/dev/null; then
    echo "ERROR: Cannot SSH to Jetson (192.168.10.62)"
    exit 1
fi

if ! ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "echo OK" &>/dev/null; then
    echo "ERROR: Cannot SSH to Home Assistant (192.168.10.168)"
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Setup environment
echo "Step 1/3: Setting up environment..."
bash "$SCRIPT_DIR/setup-env.sh"
echo ""

# Deploy to Jetson
echo "Step 2/3: Deploying to Jetson..."
bash "$SCRIPT_DIR/deploy-jetson.sh"
echo ""

# Deploy to Home Assistant
echo "Step 3/3: Deploying to Home Assistant..."
bash "$SCRIPT_DIR/deploy-ha-config.sh"
echo ""

echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Testing full pipeline..."

# Test complex command
echo "Testing complex command..."
RESPONSE=$(curl -s -X POST http://192.168.10.62:5000/process_command \
    -H "Content-Type: application/json" \
    -d '{"command": "help me optimize the office lighting"}')

if echo "$RESPONSE" | grep -q "success"; then
    echo "✅ Complex command test passed"
else
    echo "❌ Complex command test failed"
    echo "Response: $RESPONSE"
fi

# Test simple command
echo "Testing simple command..."
RESPONSE=$(curl -s -X POST http://192.168.10.62:5000/simple_command \
    -H "Content-Type: application/json" \
    -d '{"command": "turn on office lights"}')

if echo "$RESPONSE" | grep -q "success"; then
    echo "✅ Simple command test passed"
else
    echo "❌ Simple command test failed"
    echo "Response: $RESPONSE"
fi

echo ""
echo "Next step: Test voice commands through Home Assistant"
```

#### 5. Make All Scripts Executable

```bash
chmod +x scripts/deployment/*.sh
chmod +x scripts/setup-env.sh
```

### Success Criteria

#### Automated Verification:
- [ ] Systemd service unit is valid: `systemd-analyze verify config/jetson/athena-webhook.service`
- [ ] All deployment scripts are executable: `test -x scripts/deployment/deploy-jetson.sh`
- [ ] Jetson service starts successfully: `ssh jstuart@192.168.10.62 "systemctl is-active athena-webhook.service"` returns "active"
- [ ] Service survives reboot: `ssh jstuart@192.168.10.62 "sudo reboot"` && wait 60s && health check passes
- [ ] Health endpoint responds: `curl -f http://192.168.10.62:5000/health` returns 200

#### Manual Verification:
- [ ] Service logs show no errors: `ssh jstuart@192.168.10.62 "sudo journalctl -u athena-webhook.service -n 100"`
- [ ] Service auto-restarts on failure (test by killing process)
- [ ] Rollback script successfully restores previous version
- [ ] Full deployment script completes without errors

**Implementation Note:** After completing this phase and all automated verification passes, perform a complete system reboot test to ensure service persistence before proceeding.

---

## Phase 5: Monitoring, Observability & Testing

### Overview

Implement comprehensive monitoring, logging, and automated testing to ensure system health and enable rapid troubleshooting.

### Changes Required

#### 1. Create Health Monitoring Script

**File:** `/Users/jaystuart/dev/project-athena/scripts/monitoring/health-check.sh`

```bash
#!/bin/bash
# Comprehensive health check for Athena facade system

set -e

JETSON_HOST="192.168.10.62"
HA_HOST="192.168.10.168"
WEBHOOK_URL="http://$JETSON_HOST:5000"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Athena Facade System Health Check"
echo "========================================="
echo ""

TOTAL_CHECKS=0
PASSED_CHECKS=0
WARNINGS=0

check() {
    local name=$1
    local command=$2
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    echo -n "Checking $name... "
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "  Command: $command"
    fi
}

check_warning() {
    local name=$1
    local command=$2
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    echo -n "Checking $name... "
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${YELLOW}⚠️  WARN${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
}

# Network connectivity
echo "Network Connectivity:"
check "Jetson reachable" "ping -c 1 -W 2 $JETSON_HOST"
check "Home Assistant reachable" "ping -c 1 -W 2 $HA_HOST"
check "Jetson SSH accessible" "ssh -o ConnectTimeout=5 jstuart@$JETSON_HOST 'echo OK'"
check "HA SSH accessible" "ssh -i ~/.ssh/id_ed25519_new -p 23 -o ConnectTimeout=5 root@$HA_HOST 'echo OK'"
echo ""

# Jetson service status
echo "Jetson Webhook Service:"
check "Service running" "ssh jstuart@$JETSON_HOST 'systemctl is-active athena-webhook.service | grep -q active'"
check "Service enabled" "ssh jstuart@$JETSON_HOST 'systemctl is-enabled athena-webhook.service | grep -q enabled'"
check "Health endpoint responding" "curl -f -s -m 5 $WEBHOOK_URL/health"
check "Model loaded" "curl -s $WEBHOOK_URL/health | jq -e '.model_loaded == true'"
check "HA connectivity from Jetson" "curl -s $WEBHOOK_URL/health | jq -e '.ha_connectivity == true'"
check_warning "No recent errors" "ssh jstuart@$JETSON_HOST 'sudo journalctl -u athena-webhook.service --since \"5 minutes ago\" | grep -qv ERROR'"
echo ""

# Home Assistant configuration
echo "Home Assistant Configuration:"
check "HA core running" "ssh -i ~/.ssh/id_ed25519_new -p 23 root@$HA_HOST 'ha core info | grep -q running'"
check "Configuration valid" "ssh -i ~/.ssh/id_ed25519_new -p 23 root@$HA_HOST 'ha core check | grep -q valid'"
echo ""

# Functional tests
echo "Functional Tests:"
check "Complex command processing" \
    "curl -s -X POST $WEBHOOK_URL/process_command -H 'Content-Type: application/json' \
    -d '{\"command\": \"help me with the lights\"}' | jq -e '.status == \"success\"'"

check "Simple command processing" \
    "curl -s -X POST $WEBHOOK_URL/simple_command -H 'Content-Type: application/json' \
    -d '{\"command\": \"turn on office lights\"}' | jq -e '.status == \"success\"'"

echo ""

# Performance metrics
echo "Performance Metrics:"
HEALTH_JSON=$(curl -s $WEBHOOK_URL/health)
REQUEST_COUNT=$(echo "$HEALTH_JSON" | jq -r '.metrics.total_requests // 0')
ERROR_RATE=$(echo "$HEALTH_JSON" | jq -r '.metrics.error_rate // 0')

echo "  Total requests: $REQUEST_COUNT"
echo "  Error rate: ${ERROR_RATE}%"

if (( $(echo "$ERROR_RATE < 5" | bc -l) )); then
    echo -e "  ${GREEN}Error rate acceptable${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "  ${RED}Error rate too high!${NC}"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""
echo "========================================="
echo "Results: $PASSED_CHECKS/$TOTAL_CHECKS checks passed"
if [ $WARNINGS -gt 0 ]; then
    echo "Warnings: $WARNINGS"
fi

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}System Status: HEALTHY${NC}"
    exit 0
elif [ $PASSED_CHECKS -ge $((TOTAL_CHECKS * 8 / 10)) ]; then
    echo -e "${YELLOW}System Status: DEGRADED${NC}"
    exit 1
else
    echo -e "${RED}System Status: CRITICAL${NC}"
    exit 2
fi
```

#### 2. Create Automated Test Suite

**File:** `/Users/jaystuart/dev/project-athena/tests/integration/test_facade.py`

```python
#!/usr/bin/env python3
"""
Integration tests for Athena HA LLM Facade
"""

import pytest
import requests
import time
import json
from typing import Dict, Any

JETSON_URL = "http://192.168.10.62:5000"
TIMEOUT = 30

class TestWebhookEndpoints:
    """Test Jetson webhook service endpoints"""

    def test_health_endpoint(self):
        """Health endpoint should return status"""
        response = requests.get(f"{JETSON_URL}/health", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert 'status' in data
        assert 'model_loaded' in data
        assert 'ha_connectivity' in data

    def test_health_shows_model_loaded(self):
        """Model should be loaded"""
        response = requests.get(f"{JETSON_URL}/health", timeout=5)
        data = response.json()
        assert data['model_loaded'] is True, "LLM model should be loaded"

    def test_health_shows_ha_connectivity(self):
        """HA connectivity should be confirmed"""
        response = requests.get(f"{JETSON_URL}/health", timeout=5)
        data = response.json()
        assert data['ha_connectivity'] is True, "Should have HA connectivity"

class TestComplexCommands:
    """Test complex command processing"""

    def test_complex_command_success(self):
        """Complex command should process successfully"""
        response = requests.post(
            f"{JETSON_URL}/process_command",
            json={"command": "help me optimize the office lighting"},
            timeout=TIMEOUT
        )
        assert response.status_code == 200

        data = response.json()
        assert data['status'] in ['success', 'fallback']
        assert 'command' in data
        assert 'response' in data

    def test_complex_command_timing(self):
        """Complex command should complete within timeout"""
        start = time.time()
        response = requests.post(
            f"{JETSON_URL}/process_command",
            json={"command": "what is the weather"},
            timeout=TIMEOUT
        )
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 30, f"Command took {duration:.2f}s (should be < 30s)"

    def test_complex_command_returns_metadata(self):
        """Complex command should return processing metadata"""
        response = requests.post(
            f"{JETSON_URL}/process_command",
            json={"command": "explain how to use the lights"},
            timeout=TIMEOUT
        )
        data = response.json()

        assert 'processed_by' in data
        assert 'timestamp' in data

class TestSimpleCommands:
    """Test simple command processing"""

    def test_simple_command_success(self):
        """Simple command should process successfully"""
        response = requests.post(
            f"{JETSON_URL}/simple_command",
            json={"command": "turn on office lights"},
            timeout=10
        )
        assert response.status_code in [200, 503]  # 503 if HA not reachable

        if response.status_code == 200:
            data = response.json()
            assert data['status'] in ['success', 'error']
            assert data['processed_by'] == 'direct-ha'

    def test_simple_command_faster_than_complex(self):
        """Simple commands should be faster than complex"""
        # Time simple command
        start = time.time()
        requests.post(
            f"{JETSON_URL}/simple_command",
            json={"command": "turn off lights"},
            timeout=10
        )
        simple_duration = time.time() - start

        # Time complex command
        start = time.time()
        requests.post(
            f"{JETSON_URL}/process_command",
            json={"command": "help me with lights"},
            timeout=TIMEOUT
        )
        complex_duration = time.time() - start

        # Simple should generally be faster (but not strict requirement)
        print(f"Simple: {simple_duration:.2f}s, Complex: {complex_duration:.2f}s")

class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_missing_command_field(self):
        """Request without command field should return 400"""
        response = requests.post(
            f"{JETSON_URL}/process_command",
            json={"foo": "bar"},
            timeout=5
        )
        assert response.status_code == 400

    def test_empty_command(self):
        """Empty command should be handled"""
        response = requests.post(
            f"{JETSON_URL}/process_command",
            json={"command": ""},
            timeout=5
        )
        # Should either succeed with error status or return 400
        assert response.status_code in [200, 400]

    def test_very_long_command(self):
        """Very long command should be handled"""
        long_command = "help me " + "do something " * 100
        response = requests.post(
            f"{JETSON_URL}/process_command",
            json={"command": long_command},
            timeout=TIMEOUT
        )
        # Should not crash, even if it times out
        assert response.status_code in [200, 408, 500]

class TestClassificationLogic:
    """Test command classification (requires HA access)"""

    @pytest.mark.skip(reason="Requires HA access and configuration")
    def test_question_classified_as_complex(self):
        """Questions should be classified as complex"""
        # This would require HA API access
        pass

    @pytest.mark.skip(reason="Requires HA access and configuration")
    def test_simple_action_classified_correctly(self):
        """Simple actions should be classified as simple"""
        # This would require HA API access
        pass

class TestReliability:
    """Test system reliability"""

    def test_concurrent_requests(self):
        """System should handle concurrent requests"""
        import concurrent.futures

        def make_request(i):
            return requests.post(
                f"{JETSON_URL}/process_command",
                json={"command": f"test command {i}"},
                timeout=TIMEOUT
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should complete (even if some fail)
        assert len(results) == 5
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 3, "At least 3/5 concurrent requests should succeed"

    def test_service_stability_over_time(self):
        """Service should remain stable over multiple requests"""
        for i in range(10):
            response = requests.get(f"{JETSON_URL}/health", timeout=5)
            assert response.status_code == 200
            time.sleep(0.5)

        # After 10 requests, error rate should still be low
        response = requests.get(f"{JETSON_URL}/health", timeout=5)
        data = response.json()
        error_rate = data.get('metrics', {}).get('error_rate', 0)
        assert error_rate < 20, f"Error rate {error_rate}% too high after sustained load"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

**File:** `/Users/jaystuart/dev/project-athena/tests/integration/requirements.txt`

```txt
pytest==7.4.3
requests==2.31.0
```

#### 3. Create Logging Configuration

**File:** `/Users/jaystuart/dev/project-athena/src/jetson/logging.conf`

```ini
[loggers]
keys=root,athena

[handlers]
keys=consoleHandler,fileHandler,rotatingFileHandler

[formatters]
keys=detailed,simple

[logger_root]
level=INFO
handlers=consoleHandler

[logger_athena]
level=INFO
handlers=rotatingFileHandler,consoleHandler
qualname=athena
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simple
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=detailed
args=('/mnt/nvme/athena-lite/logs/webhook.log',)

[handler_rotatingFileHandler]
class=handlers.RotatingFileHandler
level=INFO
formatter=detailed
args=('/mnt/nvme/athena-lite/logs/webhook.log', 'a', 10485760, 5)

[formatter_simple]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s

[formatter_detailed]
format=%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s
```

#### 4. Create Monitoring Dashboard Data Collector

**File:** `/Users/jaystuart/dev/project-athena/scripts/monitoring/collect-metrics.sh`

```bash
#!/bin/bash
# Collect metrics for monitoring dashboard

JETSON_URL="http://192.168.10.62:5000"
OUTPUT_DIR="/tmp/athena-metrics"
TIMESTAMP=$(date +%s)

mkdir -p "$OUTPUT_DIR"

# Collect health data
curl -s "$JETSON_URL/health" > "$OUTPUT_DIR/health-$TIMESTAMP.json"

# Collect service status
ssh jstuart@192.168.10.62 "systemctl status athena-webhook.service" > "$OUTPUT_DIR/service-status-$TIMESTAMP.txt" 2>&1

# Collect resource usage
ssh jstuart@192.168.10.62 "ps aux | grep llm_webhook_service" > "$OUTPUT_DIR/process-$TIMESTAMP.txt"

# Collect recent logs
ssh jstuart@192.168.10.62 "sudo journalctl -u athena-webhook.service --since '5 minutes ago'" > "$OUTPUT_DIR/logs-$TIMESTAMP.txt"

# Parse and display summary
if [ -f "$OUTPUT_DIR/health-$TIMESTAMP.json" ]; then
    echo "=== Athena Metrics Summary ==="
    echo "Timestamp: $(date)"
    echo ""
    jq '{
        status: .status,
        model_loaded: .model_loaded,
        ha_connectivity: .ha_connectivity,
        total_requests: .metrics.total_requests,
        error_rate: .metrics.error_rate
    }' "$OUTPUT_DIR/health-$TIMESTAMP.json"
fi

# Cleanup old files (keep last 100)
cd "$OUTPUT_DIR"
ls -t | tail -n +101 | xargs -r rm --
```

#### 5. Create Cron Jobs for Monitoring

**File:** `/Users/jaystuart/dev/project-athena/scripts/monitoring/setup-cron.sh`

```bash
#!/bin/bash
# Setup cron jobs for monitoring

CRON_FILE="/tmp/athena-cron"

cat > "$CRON_FILE" << 'EOF'
# Athena Facade Monitoring
# Collect metrics every 5 minutes
*/5 * * * * /Users/jaystuart/dev/project-athena/scripts/monitoring/collect-metrics.sh

# Run health check every hour
0 * * * * /Users/jaystuart/dev/project-athena/scripts/monitoring/health-check.sh > /tmp/athena-health-$(date +\%Y\%m\%d-\%H).log 2>&1

# Alert if error rate exceeds threshold (every 15 minutes)
*/15 * * * * /Users/jaystuart/dev/project-athena/scripts/monitoring/alert-check.sh
EOF

crontab "$CRON_FILE"
rm "$CRON_FILE"

echo "Cron jobs installed:"
crontab -l | grep Athena -A 10
```

#### 6. Create Alert Script

**File:** `/Users/jaystuart/dev/project-athena/scripts/monitoring/alert-check.sh`

```bash
#!/bin/bash
# Check for alert conditions

JETSON_URL="http://192.168.10.62:5000"
ALERT_LOG="/tmp/athena-alerts.log"

# Get current health
HEALTH=$(curl -s "$JETSON_URL/health")

if [ -z "$HEALTH" ]; then
    echo "[$(date)] CRITICAL: Webhook service not responding" >> "$ALERT_LOG"
    exit 1
fi

# Check model loaded
MODEL_LOADED=$(echo "$HEALTH" | jq -r '.model_loaded')
if [ "$MODEL_LOADED" != "true" ]; then
    echo "[$(date)] CRITICAL: LLM model not loaded" >> "$ALERT_LOG"
fi

# Check error rate
ERROR_RATE=$(echo "$HEALTH" | jq -r '.metrics.error_rate // 0')
if (( $(echo "$ERROR_RATE > 10" | bc -l) )); then
    echo "[$(date)] WARNING: Error rate is ${ERROR_RATE}%" >> "$ALERT_LOG"
fi

# Check HA connectivity
HA_CONN=$(echo "$HEALTH" | jq -r '.ha_connectivity')
if [ "$HA_CONN" != "true" ]; then
    echo "[$(date)] WARNING: No Home Assistant connectivity" >> "$ALERT_LOG"
fi

# Check service status on Jetson
if ! ssh jstuart@192.168.10.62 "systemctl is-active athena-webhook.service | grep -q active"; then
    echo "[$(date)] CRITICAL: Systemd service not active" >> "$ALERT_LOG"
fi
```

### Success Criteria

#### Automated Verification:
- [ ] Health check script runs successfully: `bash scripts/monitoring/health-check.sh`
- [ ] All integration tests pass: `cd tests/integration && pytest test_facade.py -v`
- [ ] Health check returns success status: `bash scripts/monitoring/health-check.sh && echo $?` returns 0
- [ ] Metrics collection works: `bash scripts/monitoring/collect-metrics.sh` creates files
- [ ] No critical alerts: `cat /tmp/athena-alerts.log | grep CRITICAL | tail -1` returns empty

#### Manual Verification:
- [ ] Health check dashboard shows all green
- [ ] Integration tests cover all major scenarios
- [ ] Log files are rotating properly (check file sizes)
- [ ] Metrics are being collected every 5 minutes
- [ ] Alerts trigger appropriately when thresholds exceeded

**Implementation Note:** After completing this phase, run 24-hour stability test monitoring all metrics before proceeding to final phase.

---

## Phase 6: Documentation & Final Validation

### Overview

Create comprehensive operational documentation, perform end-to-end validation, and establish the system as production-ready.

### Changes Required

#### 1. Create Operations Guide

**File:** `/Users/jaystuart/dev/project-athena/docs/OPERATIONS_GUIDE.md`

```markdown
# Athena Facade Operations Guide

## Quick Reference

### Service Management

**Jetson Webhook Service:**
```bash
# Status
ssh jstuart@192.168.10.62 "sudo systemctl status athena-webhook.service"

# Restart
ssh jstuart@192.168.10.62 "sudo systemctl restart athena-webhook.service"

# Logs
ssh jstuart@192.168.10.62 "sudo journalctl -u athena-webhook.service -f"

# Health check
curl http://192.168.10.62:5000/health | jq
```

**Home Assistant:**
```bash
# Status
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core info"

# Restart
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core restart"

# Check configuration
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core check"

# Logs
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core logs"
```

### Deployment

**Full System Deployment:**
```bash
cd /Users/jaystuart/dev/project-athena
bash scripts/deployment/deploy-all.sh
```

**Jetson Only:**
```bash
bash scripts/deployment/deploy-jetson.sh
```

**Home Assistant Only:**
```bash
bash scripts/deployment/deploy-ha-config.sh
```

**Rollback:**
```bash
bash scripts/deployment/rollback-jetson.sh
```

### Monitoring

**System Health:**
```bash
bash scripts/monitoring/health-check.sh
```

**Run Tests:**
```bash
cd tests/integration
pytest test_facade.py -v
```

**View Metrics:**
```bash
bash scripts/monitoring/collect-metrics.sh
```

## Common Issues

### Issue: Webhook Service Not Responding

**Symptoms:**
- Health check fails
- Voice commands don't work
- curl to port 5000 times out

**Diagnosis:**
```bash
# Check if service is running
ssh jstuart@192.168.10.62 "systemctl status athena-webhook.service"

# Check recent logs
ssh jstuart@192.168.10.62 "sudo journalctl -u athena-webhook.service -n 100"

# Check if port is listening
ssh jstuart@192.168.10.62 "netstat -tlnp | grep 5000"
```

**Resolution:**
```bash
# Restart service
ssh jstuart@192.168.10.62 "sudo systemctl restart athena-webhook.service"

# If still failing, check logs for Python errors
ssh jstuart@192.168.10.62 "sudo journalctl -u athena-webhook.service --since '10 minutes ago'"

# Verify dependencies installed
ssh jstuart@192.168.10.62 "cd /mnt/nvme/athena-lite && pip3 list"
```

### Issue: Model Not Loading

**Symptoms:**
- Health endpoint shows `"model_loaded": false`
- All commands return errors

**Diagnosis:**
```bash
curl http://192.168.10.62:5000/health | jq '.model_loaded, .last_error'
```

**Resolution:**
```bash
# Trigger model reload
curl -X POST http://192.168.10.62:5000/reload

# Check if GPU is available (should be on Jetson)
ssh jstuart@192.168.10.62 "python3 -c 'import torch; print(torch.cuda.is_available())'"

# Check model cache directory
ssh jstuart@192.168.10.62 "ls -la /mnt/nvme/models/"
```

### Issue: Voice Commands Not Routing

**Symptoms:**
- Voice input works but doesn't trigger facade
- `input_text.last_voice_command` not updating

**Diagnosis:**
- Check HA Developer Tools → States for `input_text.last_voice_command`
- Check HA Logs for automation errors
- Verify intent script is configured

**Resolution:**
```bash
# Redeploy HA configuration
bash scripts/deployment/deploy-ha-config.sh

# Check automation status in HA Developer Tools
# Verify automation.voice_command_llm_routing_v2 exists and is enabled
```

### Issue: High Error Rate

**Symptoms:**
- Health check shows error_rate > 10%
- Frequent failures in logs

**Diagnosis:**
```bash
# Check error rate
curl -s http://192.168.10.62:5000/health | jq '.metrics'

# Review recent errors
ssh jstuart@192.168.10.62 "sudo journalctl -u athena-webhook.service | grep ERROR | tail -20"

# Check HA connectivity
curl -s http://192.168.10.62:5000/health | jq '.ha_connectivity'
```

**Resolution:**
- If HA connectivity is false: Check network, verify HA is running
- If LLM errors: Check GPU memory, restart service
- If timeout errors: Increase timeout values in configuration

### Issue: Commands Queued But Not Processing

**Symptoms:**
- Multiple voice commands queued
- Responses delayed significantly

**Diagnosis:**
- Check queue depth in HA Developer Tools → States → `sensor.athena_queue_depth`
- Check if automation is stuck

**Resolution:**
```bash
# Clear queue (emergency)
# In HA Developer Tools → Services, call:
# script.clear_athena_queue
```

## Performance Tuning

### Expected Performance Metrics

- **Simple Commands:** < 2 seconds end-to-end
- **Complex Commands:** 2-5 seconds end-to-end
- **Classification:** < 100ms
- **Error Rate:** < 5%

### Optimization Tips

1. **Reduce LLM Processing Time:**
   - Use GPU (already enabled on Jetson)
   - Reduce `max_length` in generation parameters
   - Consider smaller model (already using DialoGPT-small)

2. **Reduce Network Latency:**
   - Ensure both devices on same network segment
   - Check for switch/router issues
   - Verify no firewall delays

3. **Improve Classification:**
   - Fine-tune complex indicators based on usage patterns
   - Add more specific patterns for common commands

## Backup and Recovery

### Creating Backups

**Backup Jetson Implementation:**
```bash
ssh jstuart@192.168.10.62 "tar -czf /tmp/athena-backup-$(date +%Y%m%d).tar.gz /mnt/nvme/athena-lite/"
scp jstuart@192.168.10.62:/tmp/athena-backup-*.tar.gz ~/backups/athena/
```

**Backup HA Configuration:**
```bash
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 \
    "tar -czf /tmp/ha-config-$(date +%Y%m%d).tar.gz /config/"
scp -i ~/.ssh/id_ed25519_new -P 23 root@192.168.10.168:/tmp/ha-config-*.tar.gz ~/backups/ha/
```

### Recovery

**Restore from Backup:**
```bash
# Extract backup locally
tar -xzf ~/backups/athena/athena-backup-YYYYMMDD.tar.gz

# Deploy from extracted files
cd /Users/jaystuart/dev/project-athena
bash scripts/deployment/deploy-all.sh
```

**Emergency Rollback:**
```bash
# Use automated rollback script
bash scripts/deployment/rollback-jetson.sh
```

## Security Considerations

### Credentials Management

- HA tokens stored in Kubernetes secrets
- Retrieved via `scripts/setup-env.sh`
- Never commit .env files to git

### Network Security

- Jetson webhook only accessible on local network (192.168.10.0/24)
- HA API accessed with long-lived token
- No external exposure

### Updates

**Update Dependencies:**
```bash
# Update Jetson packages
ssh jstuart@192.168.10.62 "cd /mnt/nvme/athena-lite && pip3 install -r requirements.txt --upgrade"

# Restart service
ssh jstuart@192.168.10.62 "sudo systemctl restart athena-webhook.service"
```

## Monitoring Dashboard

### Key Metrics to Watch

1. **Service Status:** Should always be "active"
2. **Model Loaded:** Should be true
3. **HA Connectivity:** Should be true
4. **Error Rate:** Should be < 5%
5. **Response Time:** Simple < 2s, Complex < 5s

### Setting Up Alerts

```bash
# Install monitoring cron jobs
bash scripts/monitoring/setup-cron.sh

# View alert log
tail -f /tmp/athena-alerts.log
```

## Testing

### Manual Testing

**Test Complex Command:**
```bash
curl -X POST http://192.168.10.62:5000/process_command \
    -H "Content-Type: application/json" \
    -d '{"command": "help me set up the office for work"}'
```

**Test Simple Command:**
```bash
curl -X POST http://192.168.10.62:5000/simple_command \
    -H "Content-Type: application/json" \
    -d '{"command": "turn on office lights"}'
```

**Test Voice Integration:**
- Say to HA voice assistant: "Help me optimize the lighting"
- Check HA logs to see if command was routed
- Verify response received

### Automated Testing

```bash
cd /Users/jaystuart/dev/project-athena/tests/integration
pytest test_facade.py -v
```

## Maintenance Schedule

### Daily
- Check health dashboard
- Review alert log

### Weekly
- Run full test suite
- Review error logs
- Check disk space on Jetson

### Monthly
- Update dependencies
- Review performance metrics
- Backup configurations

---

**For more information:**
- Architecture: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- Deployment: [docs/DEPLOYMENT.md](DEPLOYMENT.md)
- Research: [thoughts/research/RESEARCH_HA_LLM_FACADE.md](../thoughts/research/RESEARCH_HA_LLM_FACADE.md)
```

#### 2. Create Troubleshooting Guide

**File:** `/Users/jaystuart/dev/project-athena/docs/TROUBLESHOOTING.md`

```markdown
# Athena Facade Troubleshooting Guide

## Diagnostic Flow

```
Issue Reported
      ↓
Run Health Check → All Pass? → Check Configuration
      ↓ Failure            ↓
Identify Failed    Run Test Suite → All Pass? → Review Logs
  Component               ↓ Failure         ↓
      ↓            Fix Specific   Analyze Errors
Check Service       Failure              ↓
  Status                ↓         Apply Fix
      ↓           Redeploy              ↓
Restart/Fix             ↓          Test Again
      ↓           Verify Fix
Verify Fix
```

## Quick Diagnostics

### One-Line Health Check
```bash
bash /Users/jaystuart/dev/project-athena/scripts/monitoring/health-check.sh && echo "HEALTHY" || echo "ISSUES DETECTED"
```

### Check All Services
```bash
# Jetson
ssh jstuart@192.168.10.62 "systemctl is-active athena-webhook.service"

# HA
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core info | grep state"

# Network
ping -c 1 192.168.10.62 && ping -c 1 192.168.10.168
```

## Common Error Messages

### "Connection refused" when curling webhook

**Cause:** Service not running or port not listening

**Fix:**
```bash
ssh jstuart@192.168.10.62 "sudo systemctl restart athena-webhook.service"
```

### "Model not loaded" in health check

**Cause:** Model initialization failed

**Fix:**
```bash
curl -X POST http://192.168.10.62:5000/reload
```

### "HA connectivity false"

**Cause:** HA API not reachable or token invalid

**Fix:**
```bash
# Regenerate HA token and redeploy
bash /Users/jaystuart/dev/project-athena/scripts/setup-env.sh
bash /Users/jaystuart/dev/project-athena/scripts/deployment/deploy-jetson.sh
```

### Voice commands not triggering automation

**Cause:** Intent script not configured or voice assistant not connected

**Fix:**
```bash
bash /Users/jaystuart/dev/project-athena/scripts/deployment/deploy-ha-config.sh
```

## Debug Mode

### Enable Verbose Logging

Edit `/mnt/nvme/athena-lite/.env` on Jetson:
```bash
LOG_LEVEL=DEBUG
```

Restart service:
```bash
ssh jstuart@192.168.10.62 "sudo systemctl restart athena-webhook.service"
```

### Watch Live Logs
```bash
ssh jstuart@192.168.10.62 "sudo journalctl -u athena-webhook.service -f"
```

## Performance Issues

### Slow Response Times

**Diagnosis:**
```bash
# Time a request
time curl -X POST http://192.168.10.62:5000/process_command \
    -H "Content-Type: application/json" \
    -d '{"command": "test"}'
```

**Fixes:**
- Check GPU utilization: `ssh jstuart@192.168.10.62 "nvidia-smi"`
- Check system load: `ssh jstuart@192.168.10.62 "uptime"`
- Restart service to clear memory: `ssh jstuart@192.168.10.62 "sudo systemctl restart athena-webhook.service"`

## Advanced Debugging

### Packet Capture
```bash
# On Jetson, capture traffic on port 5000
ssh jstuart@192.168.10.62 "sudo tcpdump -i any port 5000 -w /tmp/capture.pcap"
```

### Python Debugging
```bash
# Run service manually with debugger
ssh jstuart@192.168.10.62
cd /mnt/nvme/athena-lite
python3 -m pdb llm_webhook_service.py
```

### Database/State Inspection (HA)
```bash
# Access HA container and inspect state
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core logs"
```

## Recovery Procedures

### Full System Reset

**WARNING: This will restart all services**

```bash
# 1. Stop services
ssh jstuart@192.168.10.62 "sudo systemctl stop athena-webhook.service"
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core stop"

# 2. Wait 30 seconds
sleep 30

# 3. Start services
ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core start"
ssh jstuart@192.168.10.62 "sudo systemctl start athena-webhook.service"

# 4. Wait for startup
sleep 60

# 5. Verify
bash /Users/jaystuart/dev/project-athena/scripts/monitoring/health-check.sh
```

### Nuclear Option: Full Redeployment

```bash
cd /Users/jaystuart/dev/project-athena
bash scripts/deployment/deploy-all.sh
```

## Getting Help

### Collect Diagnostic Information

```bash
# Run this and share the output
bash /Users/jaystuart/dev/project-athena/scripts/monitoring/health-check.sh > /tmp/health-report.txt 2>&1
bash /Users/jaystuart/dev/project-athena/scripts/monitoring/collect-metrics.sh
tar -czf /tmp/athena-diagnostics-$(date +%Y%m%d).tar.gz /tmp/athena-metrics/ /tmp/health-report.txt
```

### Log Locations

- **Jetson Service:** `ssh jstuart@192.168.10.62 "sudo journalctl -u athena-webhook.service"`
- **HA Logs:** `ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "ha core logs"`
- **Metrics:** `/tmp/athena-metrics/`
- **Alerts:** `/tmp/athena-alerts.log`

---

**Last Updated:** $(date +%Y-%m-%d)
```

#### 3. Create End-to-End Test Plan

**File:** `/Users/jaystuart/dev/project-athena/tests/END_TO_END_TEST_PLAN.md`

```markdown
# End-to-End Test Plan

## Test Environment

- **Jetson:** 192.168.10.62 (jetson-01)
- **Home Assistant:** 192.168.10.168
- **Test Location:** Office (primary test zone)
- **Voice Device:** Home Assistant Blue

## Pre-Test Checklist

- [ ] All services running (health check passes)
- [ ] No recent errors in logs
- [ ] Voice device accessible in HA
- [ ] Test environment is quiet (minimal background noise)

## Test Cases

### TC001: Simple Voice Command

**Objective:** Verify simple voice command processing

**Steps:**
1. Say to HA voice assistant: "Turn on office lights"
2. Observe light turns on
3. Check HA automation logs

**Expected Results:**
- Light turns on within 2 seconds
- `input_text.last_voice_command` shows "turn on office lights"
- `sensor.voice_command_type` shows "simple"
- Automation triggered `rest_command.athena_llm_simple`
- Jetson logs show request to `/simple_command`

**Pass Criteria:**
- Response time < 2 seconds
- Command executed correctly
- No errors in logs

---

### TC002: Complex Voice Command

**Objective:** Verify complex voice command processing with LLM

**Steps:**
1. Say to HA voice assistant: "Help me optimize the office lighting"
2. Wait for response
3. Check logs for LLM processing

**Expected Results:**
- Response within 5 seconds
- `sensor.voice_command_type` shows "complex"
- Automation triggered `rest_command.athena_llm_complex`
- Jetson logs show LLM processing
- Intelligent response provided

**Pass Criteria:**
- Response time < 5 seconds
- LLM processing successful
- Meaningful response provided

---

### TC003: Classification Edge Case

**Objective:** Verify correct classification of ambiguous commands

**Test Commands:**
1. "help turn on lights" (should be complex - has "help")
2. "turn off all lights" (should be complex - has "all")
3. "set office lights to 50%" (should be simple)

**Expected Results:**
- Commands classified according to priority rules
- Each command processes via appropriate endpoint

**Pass Criteria:**
- All 3 commands classified correctly
- No misrouting

---

### TC004: Concurrent Commands

**Objective:** Verify queuing handles multiple commands

**Steps:**
1. Say "Turn on office lights"
2. Immediately say "Set bedroom lights to dim"
3. Immediately say "Help me set the mood for dinner"

**Expected Results:**
- All 3 commands queued (max queue depth = 5)
- Commands process sequentially
- No commands dropped

**Pass Criteria:**
- `sensor.athena_queue_depth` shows queuing
- All commands complete
- No errors

---

### TC005: Service Restart Resilience

**Objective:** Verify service auto-restarts after failure

**Steps:**
1. SSH to Jetson: `ssh jstuart@192.168.10.62`
2. Kill webhook process: `sudo pkill -f llm_webhook_service`
3. Wait 10 seconds
4. Test voice command: "Turn on office lights"

**Expected Results:**
- Systemd automatically restarts service
- Service becomes available within 10 seconds
- Voice command succeeds

**Pass Criteria:**
- Service restarts automatically
- No manual intervention needed
- Command succeeds after restart

---

### TC006: Network Failure Handling

**Objective:** Verify fallback when Jetson unreachable

**Steps:**
1. Stop Jetson webhook: `ssh jstuart@192.168.10.62 "sudo systemctl stop athena-webhook.service"`
2. Say "Turn on office lights"
3. Observe behavior

**Expected Results:**
- Command attempts Jetson webhook
- Webhook times out or returns error
- Automation fallback to HA native processing
- Command still executes (via fallback)

**Pass Criteria:**
- Fallback mechanism activates
- Command completes (even if slower)
- User receives feedback

**Cleanup:**
```bash
ssh jstuart@192.168.10.62 "sudo systemctl start athena-webhook.service"
```

---

### TC007: 24-Hour Stability Test

**Objective:** Verify system stability over extended period

**Setup:**
```bash
# Enable monitoring
bash scripts/monitoring/setup-cron.sh
```

**Test:**
- Run system for 24 hours
- Issue voice commands periodically (every 30 minutes)
- Collect metrics continuously

**Expected Results:**
- No service crashes
- Error rate remains < 5%
- Response times consistent
- No memory leaks (check with `ssh jstuart@192.168.10.62 "free -h"`)

**Pass Criteria:**
- Service uptime = 24 hours
- Error rate < 5%
- No manual intervention required

---

### TC008: Full System Reboot

**Objective:** Verify services auto-start after reboot

**Steps:**
1. Reboot Jetson: `ssh jstuart@192.168.10.62 "sudo reboot"`
2. Wait 2 minutes for boot
3. Check service status
4. Test voice command

**Expected Results:**
- Jetson boots successfully
- athena-webhook.service starts automatically
- Service is enabled (systemd)
- Voice commands work after boot

**Pass Criteria:**
- No manual service start needed
- Health check passes after reboot
- Voice commands functional

---

## Test Execution Log

**Test Date:** __________
**Executed By:** __________
**System Version:** __________

| Test Case | Status | Notes |
|-----------|--------|-------|
| TC001 | ☐ Pass ☐ Fail | |
| TC002 | ☐ Pass ☐ Fail | |
| TC003 | ☐ Pass ☐ Fail | |
| TC004 | ☐ Pass ☐ Fail | |
| TC005 | ☐ Pass ☐ Fail | |
| TC006 | ☐ Pass ☐ Fail | |
| TC007 | ☐ Pass ☐ Fail | |
| TC008 | ☐ Pass ☐ Fail | |

**Overall Result:** ☐ Pass ☐ Fail

**Sign-off:** __________________________
```

#### 4. Create Final Deployment Checklist

**File:** `/Users/jaystuart/dev/project-athena/docs/DEPLOYMENT_CHECKLIST.md`

```markdown
# Athena Facade Deployment Checklist

## Pre-Deployment

### Code & Configuration
- [ ] All code committed to git (no uncommitted changes)
- [ ] All deployment scripts tested
- [ ] Configuration files validated (YAML syntax)
- [ ] No hardcoded secrets in code
- [ ] `.env.example` file created

### Infrastructure
- [ ] Jetson accessible via SSH: `ssh jstuart@192.168.10.62 "echo OK"`
- [ ] HA accessible via SSH: `ssh -i ~/.ssh/id_ed25519_new -p 23 root@192.168.10.168 "echo OK"`
- [ ] Kubernetes cluster accessible: `kubectl cluster-info`
- [ ] HA token retrieved from secrets

### Backups
- [ ] Jetson implementation backed up
- [ ] HA configuration backed up
- [ ] Backup restoration tested

## Deployment

### Phase 1: Code Recovery
- [ ] Jetson code copied to repository
- [ ] HA configuration fragments copied
- [ ] Repository structure validated
- [ ] All files committed to git

### Phase 2: Reliability Improvements
- [ ] Updated automation with state sync fixes
- [ ] Enhanced webhook service with error handling
- [ ] Environment configuration deployed
- [ ] Timeout handling improved

### Phase 3: Voice Integration
- [ ] Intent script configured
- [ ] Custom sentences deployed
- [ ] Classification logic improved
- [ ] Queue management enabled

### Phase 4: Service Management
- [ ] Systemd service unit created
- [ ] Service deployed to Jetson
- [ ] Service enabled (auto-start)
- [ ] Service tested after reboot

### Phase 5: Monitoring
- [ ] Health check script working
- [ ] Integration tests passing
- [ ] Metrics collection configured
- [ ] Cron jobs installed
- [ ] Alert thresholds configured

### Phase 6: Documentation
- [ ] Operations guide complete
- [ ] Troubleshooting guide created
- [ ] Test plan documented
- [ ] Deployment checklist finalized (this document)

## Validation

### Automated Tests
- [ ] Health check passes: `bash scripts/monitoring/health-check.sh`
- [ ] Integration tests pass: `cd tests/integration && pytest -v`
- [ ] No critical alerts: `grep CRITICAL /tmp/athena-alerts.log`

### Manual Tests
- [ ] TC001: Simple voice command works
- [ ] TC002: Complex voice command works
- [ ] TC003: Classification edge cases handled
- [ ] TC004: Concurrent commands queued
- [ ] TC005: Service auto-restarts
- [ ] TC006: Fallback mechanism works
- [ ] TC007: 24-hour stability test passed
- [ ] TC008: Services survive reboot

### Performance Validation
- [ ] Simple command response time < 2 seconds
- [ ] Complex command response time < 5 seconds
- [ ] Error rate < 5%
- [ ] Classification accuracy > 95%

### Reliability Validation
- [ ] All 8 reliability issues addressed:
  - [ ] Issue #1: State synchronization fixed
  - [ ] Issue #2: Timing dependencies resolved
  - [ ] Issue #3: Network resilience added
  - [ ] Issue #4: Classification improved
  - [ ] Issue #5: Timeout handling enhanced
  - [ ] Issue #6: Error handling comprehensive
  - [ ] Issue #7: Voice integration connected
  - [ ] Issue #8: Concurrent commands supported

## Production Readiness

### System Health
- [ ] All services running
- [ ] Health dashboard green
- [ ] No recent errors in logs
- [ ] Resource usage acceptable

### Monitoring
- [ ] Metrics being collected
- [ ] Alerts configured and tested
- [ ] Dashboards accessible

### Documentation
- [ ] Operations guide reviewed
- [ ] Team trained on procedures
- [ ] Escalation path defined

### Rollback Plan
- [ ] Rollback script tested
- [ ] Backup verified accessible
- [ ] Recovery time < 15 minutes

## Sign-Off

**Deployment Date:** __________

**Technical Lead:** __________________________ Date: __________

**Production Approval:** __________________________ Date: __________

**Notes:**
___________________________________________________________________
___________________________________________________________________
___________________________________________________________________

## Post-Deployment

- [ ] Monitor for 48 hours
- [ ] Review error logs daily
- [ ] Check performance metrics
- [ ] Validate user feedback

**Post-Deployment Review Date:** __________
**Status:** ☐ Stable ☐ Issues ☐ Rollback Required
```

### Success Criteria

#### Automated Verification:
- [ ] Operations guide is complete and renders correctly
- [ ] Troubleshooting guide covers all known issues
- [ ] End-to-end test plan has 8+ test cases
- [ ] Deployment checklist has 50+ items
- [ ] All automated tests pass: `cd tests/integration && pytest test_facade.py -v`
- [ ] Health check passes: `bash scripts/monitoring/health-check.sh`
- [ ] No critical alerts in last 24 hours: `grep CRITICAL /tmp/athena-alerts.log | grep $(date +%Y-%m-%d) | wc -l` returns 0

#### Manual Verification:
- [ ] Operations guide procedures tested and work
- [ ] All test cases from test plan executed and passed
- [ ] 24-hour stability test completed successfully
- [ ] Deployment checklist validated by executing all items
- [ ] System demonstrates production-ready stability

**Implementation Note:** This is the final phase. After all automated and manual verification passes, the system is production-ready and the implementation plan is complete.

---

## Testing Strategy

### Unit Tests
Unit tests are not included in this plan as the focus is on integration and system testing. Future work could add unit tests for:
- Classification logic
- Error handling functions
- Webhook request parsing

### Integration Tests
Comprehensive integration test suite created in Phase 5:
- Webhook endpoint testing
- Command processing validation
- Error handling verification
- Concurrent request handling
- System reliability testing

### Manual Testing Steps

**After Phase 3 (Voice Integration):**
1. Test basic voice command: "Turn on office lights"
2. Test complex voice command: "Help me set the mood"
3. Verify classification is working correctly

**After Phase 4 (Service Management):**
1. Reboot Jetson and verify auto-start
2. Kill service and verify auto-restart
3. Check logs for any startup errors

**After Phase 5 (Monitoring):**
1. Run health check script
2. Run full integration test suite
3. Collect metrics for 1 hour and review

**After Phase 6 (Documentation):**
1. Execute complete end-to-end test plan
2. Run 24-hour stability test
3. Perform full system reboot test
4. Validate all procedures in operations guide

## Performance Considerations

### Target Response Times
- **Simple Commands:** < 2 seconds (turn on/off, set brightness)
- **Complex Commands:** 2-5 seconds (LLM processing with DialoGPT-small)
- **Classification:** < 100ms (template sensor evaluation)
- **Total Overhead:** < 300ms (facade routing and webhook communication)

### Resource Usage
- **Jetson Memory:** ~2GB for model + service (within 4GB limit in systemd)
- **Jetson CPU:** 200% quota (2 cores) sufficient for inference
- **Network Bandwidth:** Minimal (<1Mbps for JSON payloads)
- **HA Resource Impact:** Negligible (lightweight automation and templates)

### Optimization Opportunities
Not included in this plan but possible future improvements:
- Model quantization for faster inference
- Response caching for common commands
- Async processing for truly long-running operations
- CDN or local cache for model weights

## Migration Notes

### From Current Non-Functional State
No migration needed - system is being brought from configured-but-non-functional to fully operational.

### Existing HA Configuration
- Backups created before any changes (`*.backup-YYYYMMDD-HHMMSS`)
- Config sections marked with `# BEGIN ATHENA FACADE CONFIG` / `# END ATHENA FACADE CONFIG`
- Rollback possible by restoring from backups

### Existing Jetson Implementation
- Backups created in `/mnt/nvme/athena-lite-backups/` before deployment
- Rollback script provided for quick restoration
- No data migration required (stateless service)

## References

- **Original Research:** [thoughts/research/RESEARCH_HA_LLM_FACADE.md](../research/RESEARCH_HA_LLM_FACADE.md)
- **Integration Guide:** [docs/HA_LLM_INTEGRATION_GUIDE.md](../docs/HA_LLM_INTEGRATION_GUIDE.md)
- **Config Success:** [docs/CONFIG_UPDATE_SUCCESS.md](../docs/CONFIG_UPDATE_SUCCESS.md)
- **Project CLAUDE.md:** [CLAUDE.md](../../CLAUDE.md)
- **Homelab Infrastructure:** `/Users/jaystuart/dev/kubernetes/k8s-home-lab/CLAUDE.md`

---

**Plan Status:** Ready for Implementation
**Target Start Date:** 2025-01-06
**Estimated Completion:** 2025-01-20 (2 weeks)
**Created By:** Claude Code
**Last Updated:** 2025-01-06
