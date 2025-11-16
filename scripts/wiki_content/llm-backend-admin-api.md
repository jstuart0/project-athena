# LLM Backend System - Admin API Reference

> **Last Updated:** November 15, 2025
> **Status:** Production Ready
> **Base URL:** `http://localhost:8080/api/llm-backends`

## Overview

The Admin API provides comprehensive management of LLM backend configurations. All endpoints use REST principles with JSON payloads and support standard CRUD operations.

**Authentication:** Most endpoints require a valid Bearer token with appropriate permissions. The service-to-service lookup endpoint (`GET /model/{model_name}`) does not require authentication.

**Quick Links:**
- [Overview](./llm-backend-overview) - System overview
- [Router Technical Docs](./llm-backend-router) - Router internals
- [Configuration Guide](./llm-backend-config) - Setup instructions

## Base Configuration

**Admin API URL:** `http://localhost:8080`
**API Prefix:** `/api/llm-backends`
**Content-Type:** `application/json`
**Authentication:** `Authorization: Bearer {token}`

## Data Models

### LLMBackend Schema

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
  "avg_tokens_per_sec": 14.2,
  "avg_latency_ms": 4850.0,
  "total_requests": 142,
  "total_errors": 3,
  "priority": 1,
  "description": "Phi-3 Mini via Ollama for fast classification",
  "created_at": "2025-11-15T10:30:00Z",
  "updated_at": "2025-11-15T14:25:00Z"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | Auto | Primary key |
| `model_name` | string | Yes | Model identifier (e.g., "phi3:mini") |
| `backend_type` | string | Yes | Backend type: "ollama", "mlx", or "auto" |
| `endpoint_url` | string | Yes | Backend server URL |
| `enabled` | boolean | Yes | Whether backend is active |
| `max_tokens` | integer | No | Default max tokens for generation |
| `temperature_default` | float | No | Default temperature (0.0-1.0) |
| `timeout_seconds` | integer | No | Request timeout in seconds |
| `avg_tokens_per_sec` | float | No | Average generation speed (tracked) |
| `avg_latency_ms` | float | No | Average request latency (tracked) |
| `total_requests` | integer | No | Total successful requests |
| `total_errors` | integer | No | Total failed requests |
| `priority` | integer | No | Selection priority (if multiple configs) |
| `description` | string | No | Human-readable description |

## Endpoints

### 1. List All Backends

**GET** `/api/llm-backends`

List all backend configurations with optional filtering.

**Query Parameters:**
- `enabled_only` (boolean, optional) - Only return enabled backends

**Example Request:**
```bash
curl -X GET http://localhost:8080/api/llm-backends?enabled_only=true \
  -H "Authorization: Bearer $TOKEN"
```

**Example Response:**
```json
[
  {
    "id": 1,
    "model_name": "phi3:mini",
    "backend_type": "ollama",
    "endpoint_url": "http://localhost:11434",
    "enabled": true,
    "max_tokens": 2048,
    "temperature_default": 0.7,
    "description": "Fast classification model"
  },
  {
    "id": 2,
    "model_name": "llama3.1:8b",
    "backend_type": "mlx",
    "endpoint_url": "http://localhost:8080",
    "enabled": true,
    "max_tokens": 4096,
    "temperature_default": 0.7,
    "description": "Response synthesis model (MLX optimized)"
  }
]
```

**Status Codes:**
- `200 OK` - Backends retrieved successfully
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions

---

### 2. Get Backend by ID

**GET** `/api/llm-backends/{id}`

Retrieve a specific backend configuration by ID.

**Path Parameters:**
- `id` (integer) - Backend ID

**Example Request:**
```bash
curl -X GET http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN"
```

**Example Response:**
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
  "avg_tokens_per_sec": 14.2,
  "avg_latency_ms": 4850.0,
  "total_requests": 142,
  "total_errors": 3,
  "priority": 1,
  "description": "Phi-3 Mini via Ollama for fast classification",
  "created_at": "2025-11-15T10:30:00Z",
  "updated_at": "2025-11-15T14:25:00Z"
}
```

**Status Codes:**
- `200 OK` - Backend found
- `404 Not Found` - Backend ID does not exist
- `401 Unauthorized` - Missing or invalid token

---

### 3. Get Backend by Model Name (Service-to-Service)

**GET** `/api/llm-backends/model/{model_name}`

**⚠️ NO AUTHENTICATION REQUIRED** - Service-to-service endpoint used by LLM Router.

Retrieve the backend configuration for a specific model name. Returns only enabled backends.

**Path Parameters:**
- `model_name` (string) - Model identifier (e.g., "phi3:mini")

**Example Request:**
```bash
# No Authorization header required
curl -X GET http://localhost:8080/api/llm-backends/model/phi3:mini
```

**Example Response:**
```json
{
  "id": 1,
  "model_name": "phi3:mini",
  "backend_type": "ollama",
  "endpoint_url": "http://localhost:11434",
  "enabled": true,
  "max_tokens": 2048,
  "temperature_default": 0.7,
  "timeout_seconds": 60
}
```

**Status Codes:**
- `200 OK` - Backend configuration found
- `404 Not Found` - No enabled backend for this model

**Usage by LLM Router:**
```python
# LLMRouter automatically calls this endpoint
config = await self._get_backend_config("phi3:mini")
# Returns cached config or fetches from this endpoint
```

---

### 4. Create Backend

**POST** `/api/llm-backends`

Create a new backend configuration.

**Request Body:**
```json
{
  "model_name": "phi3:mini",
  "backend_type": "ollama",
  "endpoint_url": "http://localhost:11434",
  "enabled": true,
  "max_tokens": 2048,
  "temperature_default": 0.7,
  "timeout_seconds": 60,
  "description": "Phi-3 Mini via Ollama for fast classification"
}
```

**Required Fields:**
- `model_name`
- `backend_type` (must be "ollama", "mlx", or "auto")
- `endpoint_url`
- `enabled`

**Example Request:**
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
    "description": "Fast classification model"
  }'
```

**Example Response:**
```json
{
  "id": 3,
  "model_name": "phi3:mini",
  "backend_type": "ollama",
  "endpoint_url": "http://localhost:11434",
  "enabled": true,
  "max_tokens": 2048,
  "temperature_default": 0.7,
  "timeout_seconds": 60,
  "description": "Fast classification model",
  "created_at": "2025-11-15T15:00:00Z",
  "updated_at": "2025-11-15T15:00:00Z"
}
```

**Status Codes:**
- `201 Created` - Backend created successfully
- `400 Bad Request` - Invalid input data
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions
- `409 Conflict` - Backend for this model already exists

---

### 5. Update Backend

**PUT** `/api/llm-backends/{id}`

Update an existing backend configuration. Partial updates are supported.

**Path Parameters:**
- `id` (integer) - Backend ID to update

**Request Body (all fields optional):**
```json
{
  "backend_type": "mlx",
  "endpoint_url": "http://localhost:8080",
  "enabled": true,
  "max_tokens": 4096,
  "temperature_default": 0.5,
  "description": "Switched to MLX for 2x speedup"
}
```

**Example Request:**
```bash
# Switch from Ollama to MLX
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "backend_type": "mlx",
    "endpoint_url": "http://localhost:8080"
  }'
```

**Example Response:**
```json
{
  "id": 1,
  "model_name": "phi3:mini",
  "backend_type": "mlx",
  "endpoint_url": "http://localhost:8080",
  "enabled": true,
  "max_tokens": 2048,
  "temperature_default": 0.7,
  "updated_at": "2025-11-15T15:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Backend updated successfully
- `400 Bad Request` - Invalid input data
- `404 Not Found` - Backend ID does not exist
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions

---

### 6. Delete Backend

**DELETE** `/api/llm-backends/{id}`

Delete a backend configuration.

**Path Parameters:**
- `id` (integer) - Backend ID to delete

**Example Request:**
```bash
curl -X DELETE http://localhost:8080/api/llm-backends/3 \
  -H "Authorization: Bearer $TOKEN"
```

**Example Response:**
```json
{
  "message": "Backend deleted successfully",
  "id": 3
}
```

**Status Codes:**
- `200 OK` - Backend deleted successfully
- `404 Not Found` - Backend ID does not exist
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions

---

### 7. Toggle Backend Enabled Status

**POST** `/api/llm-backends/{id}/toggle`

Toggle the `enabled` status of a backend (true → false or false → true).

**Path Parameters:**
- `id` (integer) - Backend ID

**Example Request:**
```bash
# Disable backend
curl -X POST http://localhost:8080/api/llm-backends/1/toggle \
  -H "Authorization: Bearer $TOKEN"
```

**Example Response:**
```json
{
  "id": 1,
  "model_name": "phi3:mini",
  "enabled": false,
  "message": "Backend disabled"
}
```

**Status Codes:**
- `200 OK` - Status toggled successfully
- `404 Not Found` - Backend ID does not exist
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions

---

## Common Use Cases

### Use Case 1: Switch Model to Faster Backend

**Scenario:** You want to switch `phi3:mini` from Ollama to MLX for 2x performance improvement.

```bash
# 1. Find backend ID
curl -X GET http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | select(.model_name == "phi3:mini")'

# Output: {"id": 1, "model_name": "phi3:mini", "backend_type": "ollama", ...}

# 2. Update to MLX
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "backend_type": "mlx",
    "endpoint_url": "http://localhost:8080"
  }'

# 3. Verify change
curl -X GET http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" | jq '.backend_type'

# Output: "mlx"
```

**Result:** All future requests for `phi3:mini` will use MLX backend. No code changes or service restarts required!

---

### Use Case 2: Add New Model with Auto Fallback

**Scenario:** Deploy a new model with automatic fallback (try MLX first, fall back to Ollama).

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
    "description": "Large model with automatic fallback"
  }'
```

**Result:** Router will try MLX backend first, fall back to Ollama on any error.

---

### Use Case 3: Temporarily Disable a Backend

**Scenario:** MLX server is down for maintenance, temporarily switch to Ollama.

```bash
# Option 1: Toggle to disable
curl -X POST http://localhost:8080/api/llm-backends/1/toggle \
  -H "Authorization: Bearer $TOKEN"

# Option 2: Update to Ollama backend
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "backend_type": "ollama",
    "endpoint_url": "http://localhost:11434"
  }'
```

---

### Use Case 4: Monitor Performance Metrics

**Scenario:** Check performance stats for all models.

```bash
curl -X GET http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | {
    model: .model_name,
    backend: .backend_type,
    tokens_per_sec: .avg_tokens_per_sec,
    latency_ms: .avg_latency_ms,
    requests: .total_requests,
    errors: .total_errors
  }'
```

**Output:**
```json
{
  "model": "phi3:mini",
  "backend": "mlx",
  "tokens_per_sec": 33.4,
  "latency_ms": 2980.0,
  "requests": 256,
  "errors": 1
}
{
  "model": "llama3.1:8b",
  "backend": "ollama",
  "tokens_per_sec": 6.7,
  "latency_ms": 14950.0,
  "requests": 87,
  "errors": 5
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

**400 Bad Request:**
```json
{
  "detail": "Invalid backend_type. Must be one of: ollama, mlx, auto"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**403 Forbidden:**
```json
{
  "detail": "Insufficient permissions: write access required"
}
```

**404 Not Found:**
```json
{
  "detail": "Backend not found for model: phi3:mini"
}
```

**409 Conflict:**
```json
{
  "detail": "Backend configuration already exists for model: phi3:mini"
}
```

---

## Authentication and Permissions

**Required Permissions:**

| Endpoint | Method | Permission |
|----------|--------|------------|
| `/api/llm-backends` | GET | `llm_backends:read` |
| `/api/llm-backends/{id}` | GET | `llm_backends:read` |
| `/api/llm-backends/model/{model}` | GET | **None (public)** |
| `/api/llm-backends` | POST | `llm_backends:write` |
| `/api/llm-backends/{id}` | PUT | `llm_backends:write` |
| `/api/llm-backends/{id}` | DELETE | `llm_backends:write` |
| `/api/llm-backends/{id}/toggle` | POST | `llm_backends:write` |

**Get API Token:**
```bash
# Retrieve from Kubernetes secrets
kubectl -n automation get secret admin-api-credentials -o jsonpath='{.data.api-token}' | base64 -d
```

---

## Rate Limiting and Caching

**Configuration Cache:**
- LLMRouter caches backend configs for 60 seconds
- Reduces database load for high-frequency requests
- Update takes effect within 60 seconds

**No Rate Limits:**
- Admin API has no rate limiting (internal use only)
- Service-to-service endpoint optimized for high throughput

---

## Next Steps

- **[Configuration Guide](./llm-backend-config)** - Step-by-step setup
- **[Router Technical Docs](./llm-backend-router)** - How routing works
- **[Deployment Guide](./llm-backend-deployment)** - Production deployment
- **[Overview](./llm-backend-overview)** - Back to system overview

---

**Last Updated:** November 15, 2025
**API Version:** 1.0.0
**Maintained By:** Jay Stuart
