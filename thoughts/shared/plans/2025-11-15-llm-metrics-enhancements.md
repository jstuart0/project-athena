# LLM Performance Metrics Enhancements

**Date:** November 15, 2025
**Status:** Planning
**Priority:** Medium
**Estimated Effort:** 8-12 hours total

## Overview

Following the successful implementation of in-memory LLM performance metrics tracking (Phase 1 & 2 of Sprint 1), this plan outlines three enhancements to provide long-term visibility, visualization, and alerting for LLM performance.

**Current State:**
- ✅ Rolling window metrics (last 100 requests) stored in memory
- ✅ `/llm-metrics` endpoint exposes real-time performance data
- ✅ Tracking: latency, tokens/sec, per-model, per-backend stats

**Limitations of Current Implementation:**
- ❌ Metrics lost on orchestrator restart
- ❌ No historical trend analysis
- ❌ No visualization dashboard
- ❌ No performance degradation alerts
- ❌ Limited to 100 most recent requests

## Goals

1. **Persistence**: Store metrics in database for long-term analysis
2. **Visualization**: Display performance trends in Admin UI dashboard
3. **Alerting**: Notify when performance degrades below thresholds

## Enhancement 1: Persist Metrics to Database

**Estimated Effort:** 3-4 hours

### Database Schema

Create new table `llm_performance_metrics` in the Admin database:

```sql
CREATE TABLE llm_performance_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    model VARCHAR(100) NOT NULL,
    backend VARCHAR(50) NOT NULL,
    latency_seconds NUMERIC(8, 3) NOT NULL,
    tokens_generated INTEGER NOT NULL,
    tokens_per_second NUMERIC(10, 2) NOT NULL,
    prompt_tokens INTEGER,
    request_id VARCHAR(100),
    session_id VARCHAR(100),
    user_id VARCHAR(100),
    zone VARCHAR(100),
    intent VARCHAR(100),

    -- Indexes for common queries
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_model (model),
    INDEX idx_backend (backend),
    INDEX idx_model_timestamp (model, timestamp DESC)
);

-- Partition by month for performance (optional, future optimization)
-- CREATE TABLE llm_performance_metrics_2025_11 PARTITION OF llm_performance_metrics
--     FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

### Implementation Steps

#### Step 1: Add Database Model (Admin Backend)

**File:** `admin/backend/app/models.py`

```python
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Index
from datetime import datetime

class LLMPerformanceMetric(Base):
    """LLM performance metrics for monitoring and analysis."""
    __tablename__ = "llm_performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    model = Column(String(100), nullable=False, index=True)
    backend = Column(String(50), nullable=False, index=True)
    latency_seconds = Column(Numeric(8, 3), nullable=False)
    tokens_generated = Column(Integer, nullable=False)
    tokens_per_second = Column(Numeric(10, 2), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    request_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)
    user_id = Column(String(100), nullable=True)
    zone = Column(String(100), nullable=True)
    intent = Column(String(100), nullable=True)

    __table_args__ = (
        Index('idx_model_timestamp', 'model', 'timestamp'),
    )
```

#### Step 2: Create Database Migration

**File:** `admin/backend/alembic/versions/004_llm_performance_metrics.py`

```python
"""Add LLM performance metrics table

Revision ID: 004_llm_metrics
Revises: 003_intent_validation_multiintent
Create Date: 2025-11-15
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'llm_performance_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('backend', sa.String(50), nullable=False),
        sa.Column('latency_seconds', sa.Numeric(8, 3), nullable=False),
        sa.Column('tokens_generated', sa.Integer(), nullable=False),
        sa.Column('tokens_per_second', sa.Numeric(10, 2), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('zone', sa.String(100), nullable=True),
        sa.Column('intent', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_timestamp', 'llm_performance_metrics', ['timestamp'])
    op.create_index('idx_model', 'llm_performance_metrics', ['model'])
    op.create_index('idx_backend', 'llm_performance_metrics', ['backend'])
    op.create_index('idx_model_timestamp', 'llm_performance_metrics', ['model', 'timestamp'])

def downgrade():
    op.drop_index('idx_model_timestamp', 'llm_performance_metrics')
    op.drop_index('idx_backend', 'llm_performance_metrics')
    op.drop_index('idx_model', 'llm_performance_metrics')
    op.drop_index('idx_timestamp', 'llm_performance_metrics')
    op.drop_table('llm_performance_metrics')
```

#### Step 3: Add Metrics Persistence to LLM Router

**File:** `src/shared/llm_router.py`

Add database persistence option to LLM Router:

```python
class LLMRouter:
    def __init__(
        self,
        admin_url: Optional[str] = None,
        cache_ttl: int = 60,
        metrics_window_size: int = 100,
        persist_metrics: bool = True  # NEW
    ):
        # ... existing code ...
        self._persist_metrics = persist_metrics
        self._admin_url_base = admin_url or os.getenv("ADMIN_API_URL", "http://localhost:8080")

    async def _persist_metric(self, metric: Dict[str, Any]):
        """Persist metric to database via Admin API."""
        if not self._persist_metrics:
            return

        try:
            url = f"{self._admin_url_base}/api/llm-backends/metrics"
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=metric, timeout=5.0)
                if response.status_code != 201:
                    logger.warning(
                        "failed_to_persist_metric",
                        status_code=response.status_code,
                        error=response.text
                    )
        except Exception as e:
            logger.error("metric_persistence_error", error=str(e))

    async def generate(self, ...):
        # ... existing code ...

        finally:
            duration = time.time() - start_time

            # Track metrics if response was generated
            if response:
                tokens = response.get("eval_count", 0)
                tokens_per_sec = tokens / duration if duration > 0 and tokens > 0 else 0

                metric = {
                    "timestamp": start_time,
                    "model": model,
                    "backend": response.get("backend"),
                    "latency_seconds": duration,
                    "tokens": tokens,
                    "tokens_per_second": tokens_per_sec,
                    # NEW - add context from kwargs if available
                    "request_id": kwargs.get("request_id"),
                    "session_id": kwargs.get("session_id"),
                    "user_id": kwargs.get("user_id"),
                    "zone": kwargs.get("zone"),
                    "intent": kwargs.get("intent")
                }
                self._metrics.append(metric)

                # NEW - Persist to database (async, non-blocking)
                asyncio.create_task(self._persist_metric(metric))

                # ... existing logging ...
```

#### Step 4: Add Admin API Endpoint for Metrics Persistence

**File:** `admin/backend/app/routes/llm_backends.py`

```python
from app.models import LLMPerformanceMetric
from pydantic import BaseModel
from datetime import datetime

class LLMMetricCreate(BaseModel):
    """Schema for creating LLM performance metric."""
    timestamp: float  # Unix timestamp
    model: str
    backend: str
    latency_seconds: float
    tokens: int
    tokens_per_second: float
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    zone: Optional[str] = None
    intent: Optional[str] = None

@router.post("/metrics", status_code=201)
async def create_metric(
    metric: LLMMetricCreate,
    db: Session = Depends(get_db)
):
    """
    Store LLM performance metric in database.

    Called by LLM Router to persist metrics for long-term analysis.
    """
    try:
        db_metric = LLMPerformanceMetric(
            timestamp=datetime.fromtimestamp(metric.timestamp),
            model=metric.model,
            backend=metric.backend,
            latency_seconds=metric.latency_seconds,
            tokens_generated=metric.tokens,
            tokens_per_second=metric.tokens_per_second,
            request_id=metric.request_id,
            session_id=metric.session_id,
            user_id=metric.user_id,
            zone=metric.zone,
            intent=metric.intent
        )

        db.add(db_metric)
        db.commit()
        db.refresh(db_metric)

        return {"id": db_metric.id, "status": "created"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist metric: {str(e)}"
        )
```

#### Step 5: Update Orchestrator to Pass Context to LLM Router

**File:** `src/orchestrator/main.py`

Modify synthesize_node to pass request context to LLM Router:

```python
async def synthesize_node(state: OrchestratorState) -> OrchestratorState:
    # ... existing code ...

    # Generate response with context for metrics
    llm_response = await llm_router.generate(
        model=selected_model,
        prompt=full_prompt,
        temperature=0.7,
        # NEW - Pass context for metrics persistence
        request_id=state.request_id,
        session_id=state.session_id,
        user_id=state.mode,
        zone=state.room,
        intent=state.intent
    )

    # ... rest of code ...
```

### Testing Steps

1. **Run database migration:**
   ```bash
   cd admin/backend
   alembic upgrade head
   ```

2. **Verify table creation:**
   ```bash
   psql -h postgres-01.xmojo.net -U psadmin -d athena_admin -c "\d llm_performance_metrics"
   ```

3. **Run test queries:**
   ```bash
   curl -X POST http://localhost:8001/query \
     -H "Content-Type: application/json" \
     -d '{"query": "Test query", "user_id": "test", "zone": "office"}'
   ```

4. **Verify metrics persisted:**
   ```bash
   psql -h postgres-01.xmojo.net -U psadmin -d athena_admin \
     -c "SELECT * FROM llm_performance_metrics ORDER BY timestamp DESC LIMIT 5;"
   ```

5. **Check Admin API endpoint:**
   ```bash
   curl http://localhost:8080/api/llm-backends/metrics \
     -H "Content-Type: application/json" \
     -d '{
       "timestamp": 1731715200,
       "model": "phi3:mini",
       "backend": "ollama",
       "latency_seconds": 0.95,
       "tokens": 115,
       "tokens_per_second": 121.05
     }'
   ```

### Success Criteria

- ✅ Database table created successfully
- ✅ Metrics persist to database on each LLM request
- ✅ No performance degradation (persistence is async)
- ✅ Metrics visible in database queries
- ✅ Admin API endpoint accepts and stores metrics

---

## Enhancement 2: Add Metrics Visualization to Admin UI

**Estimated Effort:** 4-5 hours

### UI Components

#### Component 1: Performance Dashboard Page

**File:** `admin/frontend/src/pages/PerformanceDashboard.tsx` (NEW)

```tsx
import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface MetricData {
  timestamp: string;
  model: string;
  backend: string;
  latency_seconds: number;
  tokens_per_second: number;
}

interface AggregatedMetrics {
  overall: {
    total_requests: number;
    avg_latency: number;
    avg_tokens_per_sec: number;
  };
  by_model: Record<string, {
    requests: number;
    avg_latency: number;
    avg_tokens_per_sec: number;
  }>;
}

export default function PerformanceDashboard() {
  const [timeRange, setTimeRange] = useState('1h'); // 1h, 6h, 24h, 7d
  const [metrics, setMetrics] = useState<MetricData[]>([]);
  const [aggregated, setAggregated] = useState<AggregatedMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [timeRange]);

  const fetchMetrics = async () => {
    try {
      // Fetch historical metrics
      const response = await fetch(
        `/api/llm-backends/metrics/history?range=${timeRange}`
      );
      const data = await response.json();
      setMetrics(data.metrics);
      setAggregated(data.aggregated);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading metrics...</div>;

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">LLM Performance Metrics</h1>

      {/* Time Range Selector */}
      <div className="mb-6">
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="border rounded px-4 py-2"
        >
          <option value="1h">Last Hour</option>
          <option value="6h">Last 6 Hours</option>
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
        </select>
      </div>

      {/* Overall Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-4 rounded shadow">
          <h3 className="text-gray-600 text-sm">Total Requests</h3>
          <p className="text-2xl font-bold">{aggregated?.overall.total_requests || 0}</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <h3 className="text-gray-600 text-sm">Avg Latency</h3>
          <p className="text-2xl font-bold">
            {aggregated?.overall.avg_latency.toFixed(2) || 0}s
          </p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <h3 className="text-gray-600 text-sm">Avg Tokens/Sec</h3>
          <p className="text-2xl font-bold">
            {aggregated?.overall.avg_tokens_per_sec.toFixed(1) || 0}
          </p>
        </div>
      </div>

      {/* Latency Over Time */}
      <div className="bg-white p-6 rounded shadow mb-8">
        <h2 className="text-xl font-bold mb-4">Latency Over Time</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={metrics}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="timestamp" />
            <YAxis label={{ value: 'Latency (s)', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="latency_seconds" stroke="#8884d8" name="Latency" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Tokens/Sec Over Time */}
      <div className="bg-white p-6 rounded shadow mb-8">
        <h2 className="text-xl font-bold mb-4">Tokens/Second Over Time</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={metrics}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="timestamp" />
            <YAxis label={{ value: 'Tokens/Sec', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="tokens_per_second" stroke="#82ca9d" name="Tokens/Sec" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Per-Model Comparison */}
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-bold mb-4">Performance by Model</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={Object.entries(aggregated?.by_model || {}).map(([model, stats]) => ({
            model,
            latency: stats.avg_latency,
            tokens_per_sec: stats.avg_tokens_per_sec
          }))}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="model" />
            <YAxis yAxisId="left" label={{ value: 'Latency (s)', angle: -90, position: 'insideLeft' }} />
            <YAxis yAxisId="right" orientation="right" label={{ value: 'Tokens/Sec', angle: 90, position: 'insideRight' }} />
            <Tooltip />
            <Legend />
            <Bar yAxisId="left" dataKey="latency" fill="#8884d8" name="Avg Latency" />
            <Bar yAxisId="right" dataKey="tokens_per_sec" fill="#82ca9d" name="Avg Tokens/Sec" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

#### Component 2: Add to Navigation

**File:** `admin/frontend/src/components/Layout.tsx`

```tsx
// Add to navigation menu
<nav>
  {/* ... existing nav items ... */}
  <NavLink to="/performance">
    <ChartBarIcon className="w-5 h-5" />
    Performance
  </NavLink>
</nav>
```

**File:** `admin/frontend/src/App.tsx`

```tsx
import PerformanceDashboard from './pages/PerformanceDashboard';

// Add route
<Route path="/performance" element={<PerformanceDashboard />} />
```

### Backend API Endpoints

**File:** `admin/backend/app/routes/llm_backends.py`

```python
from datetime import datetime, timedelta
from sqlalchemy import func

@router.get("/metrics/history")
async def get_metrics_history(
    range: str = "1h",  # 1h, 6h, 24h, 7d
    db: Session = Depends(get_db)
):
    """
    Get historical LLM performance metrics.

    Query Parameters:
    - range: Time range (1h, 6h, 24h, 7d)

    Returns:
    - metrics: List of individual metrics
    - aggregated: Overall and per-model statistics
    """
    # Calculate time range
    range_mapping = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7)
    }

    time_delta = range_mapping.get(range, timedelta(hours=1))
    since = datetime.utcnow() - time_delta

    # Query metrics
    metrics_query = db.query(LLMPerformanceMetric).filter(
        LLMPerformanceMetric.timestamp >= since
    ).order_by(LLMPerformanceMetric.timestamp.desc())

    metrics = metrics_query.all()

    # Calculate aggregated stats
    overall_stats = db.query(
        func.count(LLMPerformanceMetric.id).label('total_requests'),
        func.avg(LLMPerformanceMetric.latency_seconds).label('avg_latency'),
        func.avg(LLMPerformanceMetric.tokens_per_second).label('avg_tokens_per_sec')
    ).filter(
        LLMPerformanceMetric.timestamp >= since
    ).first()

    # Per-model stats
    model_stats = db.query(
        LLMPerformanceMetric.model,
        func.count(LLMPerformanceMetric.id).label('requests'),
        func.avg(LLMPerformanceMetric.latency_seconds).label('avg_latency'),
        func.avg(LLMPerformanceMetric.tokens_per_second).label('avg_tokens_per_sec')
    ).filter(
        LLMPerformanceMetric.timestamp >= since
    ).group_by(LLMPerformanceMetric.model).all()

    return {
        "metrics": [
            {
                "timestamp": m.timestamp.isoformat(),
                "model": m.model,
                "backend": m.backend,
                "latency_seconds": float(m.latency_seconds),
                "tokens_per_second": float(m.tokens_per_second)
            }
            for m in metrics
        ],
        "aggregated": {
            "overall": {
                "total_requests": overall_stats.total_requests or 0,
                "avg_latency": float(overall_stats.avg_latency or 0),
                "avg_tokens_per_sec": float(overall_stats.avg_tokens_per_sec or 0)
            },
            "by_model": {
                stat.model: {
                    "requests": stat.requests,
                    "avg_latency": float(stat.avg_latency),
                    "avg_tokens_per_sec": float(stat.avg_tokens_per_sec)
                }
                for stat in model_stats
            }
        }
    }
```

### Testing Steps

1. **Install chart library:**
   ```bash
   cd admin/frontend
   npm install recharts
   ```

2. **Start frontend dev server:**
   ```bash
   npm run dev
   ```

3. **Generate test data:**
   ```bash
   # Run several queries to populate metrics
   for i in {1..20}; do
     curl -X POST http://localhost:8001/query \
       -H "Content-Type: application/json" \
       -d '{"query": "Test query '$i'", "user_id": "test", "zone": "office"}'
     sleep 2
   done
   ```

4. **Access dashboard:**
   - Navigate to http://localhost:3000/performance
   - Verify charts display data
   - Test time range selector
   - Verify real-time updates

### Success Criteria

- ✅ Performance dashboard accessible from navigation
- ✅ Charts display historical metrics correctly
- ✅ Time range selector works (1h, 6h, 24h, 7d)
- ✅ Dashboard auto-refreshes every 30 seconds
- ✅ Per-model comparison shows accurate data
- ✅ Responsive design works on different screen sizes

---

## Enhancement 3: Create Performance Degradation Alerts

**Estimated Effort:** 3-4 hours

### Alert System Architecture

```
LLM Router (Orchestrator)
    ↓ (check thresholds)
Alert Manager
    ↓ (if threshold exceeded)
Notification Service
    ↓
[Email / Slack / Webhook]
```

### Implementation Steps

#### Step 1: Add Alert Configuration to Admin Database

**Database Schema:**

```sql
CREATE TABLE llm_alert_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- 'latency', 'tokens_per_sec'
    model VARCHAR(100),  -- NULL = all models
    threshold_value NUMERIC(10, 2) NOT NULL,
    comparison_operator VARCHAR(10) NOT NULL, -- 'gt', 'lt', 'gte', 'lte'
    time_window_minutes INTEGER NOT NULL DEFAULT 5,
    min_samples INTEGER NOT NULL DEFAULT 3,
    enabled BOOLEAN NOT NULL DEFAULT true,
    notification_channels TEXT[], -- ['email', 'slack', 'webhook']
    cooldown_minutes INTEGER NOT NULL DEFAULT 30,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE llm_alert_history (
    id SERIAL PRIMARY KEY,
    alert_config_id INTEGER REFERENCES llm_alert_configs(id),
    triggered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metric_value NUMERIC(10, 2) NOT NULL,
    threshold_value NUMERIC(10, 2) NOT NULL,
    model VARCHAR(100),
    samples_count INTEGER NOT NULL,
    resolved_at TIMESTAMP,
    notification_sent BOOLEAN NOT NULL DEFAULT false
);
```

**Migration File:** `admin/backend/alembic/versions/005_llm_alerts.py`

#### Step 2: Add Alert Manager to Orchestrator

**File:** `src/shared/alert_manager.py` (NEW)

```python
"""
LLM Performance Alert Manager

Monitors metrics and triggers alerts when thresholds are exceeded.
"""
import asyncio
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class AlertConfig:
    """Alert configuration."""
    def __init__(
        self,
        name: str,
        metric_type: str,  # 'latency', 'tokens_per_sec'
        threshold_value: float,
        comparison: str,  # 'gt', 'lt', 'gte', 'lte'
        model: Optional[str] = None,
        time_window_minutes: int = 5,
        min_samples: int = 3,
        cooldown_minutes: int = 30
    ):
        self.name = name
        self.metric_type = metric_type
        self.threshold_value = threshold_value
        self.comparison = comparison
        self.model = model
        self.time_window_minutes = time_window_minutes
        self.min_samples = min_samples
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered: Optional[datetime] = None


class AlertManager:
    """Manages LLM performance alerts."""

    def __init__(self, admin_url: str):
        self.admin_url = admin_url
        self.client = httpx.AsyncClient(timeout=10.0)
        self.alert_configs: List[AlertConfig] = []
        self._running = False

    async def load_alert_configs(self):
        """Load alert configurations from Admin API."""
        try:
            response = await self.client.get(
                f"{self.admin_url}/api/llm-backends/alerts/configs"
            )
            response.raise_for_status()
            configs_data = response.json()

            self.alert_configs = [
                AlertConfig(
                    name=cfg["name"],
                    metric_type=cfg["metric_type"],
                    threshold_value=cfg["threshold_value"],
                    comparison=cfg["comparison_operator"],
                    model=cfg.get("model"),
                    time_window_minutes=cfg.get("time_window_minutes", 5),
                    min_samples=cfg.get("min_samples", 3),
                    cooldown_minutes=cfg.get("cooldown_minutes", 30)
                )
                for cfg in configs_data
                if cfg.get("enabled", True)
            ]

            logger.info(
                "alert_configs_loaded",
                count=len(self.alert_configs)
            )
        except Exception as e:
            logger.error("failed_to_load_alert_configs", error=str(e))

    async def check_alerts(self, metrics_data: Dict):
        """
        Check if any alert thresholds are exceeded.

        Args:
            metrics_data: Current metrics from LLM Router
        """
        for config in self.alert_configs:
            # Check cooldown
            if config.last_triggered:
                cooldown_until = config.last_triggered + timedelta(
                    minutes=config.cooldown_minutes
                )
                if datetime.utcnow() < cooldown_until:
                    continue

            # Check if alert should trigger
            should_trigger = self._evaluate_alert(config, metrics_data)

            if should_trigger:
                await self._trigger_alert(config, metrics_data)
                config.last_triggered = datetime.utcnow()

    def _evaluate_alert(self, config: AlertConfig, metrics_data: Dict) -> bool:
        """Evaluate if alert threshold is exceeded."""
        # Get relevant metrics
        if config.model:
            model_stats = metrics_data.get("by_model", {}).get(config.model)
            if not model_stats:
                return False

            if config.metric_type == "latency":
                value = model_stats.get("avg_latency_seconds", 0)
            elif config.metric_type == "tokens_per_sec":
                value = model_stats.get("avg_tokens_per_second", 0)
            else:
                return False

            requests = model_stats.get("requests", 0)
        else:
            # Overall metrics
            if config.metric_type == "latency":
                value = metrics_data.get("avg_latency_seconds", 0)
            elif config.metric_type == "tokens_per_sec":
                value = metrics_data.get("avg_tokens_per_second", 0)
            else:
                return False

            requests = metrics_data.get("total_requests", 0)

        # Check minimum samples
        if requests < config.min_samples:
            return False

        # Compare against threshold
        if config.comparison == "gt":
            return value > config.threshold_value
        elif config.comparison == "lt":
            return value < config.threshold_value
        elif config.comparison == "gte":
            return value >= config.threshold_value
        elif config.comparison == "lte":
            return value <= config.threshold_value

        return False

    async def _trigger_alert(self, config: AlertConfig, metrics_data: Dict):
        """Trigger an alert by notifying Admin API."""
        try:
            alert_data = {
                "config_name": config.name,
                "metric_type": config.metric_type,
                "threshold_value": config.threshold_value,
                "actual_value": self._get_metric_value(config, metrics_data),
                "model": config.model,
                "samples_count": self._get_samples_count(config, metrics_data)
            }

            response = await self.client.post(
                f"{self.admin_url}/api/llm-backends/alerts/trigger",
                json=alert_data
            )
            response.raise_for_status()

            logger.warning(
                "performance_alert_triggered",
                config_name=config.name,
                **alert_data
            )
        except Exception as e:
            logger.error("failed_to_trigger_alert", error=str(e))

    def _get_metric_value(self, config: AlertConfig, metrics_data: Dict) -> float:
        """Extract metric value for alert."""
        if config.model:
            model_stats = metrics_data.get("by_model", {}).get(config.model, {})
            if config.metric_type == "latency":
                return model_stats.get("avg_latency_seconds", 0)
            else:
                return model_stats.get("avg_tokens_per_second", 0)
        else:
            if config.metric_type == "latency":
                return metrics_data.get("avg_latency_seconds", 0)
            else:
                return metrics_data.get("avg_tokens_per_second", 0)

    def _get_samples_count(self, config: AlertConfig, metrics_data: Dict) -> int:
        """Get sample count for alert."""
        if config.model:
            model_stats = metrics_data.get("by_model", {}).get(config.model, {})
            return model_stats.get("requests", 0)
        else:
            return metrics_data.get("total_requests", 0)

    async def start(self):
        """Start alert monitoring loop."""
        self._running = True
        await self.load_alert_configs()

        while self._running:
            try:
                # Get current metrics from orchestrator
                response = await self.client.get(
                    f"{self.admin_url.replace('8080', '8001')}/llm-metrics"
                )
                response.raise_for_status()
                metrics_data = response.json()

                # Check alerts
                await self.check_alerts(metrics_data)

                # Wait before next check (30 seconds)
                await asyncio.sleep(30)

                # Reload configs every 5 minutes
                if datetime.utcnow().minute % 5 == 0:
                    await self.load_alert_configs()

            except Exception as e:
                logger.error("alert_check_error", error=str(e))
                await asyncio.sleep(30)

    async def stop(self):
        """Stop alert monitoring."""
        self._running = False
        await self.client.aclose()


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(admin_url: str = "http://localhost:8080") -> AlertManager:
    """Get or create alert manager singleton."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(admin_url=admin_url)
    return _alert_manager
```

#### Step 3: Integrate Alert Manager with Orchestrator

**File:** `src/orchestrator/main.py`

```python
from shared.alert_manager import get_alert_manager

# Add at startup
@app.on_event("startup")
async def startup():
    # ... existing startup code ...

    # Start alert manager
    alert_manager = get_alert_manager(
        admin_url=os.getenv("ADMIN_API_URL", "http://localhost:8080")
    )
    asyncio.create_task(alert_manager.start())
    logger.info("Alert manager started")
```

#### Step 4: Add Admin API Endpoints for Alerts

**File:** `admin/backend/app/routes/llm_backends.py`

```python
@router.get("/alerts/configs")
async def get_alert_configs(db: Session = Depends(get_db)):
    """Get all alert configurations."""
    configs = db.query(LLMAlertConfig).filter(
        LLMAlertConfig.enabled == True
    ).all()
    return configs


@router.post("/alerts/trigger")
async def trigger_alert(
    alert: dict,
    db: Session = Depends(get_db)
):
    """
    Triggered when an alert threshold is exceeded.

    Sends notifications via configured channels.
    """
    # Log alert
    logger.warning("alert_triggered", **alert)

    # TODO: Send notifications (email, Slack, webhook)
    # For now, just log it

    return {"status": "acknowledged"}


@router.post("/alerts/configs")
async def create_alert_config(
    config: dict,
    db: Session = Depends(get_db)
):
    """Create new alert configuration."""
    # Create alert config in database
    # ... implementation ...
    pass
```

#### Step 5: Add Alert Management UI

**File:** `admin/frontend/src/pages/AlertsConfig.tsx` (NEW)

```tsx
export default function AlertsConfig() {
  const [alerts, setAlerts] = useState([]);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Performance Alerts</h1>

      {/* Alert configurations list */}
      <div className="bg-white rounded shadow">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left">Name</th>
              <th className="px-6 py-3 text-left">Metric</th>
              <th className="px-6 py-3 text-left">Threshold</th>
              <th className="px-6 py-3 text-left">Model</th>
              <th className="px-6 py-3 text-left">Status</th>
              <th className="px-6 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {/* Alert rows */}
          </tbody>
        </table>
      </div>

      {/* Add new alert button */}
      <button className="mt-4 bg-blue-500 text-white px-4 py-2 rounded">
        + Add Alert
      </button>
    </div>
  );
}
```

### Example Alert Configurations

```json
[
  {
    "name": "High Latency - phi3:mini",
    "metric_type": "latency",
    "model": "phi3:mini",
    "threshold_value": 2.0,
    "comparison_operator": "gt",
    "time_window_minutes": 5,
    "min_samples": 5,
    "enabled": true
  },
  {
    "name": "Low Throughput - llama3.1:8b",
    "metric_type": "tokens_per_sec",
    "model": "llama3.1:8b",
    "threshold_value": 10.0,
    "comparison_operator": "lt",
    "time_window_minutes": 10,
    "min_samples": 3,
    "enabled": true
  },
  {
    "name": "Overall High Latency",
    "metric_type": "latency",
    "threshold_value": 3.0,
    "comparison_operator": "gt",
    "time_window_minutes": 5,
    "min_samples": 10,
    "enabled": true
  }
]
```

### Testing Steps

1. **Create test alert config:**
   ```bash
   curl -X POST http://localhost:8080/api/llm-backends/alerts/configs \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test High Latency",
       "metric_type": "latency",
       "threshold_value": 0.5,
       "comparison_operator": "gt",
       "time_window_minutes": 1,
       "min_samples": 1,
       "enabled": true
     }'
   ```

2. **Trigger alert by running slow query:**
   ```bash
   curl -X POST http://localhost:8001/query \
     -H "Content-Type: application/json" \
     -d '{"query": "Very complex query requiring deep reasoning...", "user_id": "test", "zone": "office"}'
   ```

3. **Verify alert triggered:**
   ```bash
   # Check orchestrator logs
   tail -f ~/dev/project-athena/orchestrator.log | grep alert_triggered
   ```

4. **Test cooldown:**
   - Run multiple queries within cooldown period
   - Verify alert only triggers once

### Success Criteria

- ✅ Alert configurations stored in database
- ✅ Alert manager loads configs on startup
- ✅ Alerts trigger when thresholds exceeded
- ✅ Cooldown prevents alert spam
- ✅ Alert history tracked in database
- ✅ Admin UI displays alert configurations
- ✅ Logs show alert triggers with details

---

## Implementation Timeline

**Total Estimated Time:** 8-12 hours

| Phase | Task | Estimated Time | Priority |
|-------|------|----------------|----------|
| 1 | Database persistence | 3-4 hours | High |
| 2 | Visualization dashboard | 4-5 hours | Medium |
| 3 | Alert system | 3-4 hours | Medium |

**Recommended Order:**
1. Start with Enhancement 1 (Persistence) - provides foundation
2. Add Enhancement 2 (Visualization) - requires persisted data
3. Implement Enhancement 3 (Alerts) - builds on both previous enhancements

## Dependencies

- **Database:** PostgreSQL (athena_admin)
- **Admin API:** FastAPI backend
- **Admin UI:** React frontend with recharts
- **Orchestrator:** Running with LLM Router metrics

## Success Metrics

After implementation, we should be able to:

1. **Track long-term trends:**
   - Compare model performance week-over-week
   - Identify performance regressions
   - Analyze usage patterns

2. **Visualize performance:**
   - Real-time dashboard showing current metrics
   - Historical charts for trend analysis
   - Per-model and per-backend comparisons

3. **Proactive alerting:**
   - Get notified when latency exceeds 2 seconds
   - Alert on throughput drops below 10 tokens/sec
   - Track alert history for pattern analysis

## Future Enhancements (Post-MVP)

- **Email/Slack notifications** for alerts
- **Anomaly detection** using statistical methods
- **Cost tracking** if using paid LLM backends
- **A/B testing** framework for model comparison
- **Predictive alerts** using ML models
- **Custom metric aggregations** (P50, P95, P99 latencies)
- **Export to Prometheus** for integration with Grafana

## References

- Sprint 1 Plan: `thoughts/shared/plans/2025-11-15-sprint-1-high-priority-gaps.md`
- LLM Router: `src/shared/llm_router.py`
- Orchestrator: `src/orchestrator/main.py`
- Admin Backend: `admin/backend/app/routes/llm_backends.py`
