# LLM Backend System - Configuration Guide

> **Last Updated:** November 15, 2025
> **Status:** Production Ready
> **Audience:** Developers and System Administrators

## Overview

This guide provides step-by-step instructions for configuring the LLM Backend System. You'll learn how to set up Ollama, MLX, and Auto backends, create configurations via the Admin API, and verify everything is working correctly.

**Quick Links:**
- [Overview](./llm-backend-overview) - System overview
- [Admin API Reference](./llm-backend-admin-api) - Full API documentation
- [Router Technical Docs](./llm-backend-router) - Router internals

## Prerequisites

Before configuring backends, ensure you have:

- ✅ Admin API running (`http://localhost:8080`)
- ✅ PostgreSQL database with `llm_backends` table
- ✅ API authentication token
- ✅ At least one LLM backend (Ollama or MLX) running

## Get API Token

All configuration operations require authentication.

```bash
# Retrieve API token from Kubernetes
kubectl -n automation get secret admin-api-credentials -o jsonpath='{.data.api-token}' | base64 -d

# Export for convenience
export TOKEN=$(kubectl -n automation get secret admin-api-credentials -o jsonpath='{.data.api-token}' | base64 -d)

# Verify token works
curl -X GET http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
[]  # Empty array if no backends configured yet
```

## Configuration Scenarios

### Scenario 1: Configure Ollama Backend (Default)

**Use Case:** Running Ollama locally for development or testing.

**Step 1: Verify Ollama is Running**

```bash
# Check Ollama server status
curl http://localhost:11434/api/tags

# Expected: List of available models
```

**Step 2: Ensure Model is Downloaded**

```bash
# Pull phi3:mini model (if not already pulled)
ollama pull phi3:mini

# Verify model exists
ollama list | grep phi3:mini
```

**Step 3: Create Backend Configuration**

```bash
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "ollama",
    "endpoint_url": "http://localhost:11434",
    "enabled": true,
    "max_tokens": 2048,
    "temperature_default": 0.7,
    "timeout_seconds": 60,
    "description": "Phi-3 Mini via Ollama for fast classification"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "model_name": "phi3:mini",
  "backend_type": "ollama",
  "endpoint_url": "http://localhost:11434",
  "enabled": true,
  "max_tokens": 2048,
  "temperature_default": 0.7,
  "timeout_seconds": 60,
  "description": "Phi-3 Mini via Ollama for fast classification",
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-15T10:00:00Z"
}
```

**Step 4: Verify Configuration**

```bash
# Service-to-service endpoint (no auth required)
curl http://localhost:8080/api/llm-backends/model/phi3:mini | jq

# Expected: Same configuration as above
```

**Step 5: Test Generation**

```python
from shared.llm_router import get_llm_router
import asyncio

async def test():
    router = get_llm_router()
    result = await router.generate(
        model="phi3:mini",
        prompt="What is 2+2?",
        temperature=0.7
    )
    print(f"Response: {result['response']}")
    print(f"Backend: {result['backend']}")

asyncio.run(test())
```

**Expected Output:**
```
Response: 2 + 2 equals 4.
Backend: ollama
```

---

### Scenario 2: Configure MLX Backend (Apple Silicon)

**Use Case:** Running on Mac Studio M4 or other Apple Silicon for 2-3x faster inference.

**Step 1: Install MLX**

```bash
# Install mlx-lm package
pip install mlx-lm

# Verify installation
python3 -c "import mlx; print(mlx.__version__)"
```

**Step 2: Convert Model to MLX Format**

```bash
# Convert Hugging Face model to MLX format
mlx_lm.convert \
  --hf-path microsoft/Phi-3-mini-4k-instruct \
  --mlx-path ~/models/mlx/phi3-mini

# Verify conversion
ls -lh ~/models/mlx/phi3-mini/
# Expected: config.json, weights.npz, tokenizer.model
```

**Step 3: Start MLX Server**

```bash
# Start MLX server on port 8080
mlx_lm.server \
  --model ~/models/mlx/phi3-mini \
  --port 8080 \
  --host 0.0.0.0

# Verify server is running
curl http://localhost:8080/v1/models
```

**Step 4: Create MLX Backend Configuration**

```bash
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "mlx",
    "endpoint_url": "http://localhost:8080",
    "enabled": true,
    "max_tokens": 2048,
    "temperature_default": 0.7,
    "timeout_seconds": 60,
    "description": "Phi-3 Mini via MLX (2.3x faster on Apple Silicon)"
  }'
```

**Step 5: Test MLX Generation**

```python
from shared.llm_router import get_llm_router
import asyncio

async def test_mlx():
    router = get_llm_router()
    result = await router.generate(
        model="phi3:mini",
        prompt="Explain quantum computing in one sentence.",
        temperature=0.7
    )
    print(f"Response: {result['response']}")
    print(f"Backend: {result['backend']}")  # Should be "mlx"

asyncio.run(test_mlx())
```

---

### Scenario 3: Configure Auto Backend (Hybrid Fallback)

**Use Case:** Production environment where you want MLX speed with Ollama reliability.

**Step 1: Ensure Both Backends Running**

```bash
# Verify Ollama (port 11434)
curl http://localhost:11434/api/tags

# Verify MLX (port 8080)
curl http://localhost:8080/v1/models
```

**Step 2: Create Auto Configuration**

```bash
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "llama3.1:8b",
    "backend_type": "auto",
    "endpoint_url": "http://localhost:8080",
    "enabled": true,
    "max_tokens": 4096,
    "temperature_default": 0.7,
    "timeout_seconds": 120,
    "description": "Llama 3.1 8B with auto fallback (MLX → Ollama)"
  }'
```

**Behavior:**
1. LLMRouter tries MLX first at `http://localhost:8080/v1/completions`
2. If MLX fails (timeout, error, unavailable):
   - Automatically falls back to Ollama at `http://localhost:11434/api/generate`
3. Returns result from whichever backend succeeded

**Step 3: Test Fallback Behavior**

```bash
# Test 1: Both backends up (should use MLX)
curl http://localhost:8080/api/llm-backends/model/llama3.1:8b | jq '.backend_type'
# Output: "auto"

# Test 2: Simulate MLX down
# Stop MLX server, verify router falls back to Ollama
```

---

### Scenario 4: Multiple Models with Different Backends

**Use Case:** Optimize each model for its use case.

**Configuration Strategy:**
- **phi3:mini** → MLX (fast classification, 2-3s response)
- **llama3.1:8b** → Ollama (better quality, acceptable latency)
- **codellama:7b** → Auto (try MLX, fall back to Ollama)

**Create All Configurations:**

```bash
# 1. phi3:mini on MLX
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "mlx",
    "endpoint_url": "http://localhost:8080",
    "enabled": true,
    "max_tokens": 2048,
    "temperature_default": 0.3,
    "timeout_seconds": 30,
    "description": "Fast intent classification"
  }'

# 2. llama3.1:8b on Ollama
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "llama3.1:8b",
    "backend_type": "ollama",
    "endpoint_url": "http://localhost:11434",
    "enabled": true,
    "max_tokens": 4096,
    "temperature_default": 0.7,
    "timeout_seconds": 120,
    "description": "High-quality response synthesis"
  }'

# 3. codellama:7b with auto fallback
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "codellama:7b",
    "backend_type": "auto",
    "endpoint_url": "http://localhost:8080",
    "enabled": true,
    "max_tokens": 4096,
    "temperature_default": 0.2,
    "timeout_seconds": 120,
    "description": "Code generation with hybrid backend"
  }'
```

**Verify All Configurations:**

```bash
curl -X GET http://localhost:8080/api/llm-backends?enabled_only=true \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Common Configuration Operations

### Switch Backend for Existing Model

**Scenario:** Switch `phi3:mini` from Ollama to MLX for better performance.

```bash
# 1. Find backend ID
curl -X GET http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | select(.model_name == "phi3:mini")'

# Output: {"id": 1, "model_name": "phi3:mini", ...}

# 2. Update to MLX
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "backend_type": "mlx",
    "endpoint_url": "http://localhost:8080"
  }'

# 3. Verify change
curl http://localhost:8080/api/llm-backends/model/phi3:mini | jq '.backend_type'
# Output: "mlx"
```

**No service restart required!** LLMRouter cache expires within 60 seconds.

---

### Temporarily Disable a Backend

```bash
# Option 1: Toggle enabled status
curl -X POST http://localhost:8080/api/llm-backends/1/toggle \
  -H "Authorization: Bearer $TOKEN"

# Option 2: Update enabled field
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

**Effect:** LLMRouter will fall back to default Ollama configuration.

---

### Delete Backend Configuration

```bash
curl -X DELETE http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN"
```

**Effect:** Model will use default Ollama configuration until new config created.

---

## Configuration Best Practices

### 1. Start with Ollama (Simplicity)

**Recommendation:** Configure Ollama first for all models.

**Rationale:**
- Easy setup (no model conversion)
- Broad model support
- Reliable fallback option

**Example:**
```bash
# Configure all models with Ollama initially
for model in phi3:mini llama3.1:8b codellama:7b; do
  curl -X POST http://localhost:8080/api/llm-backends \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"model_name\": \"$model\",
      \"backend_type\": \"ollama\",
      \"endpoint_url\": \"http://localhost:11434\",
      \"enabled\": true
    }"
done
```

### 2. Switch to MLX for Speed (Optimization)

**Recommendation:** After verifying Ollama works, switch critical models to MLX.

**Critical Models:**
- Intent classification (phi3:mini) → MLX
- Real-time queries → MLX

**Example:**
```bash
# Switch phi3:mini to MLX
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backend_type": "mlx", "endpoint_url": "http://localhost:8080"}'
```

### 3. Use Auto for Resilience

**Recommendation:** Production models should use `auto` backend type.

**Rationale:**
- Try fast backend (MLX) first
- Automatic fallback to reliable backend (Ollama)
- No manual intervention needed

**Example:**
```bash
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backend_type": "auto"}'
```

### 4. Set Appropriate Timeouts

**Recommendations:**

| Model Size | Timeout | Rationale |
|------------|---------|-----------|
| Small (phi3:mini) | 30-60s | Fast generation, shouldn't take long |
| Medium (llama3.1:8b) | 60-120s | Larger model, more complex reasoning |
| Large (70B+) | 120-300s | Very large models need time |

**Example:**
```bash
# Small model: 30s timeout
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"timeout_seconds": 30}'
```

### 5. Document Configurations

**Recommendation:** Add meaningful descriptions to all backends.

**Example:**
```bash
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Phi-3 Mini on MLX (2.3x faster). Used for intent classification in orchestrator. Avg latency: 2.8s"
  }'
```

---

## Troubleshooting

### Issue 1: Configuration Not Taking Effect

**Symptom:** Updated backend config, but router still using old backend.

**Cause:** Configuration cache (60-second TTL).

**Solution:** Wait 60 seconds or restart orchestrator.

```bash
# Check cache expiry
# Config changes take effect within 60 seconds

# Force immediate refresh: restart service
kubectl -n athena rollout restart deployment/athena-orchestration
```

---

### Issue 2: MLX Backend Not Found

**Symptom:** Error: "Connection refused" when using MLX backend.

**Cause:** MLX server not running or wrong port.

**Solution:**
```bash
# Check MLX server status
curl http://localhost:8080/v1/models

# If not running, start it
mlx_lm.server --model ~/models/mlx/phi3-mini --port 8080

# Verify correct endpoint in config
curl http://localhost:8080/api/llm-backends/model/phi3:mini | jq '.endpoint_url'
```

---

### Issue 3: Fallback Not Working (Auto Mode)

**Symptom:** Auto mode fails instead of falling back to Ollama.

**Cause:** Ollama backend not running or not accessible.

**Solution:**
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Check router logs for fallback attempt
kubectl -n athena logs deployment/athena-orchestration | grep "mlx_failed_falling_back"
```

---

### Issue 4: Model Not Found in Ollama

**Symptom:** Error: "model 'phi3:mini' not found"

**Cause:** Model not pulled in Ollama.

**Solution:**
```bash
# Pull model
ollama pull phi3:mini

# Verify model exists
ollama list | grep phi3:mini
```

---

### Issue 5: Backend Disabled

**Symptom:** Router using default Ollama config instead of configured backend.

**Cause:** Backend `enabled: false`.

**Solution:**
```bash
# Check if backend is enabled
curl http://localhost:8080/api/llm-backends/model/phi3:mini | jq '.enabled'

# Enable backend
curl -X POST http://localhost:8080/api/llm-backends/1/toggle \
  -H "Authorization: Bearer $TOKEN"
```

---

## Verification Checklist

After configuration, verify everything works:

**1. Backend Configuration Exists:**
```bash
curl http://localhost:8080/api/llm-backends/model/phi3:mini | jq
# Should return config, not 404
```

**2. Backend Server is Accessible:**
```bash
# Ollama
curl http://localhost:11434/api/tags

# MLX
curl http://localhost:8080/v1/models
```

**3. Model is Available:**
```bash
# Ollama
ollama list | grep phi3:mini

# MLX
ls ~/models/mlx/phi3-mini/
```

**4. Router Can Generate:**
```python
from shared.llm_router import get_llm_router
import asyncio

async def verify():
    router = get_llm_router()
    result = await router.generate(
        model="phi3:mini",
        prompt="Test prompt",
        temperature=0.7
    )
    print(f"✓ Generation successful: {result['backend']}")

asyncio.run(verify())
```

**5. Check Logs:**
```bash
kubectl -n athena logs deployment/athena-orchestration --tail=50 | grep "routing_llm_request"
```

---

## Environment-Specific Configurations

### Development (Local Laptop)

```bash
# Use Ollama only (simple setup)
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "ollama",
    "endpoint_url": "http://localhost:11434",
    "enabled": true
  }'
```

### Staging (Mac Studio)

```bash
# Use MLX for performance testing
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "mlx",
    "endpoint_url": "http://192.168.10.167:8080",
    "enabled": true
  }'
```

### Production (Kubernetes Cluster)

```bash
# Use Auto for resilience
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "auto",
    "endpoint_url": "http://mlx-service.athena.svc.cluster.local:8080",
    "enabled": true
  }'
```

---

## Next Steps

- **[Deployment Guide](./llm-backend-deployment)** - Deploy to production
- **[Admin API Reference](./llm-backend-admin-api)** - Full API docs
- **[Router Technical Docs](./llm-backend-router)** - Understanding routing
- **[Overview](./llm-backend-overview)** - Back to system overview

---

**Last Updated:** November 15, 2025
**Maintained By:** Jay Stuart
