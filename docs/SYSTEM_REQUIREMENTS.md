# Project Athena - System Requirements Document

> **Document Version:** 1.0
> **Date:** November 15, 2025
> **Status:** Current Production System
> **Author:** Jay Stuart / Claude Code

## Executive Summary

**Project Athena** is an AI-powered query orchestration system designed to process natural language queries with intent-based routing, RAG (Retrieval-Augmented Generation) integration, and multi-backend LLM support. The system provides intelligent query understanding, contextual data retrieval, and synthesized responses through a modular, microservices architecture.

**Key Capabilities:**
- Natural language query processing
- Intent-based query routing
- Multi-source RAG data integration (Weather, Sports, Airports)
- Flexible LLM backend selection (Ollama, MLX, Auto-fallback)
- Admin UI for configuration management
- Performance tracking and optimization

---

## 1. System Architecture

### 1.1 Core Components

#### 1.1.1 Gateway Service
**Location:** `src/gateway/main.py`
**Port:** 8000
**Purpose:** Single entry point for all client queries

**Requirements:**
- **REQ-GW-001**: Accept HTTP POST requests at `/query` endpoint
- **REQ-GW-002**: Forward requests to Orchestrator service
- **REQ-GW-003**: Provide health check endpoint at `/health`
- **REQ-GW-004**: Handle timeout and error responses gracefully
- **REQ-GW-005**: Support CORS for cross-origin requests

**API Contract:**
```json
POST /query
{
  "query": "string",
  "mode": "owner|guest",
  "session_id": "optional_string"
}

Response:
{
  "answer": "string",
  "sources": ["array"],
  "intents": ["array"],
  "confidence": "float",
  "processing_time_ms": "integer"
}
```

#### 1.1.2 Orchestrator Service
**Location:** `src/orchestrator/main.py`
**Port:** 8001
**Purpose:** Core orchestration engine for query processing

**Requirements:**
- **REQ-ORCH-001**: Classify user intents from natural language queries
- **REQ-ORCH-002**: Support multi-intent queries (multiple simultaneous intents)
- **REQ-ORCH-003**: Route to appropriate RAG services based on classified intents
- **REQ-ORCH-004**: Aggregate results from multiple RAG sources
- **REQ-ORCH-005**: Synthesize final responses using LLM
- **REQ-ORCH-006**: Track session state and conversation history
- **REQ-ORCH-007**: Validate responses for factual accuracy
- **REQ-ORCH-008**: Handle parallel searches across multiple providers
- **REQ-ORCH-009**: Use LLMRouter for flexible backend selection
- **REQ-ORCH-010**: Support configurable model tiers (small, medium, large)
- **REQ-ORCH-011**: Provide structured logging for debugging
- **REQ-ORCH-012**: Cache frequently accessed data

**Supported Intents:**
- Weather queries
- Sports queries
- Airport/flight information
- General knowledge (web search)
- Home automation control
- Multi-intent combinations

#### 1.1.3 RAG Services

##### Weather RAG Service
**Location:** `src/rag/weather/main.py`
**Port:** 8010
**Purpose:** Weather data retrieval and formatting

**Requirements:**
- **REQ-RAG-WEATHER-001**: Fetch current weather for specified locations
- **REQ-RAG-WEATHER-002**: Fetch weather forecasts
- **REQ-RAG-WEATHER-003**: Return structured weather data (temperature, conditions, humidity, wind)
- **REQ-RAG-WEATHER-004**: Handle location parsing and geocoding
- **REQ-RAG-WEATHER-005**: Provide health check endpoint

**API Contract:**
```json
GET /weather/current?location=Baltimore,MD
Response:
{
  "location": "Baltimore, MD",
  "temperature": 72,
  "conditions": "Partly cloudy",
  "humidity": 65,
  "wind_speed": 10
}
```

##### Sports RAG Service
**Location:** `src/rag/sports/main.py`
**Port:** 8011
**Purpose:** Sports scores, schedules, and standings

**Requirements:**
- **REQ-RAG-SPORTS-001**: Fetch live scores for specified teams/leagues
- **REQ-RAG-SPORTS-002**: Fetch upcoming game schedules
- **REQ-RAG-SPORTS-003**: Fetch league standings
- **REQ-RAG-SPORTS-004**: Support multiple sports (NFL, NBA, MLB, NHL, etc.)
- **REQ-RAG-SPORTS-005**: Return structured sports data

##### Airports RAG Service
**Location:** `src/rag/airports/main.py`
**Port:** 8012
**Purpose:** Airport and flight information

**Requirements:**
- **REQ-RAG-AIRPORTS-001**: Fetch airport information by code or name
- **REQ-RAG-AIRPORTS-002**: Fetch flight status information
- **REQ-RAG-AIRPORTS-003**: Return structured airport/flight data

#### 1.1.4 LLM Router
**Location:** `src/shared/llm_router.py`
**Purpose:** Unified LLM backend routing and management

**Requirements:**
- **REQ-LLM-001**: Support multiple LLM backends (Ollama, MLX)
- **REQ-LLM-002**: Route requests based on per-model configuration
- **REQ-LLM-003**: Fetch backend configuration from Admin API
- **REQ-LLM-004**: Cache backend configurations (60-second TTL)
- **REQ-LLM-005**: Support automatic fallback (Auto mode: MLX → Ollama)
- **REQ-LLM-006**: Provide consistent API across all backends
- **REQ-LLM-007**: Log routing decisions and performance metrics
- **REQ-LLM-008**: Handle backend failures gracefully
- **REQ-LLM-009**: Support non-streaming responses
- **REQ-LLM-010**: Allow per-request temperature and max_tokens overrides

**Supported Backend Types:**
- `ollama` - Ollama server (GGUF models, Metal/CUDA GPU)
- `mlx` - MLX server (Apple Silicon optimized, 2-3x faster)
- `auto` - Try MLX first, fall back to Ollama on failure

#### 1.1.5 Admin Backend API
**Location:** `admin/backend/app/main.py`
**Port:** 8080 (when deployed to K8s)
**Purpose:** Configuration management and administration

**Requirements:**

**LLM Backend Management:**
- **REQ-ADMIN-LLM-001**: CRUD operations for LLM backend configurations
- **REQ-ADMIN-LLM-002**: List all backends with optional filtering (enabled_only)
- **REQ-ADMIN-LLM-003**: Get backend by ID
- **REQ-ADMIN-LLM-004**: Get backend by model name (service-to-service, no auth)
- **REQ-ADMIN-LLM-005**: Create new backend configurations
- **REQ-ADMIN-LLM-006**: Update existing backend configurations
- **REQ-ADMIN-LLM-007**: Delete backend configurations
- **REQ-ADMIN-LLM-008**: Toggle backend enabled/disabled status
- **REQ-ADMIN-LLM-009**: Track performance metrics (tokens/sec, latency, requests, errors)
- **REQ-ADMIN-LLM-010**: Validate backend_type (must be ollama, mlx, or auto)
- **REQ-ADMIN-LLM-011**: Require authentication for write operations
- **REQ-ADMIN-LLM-012**: Support partial updates (PUT with subset of fields)

**Authentication & Authorization:**
- **REQ-ADMIN-AUTH-001**: Support OIDC authentication
- **REQ-ADMIN-AUTH-002**: Permission-based access control (read, write)
- **REQ-ADMIN-AUTH-003**: User session management
- **REQ-ADMIN-AUTH-004**: API token generation and management

**Database:**
- **REQ-ADMIN-DB-001**: PostgreSQL database backend
- **REQ-ADMIN-DB-002**: Alembic migrations for schema management
- **REQ-ADMIN-DB-003**: Store llm_backends table with indexes
- **REQ-ADMIN-DB-004**: Store user accounts and permissions
- **REQ-ADMIN-DB-005**: Store configuration audit logs

#### 1.1.6 Admin Frontend UI
**Location:** `admin/frontend/`
**Purpose:** Web-based configuration interface

**Requirements:**
- **REQ-ADMIN-UI-001**: Dashboard showing system overview
- **REQ-ADMIN-UI-002**: LLM backend configuration interface
- **REQ-ADMIN-UI-003**: Create/edit/delete backend configurations
- **REQ-ADMIN-UI-004**: View performance metrics
- **REQ-ADMIN-UI-005**: Enable/disable backends via toggle
- **REQ-ADMIN-UI-006**: User authentication and session management
- **REQ-ADMIN-UI-007**: Responsive design for mobile/tablet/desktop

### 1.2 Supporting Components

#### 1.2.1 Intent Classifier
**Location:** `src/orchestrator/intent_classifier.py`

**Requirements:**
- **REQ-INTENT-001**: Parse natural language queries
- **REQ-INTENT-002**: Classify into supported intent categories
- **REQ-INTENT-003**: Support multi-intent queries
- **REQ-INTENT-004**: Return confidence scores for each intent
- **REQ-INTENT-005**: Use small LLM model for fast classification
- **REQ-INTENT-006**: Validate classified intents against known set
- **REQ-INTENT-007**: Handle ambiguous queries gracefully

#### 1.2.2 Search Providers
**Location:** `src/orchestrator/search_providers/`

**Requirements:**
- **REQ-SEARCH-001**: Support multiple search providers (Brave, etc.)
- **REQ-SEARCH-002**: Parallel search across multiple providers
- **REQ-SEARCH-003**: Result fusion and deduplication
- **REQ-SEARCH-004**: Provider routing based on query type
- **REQ-SEARCH-005**: Handle provider failures and timeouts

#### 1.2.3 Session Manager
**Location:** `src/orchestrator/session_manager.py`

**Requirements:**
- **REQ-SESSION-001**: Create and manage user sessions
- **REQ-SESSION-002**: Store conversation history per session
- **REQ-SESSION-003**: Support session expiration
- **REQ-SESSION-004**: Redis-backed session storage
- **REQ-SESSION-005**: Thread-safe session access

#### 1.2.4 Validator
**Location:** `src/orchestrator/validator.py`

**Requirements:**
- **REQ-VALID-001**: Validate LLM responses for factual accuracy
- **REQ-VALID-002**: Check responses against retrieved data
- **REQ-VALID-003**: Flag hallucinations or unsupported claims
- **REQ-VALID-004**: Return validation score

---

## 2. Data Models

### 2.1 LLM Backend Configuration

```python
class LLMBackend:
    id: int
    model_name: str              # e.g., "phi3:mini", "llama3.1:8b"
    backend_type: str            # "ollama", "mlx", "auto"
    endpoint_url: str            # Backend server URL
    enabled: bool                # Active/inactive flag
    priority: int                # Selection priority

    # Performance tracking
    avg_tokens_per_sec: float
    avg_latency_ms: float
    total_requests: int
    total_errors: int

    # Configuration
    max_tokens: int
    temperature_default: float
    timeout_seconds: int

    # Metadata
    description: str
    created_at: datetime
    updated_at: datetime
    created_by_id: int
```

### 2.2 Query Processing State

```python
class QueryState:
    query: str
    session_id: str
    mode: str                    # "owner" or "guest"

    # Intent classification
    intents: List[str]
    intent_confidence: Dict[str, float]

    # RAG results
    rag_results: Dict[str, Any]
    search_results: List[Dict]

    # LLM processing
    model_tier: str              # "small", "medium", "large"
    temperature: float
    answer: str

    # Validation
    validation_score: float
    validation_notes: List[str]

    # Performance
    processing_time_ms: int
    llm_time_ms: int
    rag_time_ms: int
```

---

## 3. Performance Requirements

### 3.1 Response Time Targets

- **REQ-PERF-001**: Total end-to-end query processing: < 10 seconds
- **REQ-PERF-002**: Intent classification: < 3 seconds
- **REQ-PERF-003**: RAG data retrieval: < 2 seconds per source
- **REQ-PERF-004**: LLM synthesis (with MLX): < 3 seconds
- **REQ-PERF-005**: LLM synthesis (with Ollama): < 7 seconds
- **REQ-PERF-006**: Admin API response time: < 100ms

### 3.2 LLM Backend Performance

| Model | Backend | Target Tokens/sec | Target Latency | Use Case |
|-------|---------|-------------------|----------------|----------|
| phi3:mini | Ollama (Metal) | 14-20 t/s | 5-7s | Intent classification |
| phi3:mini | MLX | 30-40 t/s | 2-3s | Fast intent classification |
| llama3.1:8b | Ollama | 6-8 t/s | 12-15s | Response synthesis |
| llama3.1:8b | MLX | 15-20 t/s | 5-6s | Fast response synthesis |

### 3.3 Scalability

- **REQ-SCALE-001**: Support 10 concurrent queries
- **REQ-SCALE-002**: Kubernetes horizontal pod autoscaling
- **REQ-SCALE-003**: Stateless service design for easy scaling
- **REQ-SCALE-004**: Redis for shared state across replicas

---

## 4. Security Requirements

### 4.1 Authentication

- **REQ-SEC-001**: OIDC-based authentication for Admin UI
- **REQ-SEC-002**: API token authentication for service-to-service calls
- **REQ-SEC-003**: Secure session management with httponly cookies
- **REQ-SEC-004**: Password hashing with bcrypt (if local auth enabled)

### 4.2 Authorization

- **REQ-SEC-005**: Role-based access control (read, write permissions)
- **REQ-SEC-006**: Service-to-service endpoints bypass auth (internal only)
- **REQ-SEC-007**: Audit logging for configuration changes

### 4.3 Network Security

- **REQ-SEC-008**: HTTPS for all external communications
- **REQ-SEC-009**: Internal services on private network only
- **REQ-SEC-010**: CORS configuration for allowed origins

### 4.4 Data Protection

- **REQ-SEC-011**: No PII stored in query logs
- **REQ-SEC-012**: Database credentials in Kubernetes secrets
- **REQ-SEC-013**: API tokens rotated regularly

---

## 5. Reliability Requirements

### 5.1 Availability

- **REQ-REL-001**: 99.5% uptime for core services
- **REQ-REL-002**: Graceful degradation when RAG sources unavailable
- **REQ-REL-003**: Automatic backend fallback (Auto mode)
- **REQ-REL-004**: Health check endpoints for all services

### 5.2 Fault Tolerance

- **REQ-REL-005**: Continue operation if single RAG source fails
- **REQ-REL-006**: Retry failed LLM requests with exponential backoff
- **REQ-REL-007**: Circuit breaker for failing backends
- **REQ-REL-008**: Timeout protection for all external calls

### 5.3 Data Integrity

- **REQ-REL-009**: Database migrations with rollback capability
- **REQ-REL-010**: Configuration backup and restore
- **REQ-REL-011**: Atomic database transactions for config changes

---

## 6. Monitoring and Observability

### 6.1 Logging

- **REQ-MON-001**: Structured logging with JSON format
- **REQ-MON-002**: Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **REQ-MON-003**: Request tracing with correlation IDs
- **REQ-MON-004**: Performance metrics in logs
- **REQ-MON-005**: Log routing decisions and backend selection

**Key Log Events:**
- Query received
- Intent classification result
- RAG service calls and responses
- LLM routing decisions
- LLM request completion
- Validation results
- Errors and exceptions

### 6.2 Metrics

- **REQ-MON-006**: Track request counts per endpoint
- **REQ-MON-007**: Track response times (p50, p95, p99)
- **REQ-MON-008**: Track LLM tokens/sec and latency
- **REQ-MON-009**: Track cache hit rates
- **REQ-MON-010**: Track error rates per service

### 6.3 Health Checks

- **REQ-MON-011**: `/health` endpoint on all services
- **REQ-MON-012**: Liveness probes for Kubernetes
- **REQ-MON-013**: Readiness probes for Kubernetes
- **REQ-MON-014**: Dependency health in composite checks

---

## 7. Deployment Requirements

### 7.1 Containerization

- **REQ-DEPLOY-001**: Docker containers for all services
- **REQ-DEPLOY-002**: Multi-stage builds for optimized images
- **REQ-DEPLOY-003**: Container registry: 192.168.10.222:30500
- **REQ-DEPLOY-004**: Image tagging: latest, semantic versions

### 7.2 Kubernetes Deployment

- **REQ-DEPLOY-005**: Deploy to thor cluster (192.168.10.222:6443)
- **REQ-DEPLOY-006**: Namespaces: athena, athena-admin
- **REQ-DEPLOY-007**: Replica count: 2 for orchestrator, 1 for others
- **REQ-DEPLOY-008**: Resource limits and requests defined
- **REQ-DEPLOY-009**: ConfigMaps for environment-specific config
- **REQ-DEPLOY-010**: Secrets for sensitive data
- **REQ-DEPLOY-011**: Service discovery via Kubernetes DNS
- **REQ-DEPLOY-012**: Ingress configuration for external access

### 7.3 LLM Backend Deployment

**Ollama:**
- **REQ-DEPLOY-LLM-001**: Ollama server on Mac Studio (192.168.10.167:11434)
- **REQ-DEPLOY-LLM-002**: Models pulled: phi3:mini, llama3.1:8b
- **REQ-DEPLOY-LLM-003**: Metal GPU acceleration enabled

**MLX (Optional):**
- **REQ-DEPLOY-LLM-004**: MLX server on Mac Studio (192.168.10.167:8080)
- **REQ-DEPLOY-LLM-005**: Models converted to MLX format
- **REQ-DEPLOY-LLM-006**: Launch agent for automatic startup

### 7.4 Database Deployment

- **REQ-DEPLOY-DB-001**: PostgreSQL 13+ (postgres-01.xmojo.net:5432)
- **REQ-DEPLOY-DB-002**: Database: athena
- **REQ-DEPLOY-DB-003**: Connection pooling enabled
- **REQ-DEPLOY-DB-004**: Automated backups daily

---

## 8. Configuration Management

### 8.1 Environment Variables

**Gateway:**
- `ORCHESTRATOR_URL`: Orchestrator service URL

**Orchestrator:**
- `ADMIN_API_URL`: Admin API URL
- `REDIS_URL`: Redis connection string
- `WEATHER_RAG_URL`: Weather RAG service URL
- `SPORTS_RAG_URL`: Sports RAG service URL
- `AIRPORTS_RAG_URL`: Airports RAG service URL

**Admin Backend:**
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET`: JWT signing secret
- `OIDC_CLIENT_ID`: OIDC client ID
- `OIDC_CLIENT_SECRET`: OIDC client secret

**LLM Router:**
- `ADMIN_API_URL`: Admin API URL for config fetching

### 8.2 Configuration Files

- **REQ-CONFIG-001**: All config in environment variables or Admin DB
- **REQ-CONFIG-002**: No hardcoded URLs or credentials
- **REQ-CONFIG-003**: Configuration hot-reload (via cache expiry)
- **REQ-CONFIG-004**: Default values for all optional config

---

## 9. Testing Requirements

### 9.1 Unit Testing

- **REQ-TEST-001**: 80% code coverage for core logic
- **REQ-TEST-002**: pytest for Python services
- **REQ-TEST-003**: Mock external dependencies
- **REQ-TEST-004**: Test intent classification accuracy

### 9.2 Integration Testing

- **REQ-TEST-005**: End-to-end query processing tests
- **REQ-TEST-006**: Test multi-intent queries
- **REQ-TEST-007**: Test RAG service integration
- **REQ-TEST-008**: Test LLM backend routing
- **REQ-TEST-009**: Test Auto fallback behavior

### 9.3 Performance Testing

- **REQ-TEST-010**: Benchmark LLM backends (Ollama vs MLX)
- **REQ-TEST-011**: Load testing for concurrent queries
- **REQ-TEST-012**: Latency testing for all endpoints

---

## 10. Documentation Requirements

- **REQ-DOC-001**: API documentation for all endpoints
- **REQ-DOC-002**: Deployment guide
- **REQ-DOC-003**: Configuration guide
- **REQ-DOC-004**: Architecture documentation
- **REQ-DOC-005**: Troubleshooting guide
- **REQ-DOC-006**: Wiki.js integration for public docs

---

## 11. Operational Requirements

### 11.1 Backup and Recovery

- **REQ-OPS-001**: Daily PostgreSQL backups
- **REQ-OPS-002**: Configuration export/import capability
- **REQ-OPS-003**: Disaster recovery procedure documented
- **REQ-OPS-004**: Backup retention: 30 days

### 11.2 Maintenance

- **REQ-OPS-005**: Rolling updates with zero downtime
- **REQ-OPS-006**: Database migration procedure
- **REQ-OPS-007**: Model update procedure
- **REQ-OPS-008**: Configuration audit trail

### 11.3 Monitoring Alerts

- **REQ-OPS-009**: Alert on service failures
- **REQ-OPS-010**: Alert on high error rates
- **REQ-OPS-011**: Alert on response time degradation
- **REQ-OPS-012**: Alert on database connection failures

---

## 12. Future Enhancements (Planned)

### 12.1 Streaming Support

- **REQ-FUTURE-001**: Streaming LLM responses for real-time UX
- **REQ-FUTURE-002**: WebSocket support for streaming

### 12.2 Advanced RAG

- **REQ-FUTURE-003**: Vector database integration (Qdrant)
- **REQ-FUTURE-004**: Document ingestion and indexing
- **REQ-FUTURE-005**: Semantic search across documents

### 12.3 Multi-User Support

- **REQ-FUTURE-006**: User-specific conversation history
- **REQ-FUTURE-007**: User preferences and settings
- **REQ-FUTURE-008**: Multi-tenant architecture

### 12.4 Enhanced Monitoring

- **REQ-FUTURE-009**: Grafana dashboards
- **REQ-FUTURE-010**: Prometheus metrics collection
- **REQ-FUTURE-011**: Distributed tracing with Jaeger

---

## 13. Success Criteria

### 13.1 Functionality

- ✅ All core services deployed and running
- ✅ Intent classification working with 90%+ accuracy
- ✅ Multi-intent queries supported
- ✅ RAG services integrated (Weather, Sports, Airports)
- ✅ LLM backend routing operational (Ollama, MLX, Auto)
- ✅ Admin UI deployed and functional
- ✅ End-to-end query processing complete

### 13.2 Performance

- ✅ Average query response time < 10s
- ✅ MLX backend 2-3x faster than Ollama
- ✅ Admin API response time < 100ms
- ✅ 10 concurrent queries supported

### 13.3 Reliability

- ✅ No single point of failure
- ✅ Automatic backend fallback working
- ✅ Health checks passing for all services
- ✅ Graceful degradation when RAG sources fail

---

## Appendix A: Technology Stack

**Backend Services:**
- Python 3.9+
- FastAPI
- SQLAlchemy
- Alembic
- httpx
- structlog

**Frontend:**
- React
- TypeScript
- Tailwind CSS

**LLM Backends:**
- Ollama (GGUF models)
- MLX (Apple Silicon)

**Infrastructure:**
- Kubernetes (thor cluster)
- PostgreSQL 13+
- Redis
- Docker

**Deployment:**
- kubectl
- Docker Compose
- Helm (future)

**Monitoring:**
- Structured logging (JSON)
- Kubernetes health probes
- Custom metrics (future: Prometheus)

---

## Appendix B: Glossary

- **RAG**: Retrieval-Augmented Generation
- **LLM**: Large Language Model
- **GGUF**: GPT-Generated Unified Format (Ollama model format)
- **MLX**: Apple's machine learning framework for Metal GPU
- **OIDC**: OpenID Connect (authentication protocol)
- **TTL**: Time To Live (cache expiration)
- **K8s**: Kubernetes
- **CRUD**: Create, Read, Update, Delete

---

**Document Status:** Complete
**Last Updated:** November 15, 2025
**Version:** 1.0
**Maintained By:** Jay Stuart
