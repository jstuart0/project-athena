# End-to-End Latency Tracking with Feature Flag Management

**Date:** 2025-11-16
**Status:** In Progress
**Priority:** High

## Overview

Implement comprehensive end-to-end latency tracking with component-level breakdowns and feature flag management. This allows toggling features on/off to see their impact on overall latency.

## Architecture

### Database Schema

**`features` table:**
- Track system features (intent classification, RAG, caching, etc.)
- Enable/disable state
- Average latency contribution
- Category grouping
- Required flag (cannot be disabled)

**`llm_performance_metrics` table extensions:**
- Component latencies:
  - gateway_latency_ms
  - intent_classification_latency_ms
  - rag_lookup_latency_ms
  - llm_inference_latency_ms
  - response_assembly_latency_ms
  - cache_lookup_latency_ms
- features_enabled (JSONB) - snapshot of which features were enabled for this request

### Features to Track

**Processing Layer:**
- `intent_classification` - Intent detection and routing
- `multi_intent_detection` - Multi-intent query parsing
- `conversation_context` - Context preservation between queries

**RAG Layer:**
- `rag_weather` - Weather data retrieval
- `rag_sports` - Sports data retrieval
- `rag_airports` - Airport data retrieval

**Optimization Layer:**
- `redis_caching` - Redis cache for responses
- `mlx_backend` - MLX backend selection
- `response_streaming` - Streaming responses

**Integration Layer:**
- `home_assistant` - Home Assistant integration
- `clarification_questions` - Interactive clarifications

### API Endpoints

**Features Management:**
```
GET    /api/features                 # List all features
GET    /api/features/{id}            # Get feature details
PUT    /api/features/{id}/toggle     # Toggle feature on/off
GET    /api/features/impact          # Calculate latency impact by feature
```

**Enhanced Metrics:**
```
GET    /api/llm-backends/metrics     # Now includes component latencies
GET    /api/llm-backends/metrics/breakdown  # Latency breakdown analysis
GET    /api/llm-backends/metrics/what-if    # What-if analysis by feature combo
```

### Frontend UI

**Features Page:**
- Feature toggle switches organized by category
- Real-time on/off indicators
- Average latency contribution per feature
- Hit rate for caching features
- Visual warning for required features

**Enhanced Metrics Dashboard:**
- Component latency waterfall chart
- Feature impact visualization
- What-if analysis table
- Side-by-side comparison: current vs optimized
- Timeline showing latency trends

## Implementation Steps

### Step 1: Database ✅ DONE
- [x] Extended `models.py` with `Feature` model
- [x] Enhanced `LLMPerformanceMetric` with component latencies
- [ ] Create Alembic migration
- [ ] Seed initial feature data

### Step 2: Backend API
- [ ] Create `/admin/backend/app/routes/features.py`
- [ ] Implement CRUD operations for features
- [ ] Add latency impact calculation
- [ ] Add what-if analysis endpoint
- [ ] Extend metrics endpoints

### Step 3: Frontend - Features Management
- [ ] Create `/admin/frontend/features.js`
- [ ] Feature toggle UI with categories
- [ ] Real-time state indicators
- [ ] Latency contribution display

### Step 4: Frontend - Enhanced Metrics
- [ ] Extend `/admin/frontend/metrics.js`
- [ ] Component latency waterfall
- [ ] Feature impact visualization
- [ ] What-if analysis table

### Step 5: Integration
- [ ] Update orchestrator to track component latencies
- [ ] Update gateway to record feature snapshots
- [ ] Implement latency calculation logic

### Step 6: Testing & Deployment
- [ ] Test feature toggles
- [ ] Verify latency tracking
- [ ] Deploy to thor cluster

## Success Criteria

- [ ] All features are listed with toggle controls
- [ ] Component latencies are tracked per request
- [ ] What-if analysis shows projected latency
- [ ] Visual indicators clearly show enabled/disabled state
- [ ] Cannot disable required features
- [ ] Latency breakdown sums to total end-to-end latency

## Example UI Flow

1. **Features Page:**
   - User sees all features grouped by category
   - Toggle switches show current state (green=on, gray=off)
   - Each feature shows its average latency contribution
   - Required features have lock icon

2. **Metrics Dashboard:**
   - Waterfall chart shows component latencies stacked
   - Feature impact table shows:
     - Feature name
     - Enabled status
     - Avg latency (ms)
     - % of total
   - What-if table shows:
     - Current config: 2.8s total
     - All optimizations: 1.2s total (-57%)
     - No RAG: 2.1s (-25%)
     - No caching: 3.2s (+14%)

3. **Real-time Impact:**
   - When toggling a feature, see immediate update to projected latency
   - Chart adjusts to show new latency breakdown

## Technical Notes

- Feature state changes are propagated to orchestrator via API
- Latency tracking happens at component boundaries
- Metrics are stored with feature snapshot for historical analysis
- What-if calculations use historical averages
- Required features cannot be toggled (grayed out)

## Migration Plan

```sql
-- Add features table
CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    avg_latency_ms FLOAT,
    hit_rate FLOAT,
    required BOOLEAN DEFAULT false,
    priority INTEGER DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Extend llm_performance_metrics
ALTER TABLE llm_performance_metrics
    ADD COLUMN gateway_latency_ms FLOAT,
    ADD COLUMN intent_classification_latency_ms FLOAT,
    ADD COLUMN rag_lookup_latency_ms FLOAT,
    ADD COLUMN llm_inference_latency_ms FLOAT,
    ADD COLUMN response_assembly_latency_ms FLOAT,
    ADD COLUMN cache_lookup_latency_ms FLOAT,
    ADD COLUMN features_enabled JSONB;

-- Seed initial features
INSERT INTO features (name, display_name, description, category, enabled, required) VALUES
    ('intent_classification', 'Intent Classification', 'Classify user query intent', 'processing', true, true),
    ('multi_intent_detection', 'Multi-Intent Detection', 'Detect and parse multiple intents', 'processing', true, false),
    ('conversation_context', 'Conversation Context', 'Preserve context between queries', 'processing', true, false),
    ('rag_weather', 'Weather RAG', 'Retrieve weather data', 'rag', true, false),
    ('rag_sports', 'Sports RAG', 'Retrieve sports data', 'rag', true, false),
    ('rag_airports', 'Airports RAG', 'Retrieve airport data', 'rag', true, false),
    ('redis_caching', 'Redis Caching', 'Cache responses in Redis', 'optimization', true, false),
    ('mlx_backend', 'MLX Backend', 'Use MLX for inference', 'optimization', true, false),
    ('home_assistant', 'Home Assistant', 'Integrate with HA', 'integration', true, false),
    ('clarification_questions', 'Clarifications', 'Ask clarifying questions', 'integration', true, false);
```

## Dependencies

- Alembic for database migration
- FastAPI for backend routes
- React-like UI patterns for frontend
- Chart.js or D3.js for visualizations (optional, can use CSS)

## Rollback Plan

If issues occur:
1. Disable feature toggles (set all to enabled)
2. Revert migration if database issues
3. Roll back frontend deployment
4. Metrics will still work with null component latencies

## Follow-up Enhancements

- Historical latency trends per feature
- A/B testing different feature combinations
- Automatic optimization recommendations
- Alert when latency exceeds thresholds
- Export latency reports
