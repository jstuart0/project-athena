# Project Athena Deployment Architecture
**Date:** 2025-11-13
**Author:** Assistant
**Status:** Active Implementation

## Overview
This document captures the actual deployment architecture for Project Athena, clarifying where each component runs and how they interact.

## Deployment Topology

### Mac Studio (192.168.10.167)
**Primary compute node for AI services**

**Running Services:**
- **Gateway** (Port 8000): OpenAI-compatible API endpoint
- **Orchestrator** (Port 8001): LangGraph state machine for query processing
- **Ollama** (Port 11434): LLM inference service
- **RAG Services** (Ports 8010-8017): Domain-specific data retrieval
  - Weather (8010)
  - Airports (8011)
  - Sports (8012)
  - Events (8013)
  - Streaming (8014)
  - News (8015)
  - Stocks (8016)
  - Additional services as configured

**Key Characteristics:**
- 64GB RAM for LLM inference
- Direct access to Ollama for fast inference
- Python services running as processes (not containerized)
- Services managed via SSH and systemd/nohup

### Mac mini (192.168.10.181)
**Cache and vector storage node**

**Running Services:**
- **Redis** (Port 6379): Caching layer for all services
- **Qdrant** (Port 6333): Vector database for RAG
- *Both services run in Docker containers*

### Thor Kubernetes Cluster (192.168.10.222)
**Production infrastructure hosting**

**Deployed Services:**
- **Admin Interface** (Namespace: athena-admin)
  - Backend API for configuration management
  - Frontend UI for monitoring and control
  - Accessible via Ingress/LoadBalancer
- **Other infrastructure services** (as needed)

**Important:** The admin interface is NOT deployed on Mac Studio - it runs on the Kubernetes cluster for proper production deployment, scaling, and management.

### PostgreSQL Database (postgres-01.xmojo.net / 192.168.10.30)
**Central database for all configuration and state**

**Databases:**
- `athena`: Main application database
  - Intent categories and patterns
  - RAG service configurations
  - Validation rules
  - Multi-intent configurations
  - Query logs
- `athena_admin`: Admin interface database
  - User management
  - Session management
  - Audit logs

**Access Credentials:**
- User: `psadmin`
- Password: `Ibucej1!`
- Port: 5432

## Service Communication Flow

```mermaid
graph TD
    HA[Home Assistant<br/>192.168.10.168] -->|API Calls| GW[Gateway<br/>Mac Studio:8000]
    Client[Client Apps] -->|OpenAI API| GW

    GW -->|Query| ORCH[Orchestrator<br/>Mac Studio:8001]

    ORCH -->|Intent Query| DB[(PostgreSQL<br/>postgres-01.xmojo.net)]
    ORCH -->|LLM Inference| OLLAMA[Ollama<br/>Mac Studio:11434]
    ORCH -->|Cache| REDIS[Redis<br/>Mac mini:6379]
    ORCH -->|RAG Query| RAG[RAG Services<br/>Mac Studio:8010-8017]

    RAG -->|Config| DB
    RAG -->|Cache| REDIS
    RAG -->|Vectors| QDRANT[Qdrant<br/>Mac mini:6333]

    ADMIN[Admin Interface<br/>Thor K8s] -->|Config Updates| DB
    ADMIN -->|Monitor| ORCH
    ADMIN -->|Monitor| RAG
```

## Configuration Management

### Database-Driven Configuration
All service configurations are stored in PostgreSQL and loaded dynamically:

1. **Intent Patterns**: Loaded by orchestrator at startup and refreshed periodically
2. **RAG Service Endpoints**: API URLs, keys, and templates stored in database
3. **Validation Rules**: Anti-hallucination and response validation rules
4. **Multi-Intent Config**: Query splitting and chaining rules

### Admin Interface (on Thor)
The admin interface provides:
- Web UI for managing all configurations
- Real-time monitoring of service health
- Query analytics and performance metrics
- User management and access control

### Configuration Updates
1. Admin makes changes via Thor-hosted admin interface
2. Changes written to PostgreSQL (postgres-01.xmojo.net)
3. Services on Mac Studio poll database for updates (5-minute refresh)
4. Redis pub/sub can trigger immediate refresh when needed

## Deployment Procedures

### Mac Studio Services
```bash
# Deploy/restart services
ssh jstuart@192.168.10.167
cd ~/dev/project-athena

# Start orchestrator
export DATABASE_URL="postgresql://psadmin:Ibucej1!@postgres-01.xmojo.net:5432/athena"
export REDIS_URL="redis://192.168.10.181:6379"
nohup python3 -m uvicorn src/orchestrator/main:app --host 0.0.0.0 --port 8001 &

# Start gateway
export ORCHESTRATOR_SERVICE_URL="http://localhost:8001"
nohup python3 -m uvicorn src/gateway/main:app --host 0.0.0.0 --port 8000 &

# Start RAG services
for port in {8010..8017}; do
    nohup python3 -m uvicorn src/rag/service:app --host 0.0.0.0 --port $port &
done
```

### Admin Interface (on Thor)
```bash
# Access from machine with kubectl configured
kubectl config use-context thor

# Check deployment
kubectl get pods -n athena-admin

# View logs
kubectl logs -n athena-admin deployment/admin-backend

# Access via ingress
# URL: https://admin.athena.xmojo.net (example)
```

### Database Migrations
```bash
# Run from Mac Studio (has network access to postgres-01)
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
python3 scripts/run_migrations.py
```

## Security Considerations

1. **Network Isolation**
   - Services on Mac Studio only accessible within local network
   - Admin interface on Thor has proper ingress/authentication
   - Database requires authentication for all connections

2. **Credential Management**
   - Database passwords stored in environment variables
   - API keys encrypted in database
   - Admin interface uses session-based auth

3. **Access Control**
   - SSH key-based access to Mac Studio
   - Kubernetes RBAC for admin interface
   - Database user permissions properly scoped

## Monitoring and Health

### Health Endpoints
- Gateway: `http://192.168.10.167:8000/health`
- Orchestrator: `http://192.168.10.167:8001/health`
- RAG Services: `http://192.168.10.167:{port}/health`
- Admin: Via Kubernetes probes

### Logging
- Mac Studio services: Local file logs with rotation
- Admin interface: Kubernetes logging (kubectl logs)
- Database: PostgreSQL logs on postgres-01

### Metrics
- Response times tracked in query_logs table
- Service health status updated in rag_services table
- Prometheus metrics exposed by services (future)

## Backup and Recovery

1. **Database**: Regular PostgreSQL backups on postgres-01
2. **Configuration**: All config in database (backed up)
3. **Code**: Git repository (version controlled)
4. **Models**: Stored on Mac Studio, should be backed up separately

## Future Enhancements

1. **Service Mesh**: Consider Istio for service communication
2. **Observability**: Full Prometheus + Grafana stack
3. **High Availability**: Multiple Mac Studios for redundancy
4. **Auto-scaling**: Kubernetes HPA for admin interface
5. **GitOps**: ArgoCD for declarative deployments