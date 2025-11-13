# Admin Interface and RAG Services Deployment Plan
**Date:** 2025-11-13
**Author:** Assistant
**Status:** In Progress

## Overview
Deploy the admin interface for Project Athena with database-configured RAG services, allowing dynamic configuration of data sources without code changes.

## Current State
- ✅ Gateway and Orchestrator deployed on Mac Studio (192.168.10.167)
- ✅ Intent classification working with patterns from code
- ⏳ Database tables defined but not migrated
- ⏳ Admin interface built but not deployed
- ⏳ RAG services defined but not implemented

## Implementation Plan

### Phase 1: Database Migration and Setup
1. Create PostgreSQL databases (athena, athena_admin)
2. Run Alembic migrations for admin interface
3. Create intent configuration tables
4. Seed initial intent patterns and validation rules
5. Create RAG service configuration tables

### Phase 2: Deploy Admin Interface
1. Build admin backend (FastAPI + SQLAlchemy)
2. Build admin frontend (HTML/JS)
3. Deploy on Mac Studio port 8080
4. Configure authentication (basic auth initially)
5. Test admin CRUD operations

### Phase 3: Implement RAG Services
1. Create base RAG service framework
2. Implement configurable data sources:
   - Weather API (OpenWeatherMap or similar)
   - Sports API (TheSportsDB)
   - Airports/Flights API (AviationStack or similar)
3. Add admin UI for RAG configuration:
   - API endpoints
   - API keys
   - Cache TTL
   - Response templates
4. Integrate with orchestrator

### Phase 4: Admin-Configurable Features
1. Intent pattern management
2. Validation rule configuration
3. RAG service endpoint configuration
4. Response template editing
5. Real-time configuration updates via Redis pub/sub

## Technical Architecture

### Database Schema Extensions for RAG
```sql
-- RAG service configurations
CREATE TABLE rag_services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    service_type VARCHAR(50), -- 'api', 'database', 'file'
    endpoint_url TEXT,
    api_key_encrypted TEXT,
    headers JSONB,
    query_template TEXT,
    response_parser TEXT, -- JSON path or Python expression
    cache_ttl INTEGER DEFAULT 300,
    timeout INTEGER DEFAULT 5000,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RAG service parameters
CREATE TABLE rag_service_params (
    id SERIAL PRIMARY KEY,
    service_id INTEGER REFERENCES rag_services(id) ON DELETE CASCADE,
    param_name VARCHAR(50),
    param_type VARCHAR(20), -- 'query', 'header', 'path'
    default_value TEXT,
    required BOOLEAN DEFAULT false,
    description TEXT
);

-- RAG response templates
CREATE TABLE rag_response_templates (
    id SERIAL PRIMARY KEY,
    service_id INTEGER REFERENCES rag_services(id) ON DELETE CASCADE,
    intent_category VARCHAR(50),
    template_name VARCHAR(100),
    template_text TEXT,
    variables JSONB, -- Expected variables from API response
    enabled BOOLEAN DEFAULT true
);
```

### Admin Interface Components
1. **Dashboard**: Service health, request metrics
2. **Intent Configuration**: Pattern management, testing
3. **RAG Services**: Endpoint configuration, API key management
4. **Validation Rules**: Hallucination checks, response validation
5. **Response Templates**: Template editor with variable substitution
6. **Testing Console**: Live query testing with debug output

### RAG Service Implementation
```python
class ConfigurableRAGService:
    def __init__(self, db_pool, redis_client):
        self.db_pool = db_pool
        self.redis = redis_client
        self.services = {}

    async def load_configurations(self):
        """Load RAG service configs from database"""
        # Load service definitions
        # Set up API clients
        # Configure caching

    async def query(self, service_name: str, params: dict):
        """Query a RAG service with caching"""
        # Check cache
        # Make API call
        # Parse response
        # Apply template
        # Cache result
        # Return formatted response
```

## Success Criteria
1. Admin interface accessible at http://192.168.10.167:8080
2. All intent patterns manageable through UI
3. RAG services configurable without code changes
4. Real-time configuration updates working
5. Response times under 3 seconds for cached queries
6. Comprehensive logging and error handling

## Next Steps
1. Run database migrations
2. Deploy admin backend
3. Deploy admin frontend
4. Configure first RAG service (weather)
5. Test end-to-end flow