# Implementation Plan: Conversation Context Management & Clarifying Questions

**Date:** 2025-11-14
**Status:** Planning
**Priority:** High
**Estimated Effort:** 3-5 days

## Executive Summary

This plan adds comprehensive conversation context management and clarifying question capabilities to Project Athena, based on requirements from the original deprecated Athena project. These features enable multi-turn conversations, follow-up questions, and intelligent disambiguation.

## Background

### Original System Requirements

From `thoughts/shared/research/2025-01-07-comprehensive-voice-assistant-analysis.md`:

**Conversation Context Management:**
- Session tracking by client IP address
- 20-message conversation history (configurable)
- 30-minute inactivity expiry
- Background cleanup every 60 seconds
- Redis storage with 1-hour TTL
- Format: "Previous conversation:\nUser: ...\nAssistant: ..."

**Clarifying Questions:**
- Sports team disambiguation (4 ambiguous teams: Giants, Cardinals, Panthers, Spurs)
- General ambiguity detection
- User confirmation for uncertain intents

### Current System Status

**Already Implemented:**
1. **Basic conversation caching** (`src/orchestrator/main.py:734-744`)
   - Caches single query/response pairs
   - 1-hour TTL
   - NOT linked across queries

2. **Sports disambiguation** (`thoughts/shared/research/2025-11-07-sports-disambiguation-bug-fix.md`)
   - 4 ambiguous teams handled
   - Sport context detection
   - Clarification message generation

3. **Context preservation in multi-intent** (`src/orchestrator/intent_classifier.py:437-467`)
   - Only within compound queries
   - Subject carryover ("turn on lights and kitchen")
   - NOT across separate queries

**Gaps to Address:**
1. No session management - each query is isolated
2. No conversation history tracking across multiple queries
3. No follow-up question resolution ("What about tomorrow?")
4. No pronoun resolution ("Tell me more about it")
5. Limited clarifying question system (only sports)
6. No general ambiguity detection

## Goals

### Primary Goals

1. **Enable multi-turn conversations**
   - User: "What's the weather?"
   - Athena: "It's 72°F and sunny in San Francisco"
   - User: "What about tomorrow?" ← Resolves to "weather tomorrow"

2. **Add intelligent clarifying questions**
   - User: "Turn on the lights"
   - Athena: "Which lights? Living room, bedroom, or all lights?"
   - User: "Living room"

3. **Preserve conversation context**
   - Track 20-message history per session
   - 30-minute inactivity expiry
   - Seamless follow-up handling

### Secondary Goals

4. **Pronoun resolution**
   - User: "Tell me about the Giants"
   - Athena: "Which Giants? New York Giants (NFL) or San Francisco Giants (MLB)?"
   - User: "Tell me their schedule" ← Resolves to previously clarified team

5. **Entity carryover**
   - User: "What's the weather in Seattle?"
   - Athena: "It's 65°F and rainy"
   - User: "Set a reminder for tomorrow" ← "tomorrow" infers Seattle timezone

## Architecture

### Session Management

```python
# Session identifier
session_id = hash(client_ip + user_agent)  # More robust than IP alone

# Session schema (Redis)
{
    "session:<session_id>": {
        "messages": [
            {"role": "user", "content": "What's the weather?", "timestamp": 1699900000},
            {"role": "assistant", "content": "72°F sunny", "timestamp": 1699900001},
            # ... up to 20 messages
        ],
        "context": {
            "last_intent": "weather",
            "last_entities": {"location": "San Francisco"},
            "pending_clarification": None,
            "disambiguation_options": []
        },
        "last_activity": 1699900001,
        "created_at": 1699900000
    }
}
```

### Context Manager Service

New service: `src/orchestrator/context_manager.py`

**Responsibilities:**
1. Session lifecycle management
2. Conversation history tracking
3. Context extraction and enrichment
4. Follow-up question detection
5. Entity resolution across queries

**Key Methods:**
```python
class ContextManager:
    async def get_session(self, session_id: str) -> Session
    async def add_message(self, session_id: str, role: str, content: str)
    async def get_conversation_history(self, session_id: str) -> List[Message]
    async def resolve_followup(self, session_id: str, query: str) -> str
    async def extract_entities(self, session_id: str) -> Dict[str, Any]
    async def cleanup_expired_sessions(self)  # Background task
```

### Clarification System

Enhanced service: `src/orchestrator/clarification.py`

**Responsibilities:**
1. Ambiguity detection
2. Clarification question generation
3. User response mapping
4. Context-aware disambiguation

**Clarification Types:**

1. **Sports Team Disambiguation** (already exists)
   - Giants, Cardinals, Panthers, Spurs
   - Sport context detection

2. **Device Disambiguation** (NEW)
   - User: "Turn on the lights"
   - Multiple light entities exist
   - Athena: "Which lights? Living room, bedroom, kitchen, or all?"

3. **Location Disambiguation** (NEW)
   - User: "What's the weather?"
   - No location specified, no previous context
   - Athena: "Which location? San Francisco (default), or another city?"

4. **Time Disambiguation** (NEW)
   - User: "Set a timer"
   - No duration specified
   - Athena: "How long? 5 minutes, 10 minutes, or custom duration?"

**Clarification Schema:**
```python
{
    "pending_clarification": {
        "type": "device_disambiguation",
        "original_query": "turn on the lights",
        "options": [
            {"id": "light.living_room", "label": "Living room lights"},
            {"id": "light.bedroom", "label": "Bedroom lights"},
            {"id": "all", "label": "All lights"}
        ],
        "created_at": 1699900000,
        "expires_at": 1699900300  # 5 minutes
    }
}
```

## Implementation Plan

### Phase 0: Admin Panel Database & API (Day 1)

**Tasks:**

1. **Create database migration**
   - Add conversation_settings table
   - Add clarification_settings table
   - Add clarification_types table
   - Add sports_team_disambiguation table
   - Add device_disambiguation_rules table
   - Add conversation_analytics table
   - Insert default values

2. **Create Admin Panel API routes**
   - `admin/backend/routes/conversation.py`
   - Conversation settings CRUD endpoints
   - Clarification settings endpoints
   - Sports team disambiguation CRUD
   - Analytics endpoints
   - Export/import configuration

3. **Create config loader for orchestrator**
   - `src/orchestrator/config_loader.py`
   - Load settings from PostgreSQL
   - Cache in Redis (5-minute TTL)
   - Handle cache invalidation

**Deliverables:**
- `admin/backend/migrations/007_conversation_settings.sql` (150 lines)
- `admin/backend/routes/conversation.py` (400 lines)
- `admin/backend/models/conversation.py` (200 lines)
- `src/orchestrator/config_loader.py` (150 lines)

**Testing:**
```bash
# Apply migration
psql -h localhost -U athena_admin -d athena_admin < migrations/007_conversation_settings.sql

# Test API endpoints
curl http://localhost:8080/api/conversation/settings
curl http://localhost:8080/api/clarification/types

# Verify default data
psql -h localhost -U athena_admin -d athena_admin -c "SELECT * FROM conversation_settings;"
```

### Phase 1: Session Management Foundation (Day 2)

**Tasks:**

1. **Create `context_manager.py`**
   - Session schema definition
   - Redis client integration
   - Session CRUD operations
   - Background cleanup task
   - Load config from Admin Panel database

2. **Update `main.py` orchestrator**
   - Extract session ID from request headers
   - Initialize ContextManager with ConfigLoader
   - Add session tracking to request flow

3. **Add session middleware**
   - Generate/validate session IDs
   - Inject session context into state
   - Handle session expiry

4. **Create Admin Panel frontend components**
   - `ConversationSettings.tsx` - Settings page (basic version)
   - API integration for fetching/updating settings

**Deliverables:**
- `src/orchestrator/context_manager.py` (250 lines - includes config loading)
- `src/orchestrator/middleware/session.py` (100 lines)
- Updated `src/orchestrator/main.py` (50 lines changed)
- `admin/frontend/src/components/conversation/ConversationSettings.tsx` (200 lines)

**Testing:**
```bash
# Test session creation
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"query": "What'\''s the weather?", "mode": "jarvis"}'

# Verify session in Redis
redis-cli -h localhost GET "session:<session_id>"

# Test config loading from database
curl http://localhost:8001/config/conversation

# Test admin panel settings page
# Navigate to http://localhost:3000/conversation/settings
# Toggle settings, verify changes persist
```

### Phase 2: Conversation History (Day 3)

**Tasks:**

1. **Implement conversation history tracking**
   - Add messages to session on each query/response
   - Enforce configurable message limit (loaded from Admin Panel)
   - Format history for LLM context

2. **Update LLM prompt construction**
   - Inject conversation history into system prompt
   - Format: "Previous conversation:\nUser: ...\nAssistant: ..."
   - Use max_llm_history_messages from config

3. **Add context extraction**
   - Extract intent from last query
   - Extract entities (location, time, device)
   - Store in session context

4. **Add analytics tracking**
   - Log session events to conversation_analytics table
   - Track session_created, message_added, context_resolved
   - Batch insert for performance

5. **Create monitoring frontend component**
   - `ConversationMonitor.tsx` - Live session monitoring
   - Display active sessions
   - Show recent events
   - Real-time WebSocket updates

**Deliverables:**
- Enhanced `context_manager.py` (+200 lines)
- Updated `src/command/llm_handler.py` (100 lines changed)
- `src/orchestrator/analytics_tracker.py` (150 lines)
- `admin/frontend/src/components/conversation/ConversationMonitor.tsx` (300 lines)
- WebSocket endpoint in admin backend

**Testing:**
```python
# Test conversation flow
user_query_1 = "What's the weather in Seattle?"
# Verify: Response includes Seattle weather
# Verify: Analytics event logged

user_query_2 = "What about tomorrow?"
# Verify: System resolves "Seattle" from context
# Verify: System resolves "tomorrow" as next day
# Verify: Context resolution event logged

user_query_3 = "And the day after?"
# Verify: Multi-turn context preservation

# Test admin panel monitoring
# Navigate to http://localhost:3000/conversation/monitor
# Verify: Active sessions displayed
# Verify: Events update in real-time
```

### Phase 3: Follow-Up Question Resolution (Day 4)

**Tasks:**

1. **Implement follow-up detection**
   - Pattern matching for follow-up indicators
     - "what about...", "and...", "also...", "tell me more"
   - Pronoun detection ("it", "that", "them")
   - Relative time references ("tomorrow", "next week", "in 2 hours")

2. **Create query expansion logic**
   - Resolve pronouns to last entities
   - Expand relative queries with context
   - Example: "What about tomorrow?" → "What's the weather in Seattle tomorrow?"

3. **Integrate with intent classifier**
   - Pass expanded query to intent classifier
   - Preserve original query for response generation
   - Update conversation history with both

4. **Track followup analytics**
   - Log followup_detected events
   - Track resolution success/failure
   - Store expanded query for analysis

5. **Create analytics dashboard**
   - `ConversationAnalytics.tsx` - Charts and metrics
   - Follow-up detection rate
   - Context resolution success rate
   - Top intents over time
   - Session statistics

**Deliverables:**
- `src/orchestrator/followup_resolver.py` (250 lines)
- Integration with intent classifier (50 lines changed)
- Pattern matching rules
- Enhanced analytics tracking (50 lines)
- `admin/frontend/src/components/conversation/ConversationAnalytics.tsx` (400 lines)

**Testing:**
```python
# Test pronoun resolution
user_query_1 = "Tell me about the Warriors"
# Response: Warriors team info
# Verify: Analytics logged

user_query_2 = "What's their next game?"
# Verify: "their" resolves to "Warriors"
# Verify: Intent = sports_schedule
# Verify: followup_detected event logged

# Test relative time
user_query_1 = "What's the weather?"
# Response: Current weather

user_query_2 = "What about tomorrow?"
# Verify: Resolves to "weather tomorrow"
# Verify: Returns tomorrow's forecast

# Test location carryover
user_query_1 = "Weather in Portland?"
# Response: Portland weather

user_query_2 = "What about the traffic?"
# Verify: "traffic in Portland" (location carryover)

# Test admin panel analytics
# Navigate to http://localhost:3000/conversation/analytics
# Verify: Follow-up detection rate shown
# Verify: Charts render correctly
```

### Phase 4: Clarifying Questions System (Day 5)

**Tasks:**

1. **Create `clarification.py` service**
   - Load clarification types from Admin Panel database
   - Ambiguity detection for configured types
   - Clarification question generation
   - Response mapping to original query
   - Priority-based type checking

2. **Implement device disambiguation**
   - Detect "lights" query with multiple entities
   - Query Home Assistant for available lights
   - Generate clarification with options
   - Store pending clarification in session
   - Respect device_disambiguation_rules from DB

3. **Implement sports team disambiguation**
   - Load sports_team_disambiguation rules from DB
   - Check team name against configured rules
   - Generate clarification question
   - Map user response to team ID

4. **Implement general disambiguation**
   - Location disambiguation (no context)
   - Time disambiguation (timers, reminders)
   - Generic "which one?" handling

5. **Add clarification response handling**
   - Detect user clarification response
   - Map response to original intent
   - Execute resolved query
   - Clear pending clarification
   - Log clarification analytics

6. **Create clarification management UI**
   - `ClarificationManager.tsx` - Types management
   - `SportsTeamDisambiguation.tsx` - Sports rules editor
   - Enable/disable types
   - Edit timeouts and priorities
   - Add/edit/delete sports team rules

**Deliverables:**
- `src/orchestrator/clarification.py` (500 lines - includes DB integration)
- Home Assistant entity query integration (100 lines)
- Clarification templates (100 lines)
- `admin/frontend/src/components/conversation/ClarificationManager.tsx` (300 lines)
- `admin/frontend/src/components/conversation/SportsTeamDisambiguation.tsx` (400 lines)

**Schema Example:**
```python
# Pending clarification stored in session
{
    "pending_clarification": {
        "type": "device_disambiguation",
        "original_query": "turn on the lights",
        "original_intent": "home_assistant_control",
        "options": [
            {"id": "light.living_room", "label": "Living room"},
            {"id": "light.bedroom", "label": "Bedroom"},
            {"id": "light.kitchen", "label": "Kitchen"},
            {"id": "all", "label": "All lights"}
        ],
        "created_at": 1699900000,
        "expires_at": 1699900300
    }
}

# User response: "living room"
# System maps "living room" → "light.living_room"
# Executes: turn_on(entity_id="light.living_room")
```

**Testing:**
```python
# Test device disambiguation
user_query = "Turn on the lights"
# Verify: Clarification question generated
# Response: "Which lights? Living room, bedroom, kitchen, or all?"
# Verify: clarification_triggered event logged

user_response = "living room"
# Verify: Mapped to correct entity
# Verify: HA command executed
# Verify: Clarification cleared from session
# Verify: clarification_resolved event logged

# Test sports team disambiguation
user_query = "Tell me about the Giants"
# Verify: Loads rules from sports_team_disambiguation table
# Response: "Which Giants? NY Giants (NFL) or SF Giants (MLB)?"

user_response = "SF"
# Verify: Mapped to sf-giants
# Verify: Correct team info returned

# Test location disambiguation
user_query = "What's the weather?"
# If no location context exists
# Response: "Which location? San Francisco (default), or specify a city"

user_response = "Seattle"
# Verify: Weather for Seattle returned
# Verify: Location stored in context for follow-ups

# Test admin panel clarification management
# Navigate to http://localhost:3000/conversation/clarification
# Toggle device clarification on/off
# Verify: Changes reflected in next query

# Navigate to http://localhost:3000/conversation/sports-teams
# Add new sports team "Rangers" with NHL/MLB options
# Test query with "Rangers"
# Verify: Clarification triggered
```

### Phase 5: Integration, Testing & Documentation (Day 6-7)

**Tasks:**

1. **End-to-end integration**
   - Connect all components
   - Update orchestrator flow
   - Add error handling
   - Graceful degradation if DB unavailable

2. **Performance optimization**
   - Redis connection pooling
   - Session cleanup optimization
   - Context extraction caching
   - Database query optimization (indexes)

3. **Configuration export/import**
   - Export endpoint (`/api/conversation/export`)
   - Import endpoint with validation (`/api/conversation/import`)
   - Preset configurations (minimal, standard, advanced)
   - Export/import UI in admin panel

4. **Comprehensive testing**
   - Multi-turn conversation scenarios
   - Clarification flow testing
   - Session expiry testing
   - Concurrent session handling
   - Admin panel end-to-end tests

5. **Documentation**
   - Update ARCHITECTURE.md (conversation architecture)
   - Create `docs/CONVERSATION_SETUP.md` (step-by-step guide)
   - Create `docs/CLARIFICATION_RULES.md` (custom rules guide)
   - Create `docs/DEPLOYMENT_SIZES.md` (sizing guide)
   - Add conversation flow diagrams
   - Document clarification types
   - Add troubleshooting guide
   - Create `examples/conversation-configs/` with presets

6. **Community preparation**
   - Create example configurations (Pi4, NUC, Cluster)
   - Remove hardcoded personal references
   - Add contribution guidelines
   - Document open source roadmap

**Deliverables:**
- Complete integration
- Test suite (200+ test cases)
- Updated documentation (5 new docs)
- Performance benchmarks
- Export/import functionality
- Example configurations (3 presets)
- Community documentation

**Test Scenarios:**

```python
# Scenario 1: Multi-turn weather
user_1 = "What's the weather?"
# → "72°F sunny in San Francisco" (default location)

user_2 = "What about Seattle?"
# → "65°F rainy in Seattle"

user_3 = "And tomorrow?"
# → "Tomorrow in Seattle: 63°F cloudy"

user_4 = "Back to San Francisco"
# → "San Francisco: 72°F sunny"

# Scenario 2: Device disambiguation with follow-up
user_1 = "Turn on the lights"
# → "Which lights? Living room, bedroom, kitchen, or all?"

user_2 = "living room"
# → "Living room lights turned on"

user_3 = "Now turn them off"
# → "Living room lights turned off" (pronoun resolution)

# Scenario 3: Sports with clarification
user_1 = "Tell me about the Giants"
# → "Which Giants? NY Giants (NFL) or SF Giants (MLB)?"

user_2 = "SF"
# → "San Francisco Giants info..."

user_3 = "What's their next game?"
# → "Giants next game: ..." (context preserved)

# Scenario 4: Session expiry
user_1 = "What's the weather?"
# → "72°F sunny"

# Wait 31 minutes (session expires)

user_2 = "What about tomorrow?"
# → Should NOT have context, treat as new query
# → "Tomorrow in San Francisco: ..." (uses default location)
```

## Data Structures

### Session Model

```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None

class PendingClarification(BaseModel):
    type: str  # "device", "location", "time", "sports_team"
    original_query: str
    original_intent: str
    options: List[Dict[str, str]]
    created_at: float
    expires_at: float

class SessionContext(BaseModel):
    last_intent: Optional[str] = None
    last_entities: Optional[Dict[str, Any]] = None
    pending_clarification: Optional[PendingClarification] = None

class Session(BaseModel):
    session_id: str
    messages: List[Message] = []
    context: SessionContext = SessionContext()
    last_activity: float
    created_at: float

    def is_expired(self, timeout: int = 1800) -> bool:
        """Check if session expired (default 30 minutes)"""
        return (time.time() - self.last_activity) > timeout

    def add_message(self, role: str, content: str, intent: str = None, entities: Dict = None):
        """Add message and enforce 20-message limit"""
        self.messages.append(Message(
            role=role,
            content=content,
            timestamp=time.time(),
            intent=intent,
            entities=entities
        ))
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]  # Keep last 20
        self.last_activity = time.time()
```

### Clarification Types

```python
from enum import Enum

class ClarificationType(str, Enum):
    DEVICE = "device"
    LOCATION = "location"
    TIME = "time"
    SPORTS_TEAM = "sports_team"
    GENERIC = "generic"

class Clarification(BaseModel):
    type: ClarificationType
    question: str
    options: List[Dict[str, str]]
    original_query: str
    original_intent: str

    def generate_response(self) -> str:
        """Generate clarification question"""
        if self.type == ClarificationType.DEVICE:
            labels = [opt["label"] for opt in self.options]
            return f"Which device? {', '.join(labels[:-1])}, or {labels[-1]}?"
        elif self.type == ClarificationType.SPORTS_TEAM:
            return f"Which {self.question}?"
        # ... other types
```

## Configuration

### Admin Panel Integration

**⚠️ CRITICAL: All configuration lives in the Admin Panel database**

All conversation and clarification settings are managed through the Admin Panel UI and stored in PostgreSQL. No environment variables or YAML files for configuration.

### Database Schema (PostgreSQL)

**New Tables:**

```sql
-- Conversation Settings Table
CREATE TABLE conversation_settings (
    id SERIAL PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT true,
    use_context BOOLEAN NOT NULL DEFAULT true,
    max_messages INTEGER NOT NULL DEFAULT 20,
    timeout_seconds INTEGER NOT NULL DEFAULT 1800,  -- 30 minutes
    cleanup_interval_seconds INTEGER NOT NULL DEFAULT 60,
    session_ttl_seconds INTEGER NOT NULL DEFAULT 3600,  -- 1 hour
    max_llm_history_messages INTEGER NOT NULL DEFAULT 10,  -- Show 5 exchanges to LLM
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Clarification Settings Table
CREATE TABLE clarification_settings (
    id SERIAL PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT true,
    timeout_seconds INTEGER NOT NULL DEFAULT 300,  -- 5 minutes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Clarification Types Table (configurable per type)
CREATE TABLE clarification_types (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL UNIQUE,  -- 'device', 'location', 'time', 'sports_team'
    enabled BOOLEAN NOT NULL DEFAULT true,
    timeout_seconds INTEGER,  -- Override global timeout if set
    priority INTEGER NOT NULL DEFAULT 0,  -- Higher priority types checked first
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Sports Team Disambiguation Rules (configurable in UI)
CREATE TABLE sports_team_disambiguation (
    id SERIAL PRIMARY KEY,
    team_name VARCHAR(100) NOT NULL,  -- 'Giants', 'Cardinals', etc.
    requires_disambiguation BOOLEAN NOT NULL DEFAULT true,
    options JSONB NOT NULL,  -- [{"id": "ny-giants", "label": "NY Giants (NFL)", "sport": "football"}]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Device Disambiguation Rules (automatically synced from Home Assistant)
CREATE TABLE device_disambiguation_rules (
    id SERIAL PRIMARY KEY,
    device_type VARCHAR(50) NOT NULL,  -- 'lights', 'switches', 'thermostats'
    requires_disambiguation BOOLEAN NOT NULL DEFAULT true,
    min_entities_for_clarification INTEGER NOT NULL DEFAULT 2,
    include_all_option BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Conversation Analytics (for monitoring dashboard)
CREATE TABLE conversation_analytics (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- 'session_created', 'followup_detected', 'clarification_triggered'
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_type (event_type),
    INDEX idx_timestamp (timestamp)
);

-- Insert default settings
INSERT INTO conversation_settings (enabled, use_context, max_messages, timeout_seconds)
VALUES (true, true, 20, 1800);

INSERT INTO clarification_settings (enabled, timeout_seconds)
VALUES (true, 300);

-- Insert default clarification types
INSERT INTO clarification_types (type, enabled, description, priority) VALUES
    ('sports_team', true, 'Disambiguate ambiguous sports team names', 10),
    ('device', true, 'Disambiguate Home Assistant devices when multiple match', 20),
    ('location', true, 'Ask for location when not specified or in context', 30),
    ('time', true, 'Ask for duration/time when not specified', 40);

-- Insert default sports disambiguation rules
INSERT INTO sports_team_disambiguation (team_name, requires_disambiguation, options) VALUES
    ('Giants', true, '[
        {"id": "ny-giants", "label": "NY Giants (NFL)", "sport": "football"},
        {"id": "sf-giants", "label": "SF Giants (MLB)", "sport": "baseball"}
    ]'::jsonb),
    ('Cardinals', true, '[
        {"id": "az-cardinals", "label": "Arizona Cardinals (NFL)", "sport": "football"},
        {"id": "stl-cardinals", "label": "St. Louis Cardinals (MLB)", "sport": "baseball"}
    ]'::jsonb),
    ('Panthers', true, '[
        {"id": "carolina-panthers", "label": "Carolina Panthers (NFL)", "sport": "football"},
        {"id": "florida-panthers", "label": "Florida Panthers (NHL)", "sport": "hockey"}
    ]'::jsonb),
    ('Spurs', true, '[
        {"id": "sa-spurs", "label": "San Antonio Spurs (NBA)", "sport": "basketball"},
        {"id": "tottenham-spurs", "label": "Tottenham Spurs (EPL)", "sport": "soccer"}
    ]'::jsonb);
```

### Redis Schema (Runtime Data Only)

```
# Session keys (runtime only)
session:<session_id> → JSON (Session model)

# Cleanup tracking
sessions:active → SET of active session IDs

# Clarification tracking
clarification:<session_id> → JSON (PendingClarification)

# Config cache (5-minute TTL, auto-refresh from PostgreSQL)
config:conversation_settings → JSON
config:clarification_settings → JSON
config:clarification_types → JSON array
```

### Admin Panel API Endpoints

**New Backend Routes (`admin/backend/routes/conversation.py`):**

```python
# Conversation Settings
GET    /api/conversation/settings                    # Get current settings
PUT    /api/conversation/settings                    # Update settings
POST   /api/conversation/settings/reset              # Reset to defaults

# Clarification Settings
GET    /api/clarification/settings                   # Get current settings
PUT    /api/clarification/settings                   # Update settings

# Clarification Types Management
GET    /api/clarification/types                      # List all types
GET    /api/clarification/types/:id                  # Get specific type
PUT    /api/clarification/types/:id                  # Update type config
POST   /api/clarification/types/:id/toggle           # Enable/disable type

# Sports Team Disambiguation
GET    /api/clarification/sports-teams               # List all configured teams
POST   /api/clarification/sports-teams               # Add new team rule
PUT    /api/clarification/sports-teams/:id           # Update team rule
DELETE /api/clarification/sports-teams/:id           # Remove team rule

# Device Disambiguation Rules
GET    /api/clarification/device-rules               # List device rules
PUT    /api/clarification/device-rules/:id           # Update device rule
POST   /api/clarification/device-rules/sync-ha       # Sync from Home Assistant

# Analytics & Monitoring
GET    /api/conversation/analytics/summary           # Session stats (hourly/daily)
GET    /api/conversation/analytics/events            # Recent events
GET    /api/conversation/sessions/active             # Active sessions count
GET    /api/conversation/sessions/recent             # Recent sessions list
GET    /api/clarification/analytics/types            # Clarification type breakdown
GET    /api/clarification/analytics/success-rate     # Resolution success rate

# Live Monitoring (WebSocket)
WS     /api/conversation/monitor                     # Real-time session events
```

**Request/Response Examples:**

```python
# GET /api/conversation/settings
{
    "enabled": true,
    "use_context": true,
    "max_messages": 20,
    "timeout_seconds": 1800,
    "cleanup_interval_seconds": 60,
    "session_ttl_seconds": 3600,
    "max_llm_history_messages": 10,
    "updated_at": "2025-11-14T10:30:00Z"
}

# PUT /api/conversation/settings
{
    "max_messages": 30,
    "timeout_seconds": 2700  # 45 minutes
}

# Response: 200 OK
{
    "message": "Settings updated successfully",
    "settings": { ... },
    "services_notified": ["orchestrator", "context-manager"]
}

# GET /api/clarification/types
[
    {
        "id": 1,
        "type": "sports_team",
        "enabled": true,
        "timeout_seconds": null,  # Uses global default
        "priority": 10,
        "description": "Disambiguate ambiguous sports team names"
    },
    {
        "id": 2,
        "type": "device",
        "enabled": true,
        "timeout_seconds": 300,
        "priority": 20,
        "description": "Disambiguate Home Assistant devices"
    }
]

# GET /api/conversation/analytics/summary?period=24h
{
    "period": "24h",
    "total_sessions": 145,
    "active_sessions": 3,
    "avg_messages_per_session": 4.2,
    "followup_detection_rate": 0.35,  # 35% of queries are follow-ups
    "clarification_triggered": 28,
    "clarification_resolved": 24,
    "clarification_timeout": 4,
    "top_intents": [
        {"intent": "weather", "count": 52},
        {"intent": "home_assistant_control", "count": 38},
        {"intent": "sports_scores", "count": 21}
    ]
}
```

### Admin Panel Frontend Components

**New React Components (`admin/frontend/src/components/conversation/`):**

1. **ConversationSettings.tsx** - Main settings page
   ```typescript
   interface ConversationSettingsProps {
     // Real-time config editing
     // Toggle features on/off
     // Adjust timeouts and limits
     // Visual feedback for changes
   }

   Features:
   - Enable/disable conversation context
   - Adjust max messages (slider: 5-50)
   - Set timeout (slider: 5-60 minutes)
   - Set cleanup interval
   - Real-time validation
   - "Apply Changes" button with confirmation
   ```

2. **ClarificationManager.tsx** - Clarification types management
   ```typescript
   Features:
   - List all clarification types (device, location, time, sports)
   - Enable/disable individual types
   - Set priority order (drag & drop)
   - Configure per-type timeouts
   - Add custom clarification types
   ```

3. **SportsTeamDisambiguation.tsx** - Sports team rules editor
   ```typescript
   Features:
   - List all ambiguous teams (Giants, Cardinals, Panthers, Spurs)
   - Add new team disambiguation rules
   - Edit options for each team (NFL vs MLB, etc.)
   - Remove obsolete rules
   - Visual sport icons (football, baseball, hockey, basketball)
   ```

4. **ConversationMonitor.tsx** - Live monitoring dashboard
   ```typescript
   Features:
   - Active sessions count (real-time)
   - Recent session events (live feed)
   - Session details view (click to expand)
   - Conversation history for each session
   - Clarification events timeline
   - Auto-refresh every 5 seconds
   ```

5. **ConversationAnalytics.tsx** - Analytics dashboard
   ```typescript
   Charts & Metrics:
   - Sessions over time (line chart)
   - Follow-up detection rate (gauge)
   - Clarification success rate (donut chart)
   - Top intents (bar chart)
   - Average messages per session (stat card)
   - Clarification type distribution (pie chart)

   Time Range Selector: 1h, 6h, 24h, 7d, 30d
   ```

**Admin Panel Navigation Update:**

```typescript
// admin/frontend/src/App.tsx
const navigation = [
  // ... existing items
  {
    name: 'Conversation',
    icon: MessageSquare,
    children: [
      { name: 'Settings', path: '/conversation/settings' },
      { name: 'Clarification Rules', path: '/conversation/clarification' },
      { name: 'Sports Teams', path: '/conversation/sports-teams' },
      { name: 'Monitor', path: '/conversation/monitor' },
      { name: 'Analytics', path: '/conversation/analytics' }
    ]
  }
];
```

### Real-Time Config Updates

**Configuration Reload Mechanism:**

```python
# src/orchestrator/config_loader.py
class ConfigLoader:
    """Loads configuration from Admin Panel database with caching"""

    def __init__(self, db_pool, redis_client):
        self.db = db_pool
        self.redis = redis_client
        self.cache_ttl = 300  # 5 minutes

    async def get_conversation_settings(self) -> ConversationSettings:
        """Get conversation settings with Redis cache"""
        cached = await self.redis.get("config:conversation_settings")
        if cached:
            return ConversationSettings.parse_raw(cached)

        # Fetch from PostgreSQL
        settings = await self.db.fetch_one(
            "SELECT * FROM conversation_settings LIMIT 1"
        )

        # Cache for 5 minutes
        await self.redis.setex(
            "config:conversation_settings",
            self.cache_ttl,
            settings.json()
        )
        return settings

    async def invalidate_cache(self):
        """Called when admin panel updates settings"""
        await self.redis.delete("config:conversation_settings")
        await self.redis.delete("config:clarification_settings")
        await self.redis.delete("config:clarification_types")
```

**Admin Panel Notification System:**

```python
# admin/backend/routes/conversation.py
@router.put("/api/conversation/settings")
async def update_conversation_settings(settings: ConversationSettingsUpdate):
    # Update database
    await db.execute(
        "UPDATE conversation_settings SET ... WHERE id = 1"
    )

    # Invalidate cache in Redis
    await redis.delete("config:conversation_settings")

    # Notify orchestrator to reload config (optional)
    await notify_services(["orchestrator"], "config_updated")

    return {
        "message": "Settings updated successfully",
        "settings": updated_settings,
        "cache_invalidated": True
    }
```

## Open Source Considerations

**⚠️ IMPORTANT: Project Athena is designed to be open source**

While this implementation is initially for a specific 10-zone home deployment, the system is architected for broad community use.

### Design Principles for Open Source

1. **Configuration Flexibility**
   - All settings configurable via Admin Panel UI
   - No hard-coded values tied to specific deployment
   - Support 1-zone to 100+ zone deployments
   - Graceful degradation for missing services

2. **Deployment Scenarios**
   - **Single Zone (Starter)**: 1 Wyoming device, minimal resources
   - **Small Home (3-5 zones)**: Budget-friendly, single server
   - **Medium Home (5-10 zones)**: Reference implementation (this deployment)
   - **Large Home (10-20 zones)**: Multi-server, load balancing
   - **Commercial (20+ zones)**: Enterprise features, HA, failover

3. **Hardware Flexibility**
   - Support various hardware configs (Raspberry Pi to enterprise servers)
   - Auto-detect resource availability
   - Adaptive performance tuning
   - Optional GPU acceleration (not required)

### Example Configurations (Documented in README)

**Minimal Setup (1 zone, Raspberry Pi 4):**
```yaml
conversation:
  enabled: true
  max_messages: 10  # Lower for limited RAM
  timeout_seconds: 900  # 15 minutes

clarification:
  enabled: true
  types: ['device', 'location']  # Basic types only
```

**Standard Setup (5 zones, Mac mini or NUC):**
```yaml
conversation:
  enabled: true
  max_messages: 20
  timeout_seconds: 1800  # 30 minutes

clarification:
  enabled: true
  types: ['device', 'location', 'time', 'sports_team']
```

**Advanced Setup (10+ zones, Proxmox cluster):**
```yaml
conversation:
  enabled: true
  max_messages: 30
  timeout_seconds: 3600  # 1 hour

clarification:
  enabled: true
  types: ['device', 'location', 'time', 'sports_team', 'custom']
  advanced_features:
    - multi_user_profiles
    - conversation_analytics
    - cross_session_memory
```

### Documentation for Community

**New Documentation Files:**

1. **`docs/CONVERSATION_SETUP.md`**
   - Step-by-step configuration guide
   - Screenshots of Admin Panel settings
   - Common scenarios and recommended configs
   - Troubleshooting guide

2. **`docs/CLARIFICATION_RULES.md`**
   - How to add custom disambiguation rules
   - Sports team examples
   - Device naming conventions
   - Location handling

3. **`docs/DEPLOYMENT_SIZES.md`**
   - Minimal (1-3 zones)
   - Small (3-5 zones)
   - Medium (5-10 zones)
   - Large (10-20 zones)
   - Enterprise (20+ zones)
   - Resource requirements for each

4. **`examples/conversation-configs/`**
   - `minimal-pi4.sql` - Raspberry Pi 4 preset
   - `standard-nuc.sql` - Intel NUC preset
   - `advanced-cluster.sql` - Proxmox cluster preset
   - `custom-template.sql` - Blank template for customization

### Community Contribution Guidelines

**Areas for Community Enhancement:**

1. **Additional Clarification Types**
   - Music disambiguation (artist, song, playlist)
   - Recipe selection (multiple results)
   - Calendar event selection
   - Contact disambiguation (similar names)

2. **Language Support**
   - Internationalization of clarification questions
   - Multi-language conversation context
   - Locale-specific defaults

3. **Integration Examples**
   - Different smart home platforms (Home Assistant, OpenHAB, Domoticz)
   - Alternative LLM backends (local models, cloud APIs)
   - Custom RAG data sources

4. **UI Themes & Layouts**
   - Admin panel themes
   - Dashboard layouts
   - Accessibility improvements

**Contributing Process:**
```
1. Fork repository
2. Create feature branch
3. Add configuration examples for new feature
4. Update documentation
5. Submit PR with:
   - Description of use case
   - Configuration examples
   - Screenshots (if UI changes)
   - Performance impact notes
```

### Configuration Portability

**Export/Import Configurations:**

Admin Panel features for sharing configs:

```typescript
// Export current configuration
GET /api/conversation/export
Response: JSON file with all settings

// Import configuration (with validation)
POST /api/conversation/import
Body: Uploaded JSON file
Response: Preview of changes before applying

// Community presets
GET /api/conversation/presets
Response: [
  { name: "Minimal (1-3 zones)", config: {...} },
  { name: "Standard (5-10 zones)", config: {...} },
  { name: "Advanced (10+ zones)", config: {...} }
]
```

### License & Attribution

**Recommended License:** MIT or Apache 2.0 (permissive open source)

**Attribution Guidelines:**
- Reference implementation credit in docs
- Community contributors list
- Third-party dependencies clearly documented

## Rollout Plan

### Stage 1: Internal Testing (Day 5-6)
- Deploy to Mac Studio dev environment
- Test all scenarios manually
- Performance benchmarking
- **Document reference configuration for community**

### Stage 2: Single-Zone Deployment (Day 7)
- Deploy to Office zone only
- Monitor real-world usage
- Collect user feedback
- **Capture real-world usage patterns for docs**

### Stage 3: Gradual Rollout (Day 8-10)
- Deploy to Kitchen, Master Bedroom
- Monitor performance and errors
- Adjust timeouts and limits
- **Test configuration scaling (1→3→5 zones)**

### Stage 4: Full Deployment (Day 11+)
- Deploy to all 10 zones
- Full monitoring enabled
- Documentation published
- **Publish reference configuration as "Medium Home" example**

### Stage 5: Open Source Release (Day 12+)
- Clean up proprietary/personal references
- Add community documentation
- Create example configurations
- Publish GitHub repository
- Announce on Home Assistant community forums

## Success Criteria

### Functional Requirements

✅ **Multi-turn conversations work**
- User can ask follow-up questions without repeating context
- System maintains conversation history for 30 minutes
- Pronouns resolve correctly ("it", "them", "their")

✅ **Clarifying questions function**
- Ambiguous queries trigger clarification
- User responses map to correct entities
- Clarification expires after 5 minutes

✅ **Session management robust**
- Sessions tracked by client identifier
- 20-message history limit enforced
- Expired sessions cleaned up within 60 seconds

### Performance Requirements

✅ **Response times acceptable**
- Context lookup: <50ms
- Session management overhead: <100ms
- Total impact on query latency: <150ms

✅ **Redis performance**
- Session writes: <10ms
- Session reads: <5ms
- Cleanup operations: <100ms per batch

### Quality Requirements

✅ **No context leakage between sessions**
- Different users don't see each other's history
- Session expiry properly isolates conversations

✅ **Graceful degradation**
- If Redis unavailable, fall back to stateless mode
- System continues working without context features

## Risks & Mitigations

### Risk 1: Session ID Collisions

**Risk:** IP-based session IDs may collide for users behind same NAT

**Mitigation:**
- Use `hash(client_ip + user_agent + random_salt)` for session ID
- Add session validation on each request
- Implement session refresh on mismatch detection

### Risk 2: Redis Memory Growth

**Risk:** Conversation history could consume significant Redis memory

**Mitigation:**
- Enforce strict TTLs (1 hour max)
- Limit message count to 20
- Background cleanup every 60 seconds
- Monitor Redis memory usage

### Risk 3: Context Confusion

**Risk:** System might apply wrong context to new conversations

**Mitigation:**
- Clear session expiry (30 minutes)
- Visual/audio indicator for multi-turn mode
- User can say "new conversation" to reset context

### Risk 4: Clarification Timeout

**Risk:** User doesn't respond to clarification within timeout

**Mitigation:**
- Default to "all" option after 5 minutes
- Clear pending clarification from session
- Log timeout events for analysis

## Monitoring & Observability

### Metrics to Track

```python
# Session metrics
session_created_total
session_expired_total
session_active_count
session_message_count_histogram

# Context metrics
context_followup_detected_total
context_resolution_success_total
context_resolution_failed_total

# Clarification metrics
clarification_triggered_total
clarification_resolved_total
clarification_timeout_total
clarification_type_distribution

# Performance metrics
session_lookup_duration_seconds
context_extraction_duration_seconds
redis_operation_duration_seconds
```

### Logs to Capture

```python
# Session lifecycle
logger.info("Session created", session_id=session_id)
logger.info("Session expired", session_id=session_id, age_seconds=age)

# Context resolution
logger.info("Follow-up detected", original_query=query, expanded_query=expanded)
logger.warning("Context resolution failed", query=query, reason=reason)

# Clarification flow
logger.info("Clarification triggered", type=type, options_count=len(options))
logger.info("Clarification resolved", type=type, selected_option=option)
logger.warning("Clarification timeout", type=type, original_query=query)
```

## Testing Strategy

### Unit Tests

- `test_context_manager.py` - Session CRUD, expiry, cleanup
- `test_followup_resolver.py` - Pronoun resolution, query expansion
- `test_clarification.py` - Ambiguity detection, question generation

### Integration Tests

- `test_conversation_flow.py` - Multi-turn scenarios
- `test_clarification_flow.py` - Disambiguation scenarios
- `test_session_expiry.py` - Timeout and cleanup

### Performance Tests

- `test_redis_performance.py` - Session read/write benchmarks
- `test_context_overhead.py` - Latency impact measurement
- `test_concurrent_sessions.py` - Multiple users simultaneously

### Acceptance Tests

Real-world conversation scenarios covering all use cases documented in Phase 5.

## Documentation Updates

### Files to Update

1. **`docs/ARCHITECTURE.md`**
   - Add conversation context architecture
   - Add clarification system diagram
   - Document session lifecycle

2. **`docs/DEPLOYMENT.md`**
   - Add Redis configuration requirements
   - Add environment variable documentation
   - Add monitoring setup

3. **`README.md`**
   - Add conversation features to feature list
   - Add example multi-turn conversations

4. **New: `docs/CONVERSATION_MANAGEMENT.md`**
   - Comprehensive conversation system guide
   - Clarification types reference
   - Troubleshooting guide

## Open Questions

1. **Should we support user accounts eventually?**
   - Current: Session by IP/UA
   - Future: Tie sessions to HA users?
   - Impact: Better personalization, privacy

2. **How many messages should we show to LLM?**
   - Store: 20 messages
   - Show to LLM: 5 exchanges (10 messages)?
   - Trade-off: Context richness vs. token usage

3. **Should clarification timeout be configurable per type?**
   - Device: 5 minutes (current plan)
   - Sports: 2 minutes (shorter)
   - Location: 10 minutes (longer)

4. **Voice feedback for multi-turn mode?**
   - Should Athena say "I remember we were talking about the weather"?
   - Trade-off: Clarity vs. verbosity

## Dependencies

### Required Services

- **PostgreSQL** (Admin Panel database - already deployed)
- **Redis** (session storage and config caching - already deployed)
- **Home Assistant API** (device queries - already integrated)
- **Existing LLM services** (phi3, llama3.1 via Ollama - already deployed)

### New Python Packages

```toml
# pyproject.toml additions (orchestrator service)
dependencies = [
    # ... existing
    "redis-om>=0.2.0",  # Redis object mapping for sessions
    "asyncpg>=0.29.0",  # PostgreSQL async driver for config loading
]
```

```toml
# requirements.txt additions (admin backend)
dependencies = [
    # ... existing (fastapi, uvicorn, etc.)
    # No new packages needed - already have asyncpg, redis
]
```

### Database Migration

```bash
# Apply conversation settings migration
cd admin/backend
psql -h localhost -U athena_admin -d athena_admin < migrations/007_conversation_settings.sql

# Verify tables created
psql -h localhost -U athena_admin -d athena_admin -c "\dt" | grep conversation
# Expected output:
#  public | conversation_analytics        | table | athena_admin
#  public | conversation_settings         | table | athena_admin
#  public | clarification_settings        | table | athena_admin
#  public | clarification_types           | table | athena_admin
#  public | sports_team_disambiguation    | table | athena_admin
#  public | device_disambiguation_rules   | table | athena_admin
```

### Configuration Changes

**⚠️ CRITICAL: Configuration now lives in Admin Panel database (PostgreSQL)**

No YAML or environment variable configuration required. All settings managed via:
- Admin Panel UI: http://localhost:3000/conversation/settings
- Admin Panel API: http://localhost:8080/api/conversation/settings

**Default configuration automatically inserted via migration:**
```sql
-- Default conversation settings (from migration)
INSERT INTO conversation_settings (
    enabled, use_context, max_messages,
    timeout_seconds, cleanup_interval_seconds, session_ttl_seconds
) VALUES (
    true, true, 20, 1800, 60, 3600
);

-- Default clarification settings
INSERT INTO clarification_settings (enabled, timeout_seconds)
VALUES (true, 300);

-- Default clarification types
INSERT INTO clarification_types (type, enabled, priority) VALUES
    ('sports_team', true, 10),
    ('device', true, 20),
    ('location', true, 30),
    ('time', true, 40);
```

**Environment variables (only for DB connection):**
```bash
# .env (orchestrator service) - only connection details
ADMIN_DB_HOST=localhost
ADMIN_DB_PORT=5432
ADMIN_DB_NAME=athena_admin
ADMIN_DB_USER=athena_admin
ADMIN_DB_PASSWORD=<from secrets>
```

All feature configuration is dynamic and loaded from PostgreSQL on startup, cached in Redis for performance.

## Migration Path

### Backward Compatibility

- All existing queries continue to work
- Context features are additive, not breaking
- Stateless mode available as fallback

### Gradual Enablement

```yaml
# Phase 1: Session tracking only (no context usage)
conversation:
  enabled: true
  use_context: false  # Just track, don't use yet

# Phase 2: Enable context for follow-ups
conversation:
  enabled: true
  use_context: true
  clarification_enabled: false  # Context only, no clarification

# Phase 3: Full system
conversation:
  enabled: true
  use_context: true
  clarification_enabled: true
```

## Future Enhancements

### Post-MVP Features

1. **User profiles**
   - Tie sessions to HA users
   - Personalized context per user
   - Preference learning

2. **Advanced clarification**
   - "Did you mean X or Y?" suggestions
   - Fuzzy matching for user responses
   - Context-aware clarification (time of day, user history)

3. **Conversation analytics**
   - Track common clarification needs
   - Identify ambiguous patterns
   - Auto-improve disambiguation rules

4. **Cross-session memory**
   - Long-term preferences
   - Routine detection
   - Proactive suggestions

## References

### Original System Documentation

- `thoughts/shared/research/2025-01-07-comprehensive-voice-assistant-analysis.md`
  - Lines 262-268: Context Management implementation
  - Lines 86-89: Session Management flow
  - Lines 111-115: Context Enhancement details

### Related Documents

- `thoughts/shared/research/2025-11-07-sports-disambiguation-bug-fix.md` - Sports clarification
- `thoughts/shared/research/2025-11-14-voice-transcript-optimization-analysis.md` - Context optimization ideas
- `src/orchestrator/main.py:734-744` - Current conversation caching
- `src/orchestrator/intent_classifier.py:437-467` - Multi-intent context preservation

---

**Next Steps:**

1. **Review and Approval** (Day 0)
   - Review this plan
   - Confirm admin panel integration approach
   - Approve open source design principles
   - Prioritize phases if needed

2. **Database Migration** (Day 1 - Phase 0)
   - Create migration file `007_conversation_settings.sql`
   - Apply migration to athena_admin database
   - Verify default data inserted correctly

3. **Admin Panel API Development** (Day 1 - Phase 0)
   - Create conversation API routes
   - Implement config loader for orchestrator
   - Test API endpoints

4. **Backend Implementation** (Day 2-5 - Phases 1-4)
   - Build conversation context system
   - Implement clarification engine
   - Integrate with admin panel database
   - Track analytics to database

5. **Frontend Development** (Day 2-5 - Phases 1-4)
   - Build Settings page
   - Build Monitoring dashboard
   - Build Analytics dashboard
   - Build Clarification management UI

6. **Testing & Documentation** (Day 6-7 - Phase 5)
   - End-to-end testing
   - Performance benchmarking
   - Write community documentation
   - Create example configurations

7. **Deployment** (Day 8+)
   - Deploy to Mac Studio dev environment
   - Gradual rollout (1 → 3 → 10 zones)
   - Monitor real-world usage
   - Iterate based on feedback

8. **Open Source Preparation** (Day 12+)
   - Clean up personal references
   - Finalize documentation
   - Prepare GitHub repository
   - Community announcement

**Estimated Timeline:** 6-7 days implementation + 4-5 days testing/deployment = **10-12 days total**

**Resources Required:**
- 1 Backend Developer (Python/FastAPI)
- 1 Frontend Developer (React/TypeScript)
- 1 DevOps Engineer (deployment, monitoring)
- PostgreSQL database (Admin Panel - already exists)
- Redis instance (already exists)
- Mac Studio M4 dev environment (already available)
