# LLM Metrics Database Logging

## Overview

All LLM requests from the Gateway and Orchestrator services now automatically log performance metrics to the admin database. This enables real-time monitoring via the admin UI's performance metrics page.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Admin Database                           │
│              (llm_performance_metric table)                  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ POST /api/llm-backends/metrics
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────────────────┐              ┌───────────────────┐
│  Gateway Service  │              │ Orchestrator      │
│                   │              │ Service           │
│ - Direct Ollama   │              │                   │
│   calls           │              │ - LLM Router      │
│ - Logs metrics    │              │   (auto-logs)     │
│   on each call    │              │                   │
└───────────────────┘              └───────────────────┘
```

## Implementation Details

### Gateway Service (`src/gateway/main.py`)

**Direct Ollama Calls:**
- `route_to_ollama()` function now logs metrics for all direct LLM calls
- Metrics are logged asynchronously (fire-and-forget) to avoid blocking
- Captures: model, backend, latency, tokens, tokens/sec, session_id, device_id

**Helper Function:**
- `_log_metric_to_db()` - POSTs metrics to admin backend
- Handles errors gracefully without impacting main request flow
- Uses 5-second timeout for resilience

### Orchestrator Service (`src/orchestrator/main.py`)

**LLM Router Integration:**
- All LLM calls use `llm_router.generate()`
- LLM Router automatically persists metrics via `_persist_metric()`
- No changes needed in orchestrator - already covered!

**LLM Calls Tracked:**
1. **classify_node()** - Intent classification (line 298)
2. **synthesize_node()** - Response generation (line 634)
3. **validate_node()** - Fact checking (line 734)

### Shared LLM Router (`src/shared/llm_router.py`)

**Automatic Metric Persistence:**
- Every call to `generate()` logs metrics to database
- Metrics include: timestamp, model, backend, latency, tokens, tokens/sec
- Optional metadata: request_id, session_id, user_id, zone, intent
- Fire-and-forget async task via `_persist_metric()` (line 343)

## Metric Schema

Metrics are stored in the `llm_performance_metric` table with the following fields:

```python
{
    "timestamp": float,              # Unix timestamp of request start
    "model": str,                    # Model name (e.g., "phi3:mini")
    "backend": str,                  # Backend type ("ollama", "mlx", "auto")
    "latency_seconds": float,        # Total request latency
    "tokens": int,                   # Number of tokens generated
    "tokens_per_second": float,      # Token generation speed
    "request_id": str,               # Optional request ID
    "session_id": str,               # Optional session ID
    "user_id": str,                  # Optional user ID
    "zone": str,                     # Optional zone/location
    "intent": str                    # Optional intent classification
}
```

## Configuration

### Environment Variables

Both Gateway and Orchestrator require the `ADMIN_API_URL` environment variable:

```bash
# Kubernetes service URL (production)
ADMIN_API_URL=http://athena-admin-backend.athena-admin.svc.cluster.local:8080

# Local development
ADMIN_API_URL=http://localhost:8080
```

### Docker Compose

Updated `deployment/mac-studio/docker-compose.yml`:

```yaml
gateway:
  environment:
    - ADMIN_API_URL=http://athena-admin-backend.athena-admin.svc.cluster.local:8080

orchestrator:
  environment:
    - ADMIN_API_URL=http://athena-admin-backend.athena-admin.svc.cluster.local:8080
```

### LLM Router Configuration

The LLM Router can be configured to enable/disable metric persistence:

```python
router = LLMRouter(
    admin_url="http://localhost:8080",
    persist_metrics=True  # Enable database logging (default)
)
```

## Admin API Endpoint

**POST** `/api/llm-backends/metrics`

Creates a new performance metric record.

**Request Body:**
```json
{
    "timestamp": 1700000000.123,
    "model": "phi3:mini",
    "backend": "ollama",
    "latency_seconds": 2.5,
    "tokens": 150,
    "tokens_per_second": 60.0,
    "request_id": "req_123abc",
    "session_id": "sess_xyz789",
    "intent": "weather_query"
}
```

**Response:**
```json
{
    "id": 1,
    "status": "created"
}
```

**Authentication:**
- No authentication required for service-to-service calls
- Endpoint is designed for internal use by Gateway/Orchestrator

## Viewing Metrics

### Admin UI

Access the performance metrics page at:
```
https://athena-admin.xmojo.net/performance
```

Features:
- Real-time metrics dashboard
- Model performance comparison
- Backend performance comparison
- Historical trends
- Filtering by model, backend, time range

### API

**GET** `/api/llm-backends/metrics`

Query parameters:
- `model` - Filter by model name (optional)
- `backend` - Filter by backend type (optional)
- `limit` - Maximum records to return (default: 100, max: 1000)

Example:
```bash
curl "http://localhost:8080/api/llm-backends/metrics?model=phi3:mini&limit=50"
```

## Error Handling

### Metric Logging Failures

Metric logging is designed to be resilient:

1. **Fire-and-forget**: Metrics are logged asynchronously via `asyncio.create_task()`
2. **Non-blocking**: Failures don't impact LLM request processing
3. **Logged warnings**: Errors are logged but don't raise exceptions
4. **Timeout protection**: 5-second timeout prevents hanging
5. **Graceful degradation**: If admin backend is unavailable, requests continue normally

### Monitoring

Check logs for metric logging issues:

```bash
# Gateway logs
docker logs athena-gateway | grep metric

# Orchestrator logs
docker logs athena-orchestrator | grep metric

# Admin backend logs
kubectl -n athena-admin logs -f deployment/athena-admin-backend
```

## Testing

### Manual Testing

1. Make an LLM request via the admin UI voice test
2. Check the performance metrics page
3. Verify new metric appears in the table

### Programmatic Testing

```bash
# Test Gateway direct Ollama call
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Check metrics were logged
curl "http://localhost:8080/api/llm-backends/metrics?limit=1"
```

### Voice Test via Admin UI

1. Navigate to: https://athena-admin.xmojo.net/voice-test
2. Enter a test query: "What is the weather?"
3. Click "Send"
4. Navigate to: https://athena-admin.xmojo.net/performance
5. Verify new metric appears with:
   - Model: phi3:mini or llama3.1:8b
   - Backend: ollama
   - Latency: ~2-5 seconds
   - Tokens/sec: ~40-60

## Troubleshooting

### Metrics Not Appearing

1. **Check ADMIN_API_URL environment variable:**
   ```bash
   docker exec athena-gateway env | grep ADMIN_API_URL
   docker exec athena-orchestrator env | grep ADMIN_API_URL
   ```

2. **Check admin backend is running:**
   ```bash
   kubectl -n athena-admin get pods
   curl http://athena-admin-backend.athena-admin.svc.cluster.local:8080/health
   ```

3. **Check database connectivity:**
   ```bash
   kubectl -n athena-admin exec -it deployment/athena-admin-backend -- \
     python -c "from app.database import get_db; next(get_db())"
   ```

4. **Check service logs:**
   ```bash
   docker logs athena-gateway --tail 50
   docker logs athena-orchestrator --tail 50
   ```

### Metric Logging Errors

If you see errors like:
```
failed_to_log_metric status_code=500
```

Check:
1. Admin backend database connection
2. Database schema is up to date (run migrations)
3. LLMPerformanceMetric model exists in database

### Performance Impact

Metric logging should have minimal impact:
- Async fire-and-forget (doesn't block)
- 5-second timeout prevents hanging
- Typical overhead: <50ms

If you see performance issues:
1. Disable metric persistence temporarily:
   ```python
   router = LLMRouter(persist_metrics=False)
   ```
2. Check admin backend response times
3. Check database query performance

## Future Enhancements

Potential improvements:

1. **Batch metric logging** - Reduce API calls by batching metrics
2. **Local buffering** - Buffer metrics locally and flush periodically
3. **Metric aggregation** - Pre-aggregate metrics for faster queries
4. **Real-time streaming** - WebSocket stream of live metrics
5. **Alerting** - Alert on performance degradation
6. **Cost tracking** - Track token usage and estimated costs

## Related Documentation

- [Admin Configuration Guide](ADMIN_CONFIG.md)
- [LLM Backend Router](../scripts/wiki_content/llm-backend-router.md)
- [Performance Metrics API](../admin/backend/app/routes/llm_backends.py)
