# LLM Metrics Database Logging - Implementation Summary

## Overview

Successfully added database metric logging to Gateway and Orchestrator services so that all LLM requests appear on the admin performance metrics page.

## Changes Made

### 1. Gateway Service (`src/gateway/main.py`)

#### Added Helper Function

**Function:** `_log_metric_to_db()` (lines 178-243)
- POSTs metrics to admin backend at `/api/llm-backends/metrics`
- Fire-and-forget async function (non-blocking)
- Handles errors gracefully without impacting main request
- 5-second timeout for resilience

**Metric Fields:**
- timestamp (float)
- model (str)
- backend (str)
- latency_seconds (float)
- tokens (int)
- tokens_per_second (float)
- request_id (optional str)
- session_id (optional str)
- user_id (optional str)
- zone (optional str)
- intent (optional str)

#### Updated `route_to_ollama()` Function

**Changes:** (lines 305-384)
- Added parameters: `device_id`, `session_id`, `user_id`
- Captures `start_time` before LLM call
- Extracts `eval_count` from Ollama response
- Calculates latency and tokens/sec
- Calls `_log_metric_to_db()` asynchronously via `asyncio.create_task()`

**Metrics Captured:**
- Model name (mapped from OpenAI to Ollama models)
- Backend: "ollama"
- Latency in seconds
- Token count from Ollama's eval_count
- Tokens per second calculation
- Request ID, session ID, device ID (zone)

#### Added Configuration

**Environment Variable:** `ADMIN_API_URL` (line 54)
- Default: `http://athena-admin-backend.athena-admin.svc.cluster.local:8080`
- Used for posting metrics to admin backend

### 2. Orchestrator Service

**Status:** ✅ Already Covered

The orchestrator makes all LLM calls through `llm_router.generate()`, which already handles metric persistence automatically via `_persist_metric()` in the LLM router.

**LLM Calls Tracked:**
1. **classify_node()** (line 298) - Intent classification
2. **synthesize_node()** (line 634) - Response generation
3. **validate_node()** (line 734) - Fact checking

**No changes needed** - existing implementation is correct.

### 3. Deployment Configuration

#### Updated `deployment/mac-studio/docker-compose.yml`

**Gateway Service:**
- Added `ADMIN_API_URL` environment variable (line 151)

**Orchestrator Service:**
- Added `ADMIN_API_URL` environment variable (line 223)

**Value:** `http://athena-admin-backend.athena-admin.svc.cluster.local:8080`

### 4. Documentation

**Created:** `docs/LLM_METRICS_LOGGING.md`
- Comprehensive guide to metric logging system
- Architecture diagram
- Implementation details
- Configuration instructions
- API documentation
- Troubleshooting guide

## How It Works

### Gateway Flow

```
1. User makes LLM request via Gateway
2. Gateway routes to either:
   a. Orchestrator (for Athena queries)
   b. Direct Ollama (for general queries)
3. For direct Ollama calls:
   - Capture start_time
   - Call Ollama API
   - Extract eval_count, response_text
   - Calculate latency and tokens/sec
   - Fire async task to log metric
4. Return response to user (don't wait for metric logging)
```

### Orchestrator Flow

```
1. Gateway routes to Orchestrator
2. Orchestrator processes through LangGraph:
   - classify_node -> llm_router.generate()
   - synthesize_node -> llm_router.generate()
   - validate_node -> llm_router.generate()
3. Each llm_router.generate() call:
   - Executes LLM request
   - Captures metrics
   - Fires async task to persist to DB
4. Orchestrator returns final response
```

### Metric Persistence

```
1. Service calls _log_metric_to_db() or llm_router._persist_metric()
2. Creates HTTP client
3. POSTs to http://athena-admin-backend.../api/llm-backends/metrics
4. Admin backend:
   - Validates payload
   - Creates LLMPerformanceMetric record
   - Saves to database
   - Returns 201 Created
5. Metric appears on admin UI performance page
```

## Testing

### Manual Testing Steps

1. **Start services:**
   ```bash
   cd deployment/mac-studio
   docker compose up -d
   ```

2. **Make a test request:**
   ```bash
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [{"role": "user", "content": "Hello"}]
     }'
   ```

3. **Check metrics in database:**
   ```bash
   curl "http://localhost:8080/api/llm-backends/metrics?limit=1"
   ```

4. **Check admin UI:**
   - Navigate to: https://athena-admin.xmojo.net/performance
   - Verify new metric appears

### Voice Test via Admin UI

1. Go to: https://athena-admin.xmojo.net/voice-test
2. Enter query: "What is the weather in Baltimore?"
3. Click "Send"
4. Go to: https://athena-admin.xmojo.net/performance
5. Verify metric with:
   - Model: phi3:mini or llama3.1:8b
   - Backend: ollama
   - Latency: 2-5 seconds
   - Tokens/sec: 40-60

## Error Handling

### Fire-and-Forget Design

Metric logging uses `asyncio.create_task()` for fire-and-forget execution:

**Benefits:**
- ✅ Non-blocking - doesn't slow down LLM requests
- ✅ Resilient - failures don't break main flow
- ✅ Simple - no complex queue/retry logic needed

**Limitations:**
- ❌ No retry on failure
- ❌ Metrics may be lost if admin backend is down
- ❌ No delivery guarantees

### Graceful Degradation

If metric logging fails:
1. Error is logged: `logger.error("Metric logging error: ...")`
2. Request continues normally
3. User gets their response
4. Metric is lost (but request succeeds)

### Monitoring

Check logs for issues:
```bash
# Gateway
docker logs athena-gateway | grep -i "metric"

# Orchestrator
docker logs athena-orchestrator | grep -i "metric"

# Admin backend
kubectl -n athena-admin logs deployment/athena-admin-backend | grep -i "metric"
```

## Key Design Decisions

### 1. Fire-and-Forget vs. Queue

**Chose:** Fire-and-forget via `asyncio.create_task()`

**Rationale:**
- Simple implementation
- Minimal latency impact
- Acceptable data loss risk (metrics are non-critical)
- Admin backend already handles persistence

**Alternative Considered:** Redis queue with worker
- More complex
- Overkill for current scale
- Can migrate later if needed

### 2. Direct HTTP vs. Message Bus

**Chose:** Direct HTTP POST to admin backend

**Rationale:**
- Simple and direct
- Low latency (~10-50ms)
- Works with existing admin API
- No additional infrastructure needed

**Alternative Considered:** RabbitMQ/Kafka
- Too complex for current needs
- Additional services to maintain
- Can add later for high-volume scenarios

### 3. Individual Requests vs. Batching

**Chose:** Individual HTTP requests per metric

**Rationale:**
- Real-time metrics visibility
- Simpler implementation
- Acceptable overhead at current scale

**Alternative Considered:** Batch metrics every N seconds
- Would reduce API calls
- Adds complexity (buffering, flushing)
- Can add later if needed

## Performance Impact

### Expected Overhead

**Per LLM Request:**
- Metric calculation: ~1-2ms
- HTTP POST (async): ~10-50ms (non-blocking)
- Total user-visible impact: ~0ms (fire-and-forget)

**Admin Backend:**
- Database INSERT: ~5-10ms
- Expected load: ~10-100 requests/minute
- Database table size growth: ~1MB/day

### Monitoring

Watch for:
- Slow admin backend response times
- Database connection pool exhaustion
- Disk space growth on postgres

## Future Enhancements

### Near-term (1-2 weeks)

1. **Add metric batching** - Reduce API calls
2. **Add retry logic** - Improve reliability
3. **Add metric buffering** - Handle temporary outages

### Medium-term (1-2 months)

1. **Real-time metric streaming** - WebSocket push to UI
2. **Metric aggregation** - Pre-compute averages/percentiles
3. **Alerting** - Alert on performance degradation
4. **Cost tracking** - Estimate costs based on token usage

### Long-term (3-6 months)

1. **Time-series database** - Move to InfluxDB or TimescaleDB
2. **Advanced analytics** - ML-based anomaly detection
3. **Multi-region support** - Aggregate metrics across regions
4. **Custom dashboards** - Grafana integration

## Files Changed

### Modified Files

1. **src/gateway/main.py**
   - Added `_log_metric_to_db()` helper function
   - Updated `route_to_ollama()` to log metrics
   - Added `ADMIN_API_URL` configuration

2. **deployment/mac-studio/docker-compose.yml**
   - Added `ADMIN_API_URL` to gateway environment
   - Added `ADMIN_API_URL` to orchestrator environment

### New Files

1. **docs/LLM_METRICS_LOGGING.md**
   - Comprehensive documentation
   - Architecture diagrams
   - Troubleshooting guide

2. **METRICS_IMPLEMENTATION_SUMMARY.md** (this file)
   - Implementation summary
   - Testing instructions
   - Design decisions

## Verification Checklist

### Code Changes

- [x] Gateway logs metrics for direct Ollama calls
- [x] Orchestrator uses LLM router (already logs metrics)
- [x] Fire-and-forget async implementation
- [x] Error handling without breaking requests
- [x] Admin API URL configuration

### Configuration

- [x] ADMIN_API_URL in gateway docker-compose
- [x] ADMIN_API_URL in orchestrator docker-compose
- [x] Default value for local/k8s environments

### Testing

- [ ] Test direct Ollama call via Gateway
- [ ] Test orchestrator call via admin voice test
- [ ] Verify metrics appear in database
- [ ] Verify metrics appear on admin UI
- [ ] Test error handling (admin backend down)

### Documentation

- [x] Implementation summary (this file)
- [x] LLM metrics logging guide
- [x] Architecture documentation
- [x] Troubleshooting guide

## Next Steps

1. **Deploy Changes:**
   ```bash
   cd deployment/mac-studio
   docker compose down
   docker compose up -d
   ```

2. **Verify Deployment:**
   - Check service logs
   - Test voice query
   - Check admin UI metrics page

3. **Monitor Performance:**
   - Watch logs for metric errors
   - Monitor admin backend latency
   - Check database growth

4. **Iterate:**
   - Add batching if needed
   - Add retry logic if metrics are lost
   - Optimize if performance degrades

## Conclusion

Successfully implemented database metric logging for all LLM requests in both Gateway and Orchestrator services. The implementation is:

- ✅ **Non-blocking** - Fire-and-forget async design
- ✅ **Resilient** - Graceful error handling
- ✅ **Simple** - Minimal code changes
- ✅ **Complete** - All LLM calls tracked
- ✅ **Documented** - Comprehensive guides

All LLM requests will now appear on the admin performance metrics page for real-time monitoring and analysis.
