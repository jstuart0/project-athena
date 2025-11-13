# Admin-Configurable Intent Classification System

## Overview

Transform the intent classification system to be fully configurable through the admin interface, allowing real-time updates without code changes or deployments.

## Architecture

### Database-Driven Configuration

```
┌─────────────────────────────────────────────┐
│              Admin Interface                │
│  ┌────────────────────────────────────────┐ │
│  │  Intent Manager                        │ │
│  │   ├─> Create/Edit Intent Categories    │ │
│  │   ├─> Manage Pattern Matching Rules    │ │
│  │   ├─> Configure Confidence Thresholds  │ │
│  │   ├─> Set Cache TTLs                   │ │
│  │   └─> Test Intent Classification       │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
                     ↓ API
┌─────────────────────────────────────────────┐
│          PostgreSQL Database                │
│  ┌────────────────────────────────────────┐ │
│  │ Tables:                                │ │
│  │  • intent_categories                   │ │
│  │  • intent_patterns                     │ │
│  │  • intent_entities                     │ │
│  │  • validation_rules                    │ │
│  │  • cache_configurations                │ │
│  │  • intent_test_cases                   │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│     Dynamic Intent Classifier               │
│  ┌────────────────────────────────────────┐ │
│  │  • Loads patterns from DB on startup   │ │
│  │  • Refreshes config via Redis pub/sub  │ │
│  │  • Hot-reload without restart          │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## Database Schema

### 1. Intent Categories Table

```sql
CREATE TABLE intent_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 100,  -- Higher priority checked first
    enabled BOOLEAN DEFAULT true,
    requires_llm BOOLEAN DEFAULT false,
    confidence_threshold DECIMAL(3,2) DEFAULT 0.70,
    cache_ttl INTEGER DEFAULT 300,  -- seconds
    color VARCHAR(7),  -- For UI display
    icon VARCHAR(50),  -- Icon name for UI
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed with initial categories
INSERT INTO intent_categories (name, display_name, description, priority, cache_ttl) VALUES
('control', 'Device Control', 'Smart home device control commands', 200, 0),
('weather', 'Weather', 'Weather information queries', 100, 600),
('sports', 'Sports', 'Sports scores and information', 100, 300),
('airports', 'Airports', 'Flight and airport information', 100, 120),
('transit', 'Transit', 'Public transportation information', 100, 60),
('emergency', 'Emergency', 'Emergency services and help', 300, 0),
('food', 'Food & Dining', 'Restaurant and food queries', 100, 3600),
('events', 'Events', 'Local events and entertainment', 100, 3600),
('location', 'Location', 'Distance and direction queries', 100, 1800),
('general_info', 'General Info', 'General information queries', 50, 300);
```

### 2. Intent Patterns Table

```sql
CREATE TABLE intent_patterns (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES intent_categories(id) ON DELETE CASCADE,
    pattern_group VARCHAR(50),  -- e.g., 'basic', 'dimming', 'temperature'
    pattern TEXT NOT NULL,
    pattern_type VARCHAR(20) DEFAULT 'exact',  -- 'exact', 'regex', 'fuzzy'
    weight DECIMAL(3,2) DEFAULT 1.0,  -- Pattern importance weight
    case_sensitive BOOLEAN DEFAULT false,
    enabled BOOLEAN DEFAULT true,
    examples TEXT[],  -- Example queries that match
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    INDEX idx_category (category_id),
    INDEX idx_enabled (enabled)
);

-- Example patterns
INSERT INTO intent_patterns (category_id, pattern_group, pattern, examples) VALUES
(1, 'basic', 'turn on', ARRAY['turn on the lights', 'turn on bedroom fan']),
(1, 'basic', 'turn off', ARRAY['turn off the TV', 'turn off all lights']),
(1, 'dimming', 'dim', ARRAY['dim the lights', 'dim bedroom to 50%']),
(2, 'current', 'weather', ARRAY['what\'s the weather', 'weather today']),
(3, 'teams', 'ravens', ARRAY['ravens score', 'did the ravens win']);
```

### 3. Intent Entities Table

```sql
CREATE TABLE intent_entities (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES intent_categories(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,  -- 'room', 'device', 'team', etc.
    entity_value VARCHAR(100) NOT NULL,
    synonyms TEXT[],  -- Alternative names
    metadata JSONB,  -- Additional entity data
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(category_id, entity_type, entity_value),
    INDEX idx_category_type (category_id, entity_type)
);

-- Example entities
INSERT INTO intent_entities (category_id, entity_type, entity_value, synonyms) VALUES
(1, 'room', 'bedroom', ARRAY['master bedroom', 'bed room', 'sleeping room']),
(1, 'device', 'lights', ARRAY['light', 'lamps', 'lighting']),
(3, 'team', 'ravens', ARRAY['Baltimore Ravens', 'ravens team']);
```

### 4. Validation Rules Table

```sql
CREATE TABLE validation_rules (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES intent_categories(id) ON DELETE CASCADE,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,  -- 'required_entity', 'response_contains', 'format_check'
    rule_config JSONB NOT NULL,  -- Rule configuration
    error_message TEXT,
    severity VARCHAR(20) DEFAULT 'warning',  -- 'error', 'warning', 'info'
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example validation rules
INSERT INTO validation_rules (category_id, rule_name, rule_type, rule_config, error_message) VALUES
(3, 'score_check', 'response_contains', '{"patterns": ["\\\\d+", "won", "lost", "beat"]}', 'Response must include score or result'),
(2, 'weather_check', 'response_contains', '{"patterns": ["degrees", "°", "sunny", "rain"]}', 'Response must include weather information');
```

### 5. Intent Test Cases Table

```sql
CREATE TABLE intent_test_cases (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES intent_categories(id) ON DELETE CASCADE,
    test_query TEXT NOT NULL,
    expected_category VARCHAR(50) NOT NULL,
    expected_entities JSONB,
    expected_confidence_min DECIMAL(3,2),
    notes TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_test_result JSONB,
    last_test_date TIMESTAMP
);

-- Example test cases
INSERT INTO intent_test_cases (category_id, test_query, expected_category, expected_entities, expected_confidence_min) VALUES
(1, 'turn on the bedroom lights', 'control', '{"room": "bedroom", "device": "lights", "action": "on"}', 0.8),
(2, 'what is the weather tomorrow', 'weather', '{"timeframe": "tomorrow"}', 0.7);
```

### 6. Configuration History Table

```sql
CREATE TABLE configuration_history (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    operation VARCHAR(20) NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE'
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Trigger to track changes
CREATE OR REPLACE FUNCTION track_configuration_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO configuration_history (table_name, record_id, operation, old_values, new_values, changed_by)
    VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        to_jsonb(OLD),
        to_jsonb(NEW),
        current_user
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all configuration tables
CREATE TRIGGER track_intent_categories_changes
    AFTER INSERT OR UPDATE OR DELETE ON intent_categories
    FOR EACH ROW EXECUTE FUNCTION track_configuration_change();
```

## Enhanced Intent Classifier Implementation

### Database-Aware Intent Classifier

```python
# src/orchestrator/db_intent_classifier.py

import asyncio
import asyncpg
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


class DatabaseIntentClassifier:
    """Intent classifier that loads configuration from database"""

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        redis_client: redis.Redis,
        refresh_interval: int = 300  # Refresh config every 5 minutes
    ):
        self.db_pool = db_pool
        self.redis = redis_client
        self.refresh_interval = refresh_interval

        # Cache configuration in memory
        self.categories: Dict[str, Dict] = {}
        self.patterns: Dict[str, List[Dict]] = {}
        self.entities: Dict[str, List[Dict]] = {}
        self.validation_rules: Dict[str, List[Dict]] = {}

        # Last refresh time
        self.last_refresh = None
        self.refresh_lock = asyncio.Lock()

    async def initialize(self):
        """Load initial configuration from database"""
        await self.refresh_configuration()

        # Set up Redis pub/sub for real-time updates
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe('intent_config_update')

        # Start background refresh task
        asyncio.create_task(self._periodic_refresh())
        asyncio.create_task(self._listen_for_updates())

    async def refresh_configuration(self):
        """Load all configuration from database"""
        async with self.refresh_lock:
            try:
                async with self.db_pool.acquire() as conn:
                    # Load categories
                    categories = await conn.fetch("""
                        SELECT * FROM intent_categories
                        WHERE enabled = true
                        ORDER BY priority DESC
                    """)
                    self.categories = {
                        cat['name']: dict(cat)
                        for cat in categories
                    }

                    # Load patterns
                    patterns = await conn.fetch("""
                        SELECT p.*, c.name as category_name
                        FROM intent_patterns p
                        JOIN intent_categories c ON p.category_id = c.id
                        WHERE p.enabled = true AND c.enabled = true
                        ORDER BY p.weight DESC
                    """)

                    self.patterns = {}
                    for pattern in patterns:
                        cat_name = pattern['category_name']
                        if cat_name not in self.patterns:
                            self.patterns[cat_name] = []
                        self.patterns[cat_name].append(dict(pattern))

                    # Load entities
                    entities = await conn.fetch("""
                        SELECT e.*, c.name as category_name
                        FROM intent_entities e
                        JOIN intent_categories c ON e.category_id = c.id
                        WHERE e.enabled = true AND c.enabled = true
                    """)

                    self.entities = {}
                    for entity in entities:
                        cat_name = entity['category_name']
                        if cat_name not in self.entities:
                            self.entities[cat_name] = []
                        self.entities[cat_name].append(dict(entity))

                    # Load validation rules
                    rules = await conn.fetch("""
                        SELECT r.*, c.name as category_name
                        FROM validation_rules r
                        JOIN intent_categories c ON r.category_id = c.id
                        WHERE r.enabled = true AND c.enabled = true
                    """)

                    self.validation_rules = {}
                    for rule in rules:
                        cat_name = rule['category_name']
                        if cat_name not in self.validation_rules:
                            self.validation_rules[cat_name] = []
                        self.validation_rules[cat_name].append(dict(rule))

                self.last_refresh = datetime.now()
                logger.info(
                    f"Intent configuration refreshed: "
                    f"{len(self.categories)} categories, "
                    f"{sum(len(p) for p in self.patterns.values())} patterns"
                )

            except Exception as e:
                logger.error(f"Failed to refresh intent configuration: {e}")
                raise

    async def _periodic_refresh(self):
        """Periodically refresh configuration"""
        while True:
            await asyncio.sleep(self.refresh_interval)
            try:
                await self.refresh_configuration()
            except Exception as e:
                logger.error(f"Periodic refresh failed: {e}")

    async def _listen_for_updates(self):
        """Listen for Redis pub/sub configuration updates"""
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    if data.get('action') == 'refresh':
                        logger.info("Received configuration update notification")
                        await self.refresh_configuration()
                except Exception as e:
                    logger.error(f"Failed to process update notification: {e}")

    async def classify(self, query: str) -> Dict[str, Any]:
        """Classify intent using database configuration"""
        query_lower = query.lower().strip()

        # Check if refresh needed
        if (
            self.last_refresh is None or
            datetime.now() - self.last_refresh > timedelta(seconds=self.refresh_interval)
        ):
            await self.refresh_configuration()

        best_match = None
        best_confidence = 0.0
        matched_patterns = []

        # Check each category by priority
        for cat_name, category in sorted(
            self.categories.items(),
            key=lambda x: x[1]['priority'],
            reverse=True
        ):
            if cat_name not in self.patterns:
                continue

            # Calculate pattern matches
            category_score = 0.0
            category_matches = []

            for pattern_def in self.patterns[cat_name]:
                pattern = pattern_def['pattern']
                weight = float(pattern_def.get('weight', 1.0))

                matched = False
                if pattern_def.get('pattern_type') == 'regex':
                    try:
                        if re.search(pattern, query_lower):
                            matched = True
                    except re.error:
                        logger.warning(f"Invalid regex pattern: {pattern}")
                else:
                    # Exact match (substring)
                    if pattern.lower() in query_lower:
                        matched = True

                if matched:
                    category_score += weight
                    category_matches.append(pattern)

            if category_score > 0:
                # Calculate confidence
                max_possible_score = sum(
                    float(p.get('weight', 1.0))
                    for p in self.patterns[cat_name]
                )
                base_confidence = 0.5
                confidence = base_confidence + (
                    (category_score / max(max_possible_score, 1)) * 0.5
                )

                # Apply category confidence threshold
                threshold = float(category.get('confidence_threshold', 0.7))

                if confidence >= threshold and confidence > best_confidence:
                    best_confidence = confidence
                    best_match = cat_name
                    matched_patterns = category_matches

        # Extract entities
        entities = {}
        if best_match and best_match in self.entities:
            entities = await self._extract_entities(
                query_lower,
                self.entities[best_match]
            )

        # Determine if LLM is required
        requires_llm = False
        if best_match:
            requires_llm = self.categories[best_match].get('requires_llm', False)

        # Check for complex indicators
        if not requires_llm:
            complex_indicators = [
                "explain", "why", "how", "what is the difference",
                "compare", "analyze", "summarize"
            ]
            requires_llm = any(ind in query_lower for ind in complex_indicators)

        return {
            'category': best_match or 'unknown',
            'confidence': best_confidence,
            'entities': entities,
            'requires_llm': requires_llm,
            'matched_patterns': matched_patterns,
            'cache_ttl': self.categories.get(best_match, {}).get('cache_ttl', 300) if best_match else 0
        }

    async def _extract_entities(
        self,
        query: str,
        entity_definitions: List[Dict]
    ) -> Dict[str, Any]:
        """Extract entities based on database definitions"""
        entities = {}

        for entity_def in entity_definitions:
            entity_type = entity_def['entity_type']
            entity_value = entity_def['entity_value'].lower()
            synonyms = entity_def.get('synonyms', [])

            # Check main value
            if entity_value in query:
                entities[entity_type] = entity_def['entity_value']
                continue

            # Check synonyms
            for synonym in synonyms:
                if synonym.lower() in query:
                    entities[entity_type] = entity_def['entity_value']
                    break

        return entities

    async def add_pattern(
        self,
        category: str,
        pattern: str,
        pattern_group: str = 'custom',
        weight: float = 1.0,
        examples: List[str] = None
    ) -> int:
        """Add a new pattern through the API"""
        async with self.db_pool.acquire() as conn:
            # Get category ID
            cat_id = await conn.fetchval(
                "SELECT id FROM intent_categories WHERE name = $1",
                category
            )

            if not cat_id:
                raise ValueError(f"Category {category} not found")

            # Insert pattern
            pattern_id = await conn.fetchval("""
                INSERT INTO intent_patterns
                (category_id, pattern_group, pattern, weight, examples, created_by)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, cat_id, pattern_group, pattern, weight, examples, 'admin_api')

            # Notify other instances to refresh
            await self.redis.publish(
                'intent_config_update',
                json.dumps({'action': 'refresh', 'table': 'intent_patterns'})
            )

            # Refresh local configuration
            await self.refresh_configuration()

            return pattern_id

    async def test_classification(
        self,
        query: str
    ) -> Dict[str, Any]:
        """Test classification with detailed results"""
        result = await self.classify(query)

        # Add debugging information
        result['debug'] = {
            'categories_checked': list(self.categories.keys()),
            'total_patterns': sum(len(p) for p in self.patterns.values()),
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None
        }

        # Run test cases if matching
        async with self.db_pool.acquire() as conn:
            test_cases = await conn.fetch("""
                SELECT * FROM intent_test_cases
                WHERE test_query = $1 AND enabled = true
            """, query)

            if test_cases:
                test_case = dict(test_cases[0])
                passed = (
                    result['category'] == test_case['expected_category'] and
                    result['confidence'] >= float(test_case.get('expected_confidence_min', 0))
                )

                result['test_result'] = {
                    'passed': passed,
                    'expected_category': test_case['expected_category'],
                    'expected_confidence_min': float(test_case.get('expected_confidence_min', 0))
                }

                # Update test result in database
                await conn.execute("""
                    UPDATE intent_test_cases
                    SET last_test_result = $1, last_test_date = $2
                    WHERE id = $3
                """, json.dumps(result), datetime.now(), test_case['id'])

        return result

    async def close(self):
        """Clean up resources"""
        if hasattr(self, 'pubsub'):
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
```

## Admin API Endpoints

### FastAPI Router for Intent Management

```python
# src/admin/backend/routers/intents.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import asyncpg
from datetime import datetime

router = APIRouter(prefix="/api/intents", tags=["intents"])


class IntentCategoryCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str]
    priority: int = 100
    confidence_threshold: float = 0.70
    cache_ttl: int = 300
    requires_llm: bool = False
    color: Optional[str]
    icon: Optional[str]


class IntentPatternCreate(BaseModel):
    category_id: int
    pattern_group: str
    pattern: str
    pattern_type: str = "exact"
    weight: float = 1.0
    case_sensitive: bool = False
    examples: Optional[List[str]]


class IntentEntityCreate(BaseModel):
    category_id: int
    entity_type: str
    entity_value: str
    synonyms: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]


class TestQueryRequest(BaseModel):
    query: str
    expected_category: Optional[str]
    expected_confidence_min: Optional[float]


@router.get("/categories")
async def list_categories(
    enabled: Optional[bool] = Query(None),
    db: asyncpg.Pool = Depends(get_db)
):
    """List all intent categories"""
    query = "SELECT * FROM intent_categories"
    params = []

    if enabled is not None:
        query += " WHERE enabled = $1"
        params.append(enabled)

    query += " ORDER BY priority DESC, name"

    async with db.acquire() as conn:
        results = await conn.fetch(query, *params)

    return [dict(r) for r in results]


@router.post("/categories")
async def create_category(
    category: IntentCategoryCreate,
    db: asyncpg.Pool = Depends(get_db)
):
    """Create a new intent category"""
    async with db.acquire() as conn:
        try:
            cat_id = await conn.fetchval("""
                INSERT INTO intent_categories
                (name, display_name, description, priority, confidence_threshold,
                 cache_ttl, requires_llm, color, icon)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """,
                category.name,
                category.display_name,
                category.description,
                category.priority,
                category.confidence_threshold,
                category.cache_ttl,
                category.requires_llm,
                category.color,
                category.icon
            )

            # Publish update notification
            await publish_config_update("intent_categories")

            return {"id": cat_id, "message": "Category created successfully"}

        except asyncpg.UniqueViolationError:
            raise HTTPException(400, f"Category {category.name} already exists")


@router.put("/categories/{category_id}")
async def update_category(
    category_id: int,
    updates: Dict[str, Any],
    db: asyncpg.Pool = Depends(get_db)
):
    """Update an intent category"""
    # Build update query dynamically
    set_clauses = []
    params = []
    param_count = 1

    for key, value in updates.items():
        if key not in ['id', 'created_at']:  # Exclude immutable fields
            set_clauses.append(f"{key} = ${param_count}")
            params.append(value)
            param_count += 1

    if not set_clauses:
        raise HTTPException(400, "No valid fields to update")

    params.append(category_id)
    query = f"""
        UPDATE intent_categories
        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ${param_count}
        RETURNING *
    """

    async with db.acquire() as conn:
        result = await conn.fetchrow(query, *params)

        if not result:
            raise HTTPException(404, f"Category {category_id} not found")

        # Publish update notification
        await publish_config_update("intent_categories")

        return dict(result)


@router.get("/patterns")
async def list_patterns(
    category_id: Optional[int] = Query(None),
    pattern_group: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: asyncpg.Pool = Depends(get_db)
):
    """List intent patterns with optional filters"""
    query = """
        SELECT p.*, c.name as category_name, c.display_name as category_display_name
        FROM intent_patterns p
        JOIN intent_categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []
    param_count = 0

    if category_id is not None:
        param_count += 1
        query += f" AND p.category_id = ${param_count}"
        params.append(category_id)

    if pattern_group is not None:
        param_count += 1
        query += f" AND p.pattern_group = ${param_count}"
        params.append(pattern_group)

    if enabled is not None:
        param_count += 1
        query += f" AND p.enabled = ${param_count}"
        params.append(enabled)

    query += " ORDER BY p.weight DESC, p.pattern"

    async with db.acquire() as conn:
        results = await conn.fetch(query, *params)

    return [dict(r) for r in results]


@router.post("/patterns")
async def create_pattern(
    pattern: IntentPatternCreate,
    db: asyncpg.Pool = Depends(get_db)
):
    """Create a new intent pattern"""
    async with db.acquire() as conn:
        pattern_id = await conn.fetchval("""
            INSERT INTO intent_patterns
            (category_id, pattern_group, pattern, pattern_type, weight,
             case_sensitive, examples, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """,
            pattern.category_id,
            pattern.pattern_group,
            pattern.pattern,
            pattern.pattern_type,
            pattern.weight,
            pattern.case_sensitive,
            pattern.examples,
            'admin_api'
        )

        # Publish update notification
        await publish_config_update("intent_patterns")

        return {"id": pattern_id, "message": "Pattern created successfully"}


@router.delete("/patterns/{pattern_id}")
async def delete_pattern(
    pattern_id: int,
    db: asyncpg.Pool = Depends(get_db)
):
    """Delete an intent pattern"""
    async with db.acquire() as conn:
        deleted = await conn.fetchval(
            "DELETE FROM intent_patterns WHERE id = $1 RETURNING id",
            pattern_id
        )

        if not deleted:
            raise HTTPException(404, f"Pattern {pattern_id} not found")

        # Publish update notification
        await publish_config_update("intent_patterns")

        return {"message": "Pattern deleted successfully"}


@router.post("/test")
async def test_classification(
    request: TestQueryRequest,
    db: asyncpg.Pool = Depends(get_db),
    classifier: DatabaseIntentClassifier = Depends(get_classifier)
):
    """Test intent classification with a query"""
    result = await classifier.test_classification(request.query)

    # Check against expected if provided
    if request.expected_category:
        result['expected_match'] = result['category'] == request.expected_category

    if request.expected_confidence_min:
        result['confidence_pass'] = result['confidence'] >= request.expected_confidence_min

    return result


@router.post("/patterns/bulk-import")
async def bulk_import_patterns(
    patterns: List[IntentPatternCreate],
    db: asyncpg.Pool = Depends(get_db)
):
    """Bulk import intent patterns"""
    async with db.acquire() as conn:
        # Use COPY for efficient bulk insert
        imported = 0
        errors = []

        for pattern in patterns:
            try:
                await conn.execute("""
                    INSERT INTO intent_patterns
                    (category_id, pattern_group, pattern, pattern_type,
                     weight, case_sensitive, examples, created_by)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                    pattern.category_id,
                    pattern.pattern_group,
                    pattern.pattern,
                    pattern.pattern_type,
                    pattern.weight,
                    pattern.case_sensitive,
                    pattern.examples,
                    'bulk_import'
                )
                imported += 1
            except Exception as e:
                errors.append(f"Pattern '{pattern.pattern}': {str(e)}")

        # Publish update notification
        await publish_config_update("intent_patterns")

        return {
            "imported": imported,
            "errors": errors,
            "message": f"Imported {imported} patterns successfully"
        }


@router.get("/test-cases")
async def list_test_cases(
    category_id: Optional[int] = Query(None),
    db: asyncpg.Pool = Depends(get_db)
):
    """List intent test cases"""
    query = """
        SELECT t.*, c.name as category_name
        FROM intent_test_cases t
        JOIN intent_categories c ON t.category_id = c.id
        WHERE t.enabled = true
    """
    params = []

    if category_id is not None:
        query += " AND t.category_id = $1"
        params.append(category_id)

    query += " ORDER BY t.created_at DESC"

    async with db.acquire() as conn:
        results = await conn.fetch(query, *params)

    return [dict(r) for r in results]


@router.post("/test-cases/run-all")
async def run_all_test_cases(
    category_id: Optional[int] = Query(None),
    db: asyncpg.Pool = Depends(get_db),
    classifier: DatabaseIntentClassifier = Depends(get_classifier)
):
    """Run all test cases and report results"""
    query = "SELECT * FROM intent_test_cases WHERE enabled = true"
    params = []

    if category_id is not None:
        query += " AND category_id = $1"
        params.append(category_id)

    async with db.acquire() as conn:
        test_cases = await conn.fetch(query, *params)

    results = {
        'total': len(test_cases),
        'passed': 0,
        'failed': 0,
        'details': []
    }

    for test_case in test_cases:
        test_result = await classifier.test_classification(test_case['test_query'])

        passed = (
            test_result['category'] == test_case['expected_category'] and
            test_result['confidence'] >= float(test_case.get('expected_confidence_min', 0))
        )

        if passed:
            results['passed'] += 1
        else:
            results['failed'] += 1

        results['details'].append({
            'id': test_case['id'],
            'query': test_case['test_query'],
            'passed': passed,
            'expected': test_case['expected_category'],
            'actual': test_result['category'],
            'confidence': test_result['confidence']
        })

    return results


@router.get("/statistics")
async def get_statistics(
    db: asyncpg.Pool = Depends(get_db)
):
    """Get intent system statistics"""
    async with db.acquire() as conn:
        stats = {}

        # Category count
        stats['total_categories'] = await conn.fetchval(
            "SELECT COUNT(*) FROM intent_categories WHERE enabled = true"
        )

        # Pattern count
        stats['total_patterns'] = await conn.fetchval(
            "SELECT COUNT(*) FROM intent_patterns WHERE enabled = true"
        )

        # Entity count
        stats['total_entities'] = await conn.fetchval(
            "SELECT COUNT(*) FROM intent_entities WHERE enabled = true"
        )

        # Test case stats
        test_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN last_test_result->>'passed' = 'true' THEN 1 END) as passed,
                COUNT(CASE WHEN last_test_result->>'passed' = 'false' THEN 1 END) as failed
            FROM intent_test_cases
            WHERE enabled = true
        """)
        stats['test_cases'] = dict(test_stats)

        # Recent changes
        stats['recent_changes'] = await conn.fetchval("""
            SELECT COUNT(*)
            FROM configuration_history
            WHERE changed_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
        """)

        # Pattern distribution by category
        pattern_dist = await conn.fetch("""
            SELECT c.display_name, COUNT(p.id) as pattern_count
            FROM intent_categories c
            LEFT JOIN intent_patterns p ON c.id = p.category_id AND p.enabled = true
            WHERE c.enabled = true
            GROUP BY c.display_name
            ORDER BY pattern_count DESC
        """)
        stats['pattern_distribution'] = [dict(r) for r in pattern_dist]

    return stats


async def publish_config_update(table: str):
    """Publish configuration update notification via Redis"""
    # This would be injected/configured in actual implementation
    redis_client = get_redis_client()
    await redis_client.publish(
        'intent_config_update',
        json.dumps({'action': 'refresh', 'table': table, 'timestamp': datetime.now().isoformat()})
    )
```

## Admin UI Components

### React Components for Intent Management

```typescript
// src/admin/frontend/components/IntentManager.tsx

import React, { useState, useEffect } from 'react';
import {
  Tabs,
  Tab,
  Card,
  Table,
  Button,
  Modal,
  Form,
  Alert,
  Badge
} from 'react-bootstrap';

interface IntentCategory {
  id: number;
  name: string;
  display_name: string;
  description: string;
  priority: number;
  confidence_threshold: number;
  cache_ttl: number;
  enabled: boolean;
  color?: string;
  icon?: string;
}

interface IntentPattern {
  id: number;
  category_id: number;
  category_name: string;
  pattern: string;
  pattern_type: string;
  weight: number;
  enabled: boolean;
  examples?: string[];
}

export const IntentManager: React.FC = () => {
  const [categories, setCategories] = useState<IntentCategory[]>([]);
  const [patterns, setPatterns] = useState<IntentPattern[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [showPatternModal, setShowPatternModal] = useState(false);
  const [testQuery, setTestQuery] = useState('');
  const [testResult, setTestResult] = useState<any>(null);

  useEffect(() => {
    loadCategories();
    loadPatterns();
  }, []);

  const loadCategories = async () => {
    const response = await fetch('/api/intents/categories');
    const data = await response.json();
    setCategories(data);
  };

  const loadPatterns = async (categoryId?: number) => {
    let url = '/api/intents/patterns';
    if (categoryId) {
      url += `?category_id=${categoryId}`;
    }
    const response = await fetch(url);
    const data = await response.json();
    setPatterns(data);
  };

  const testClassification = async () => {
    const response = await fetch('/api/intents/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: testQuery })
    });
    const result = await response.json();
    setTestResult(result);
  };

  const addPattern = async (pattern: Partial<IntentPattern>) => {
    const response = await fetch('/api/intents/patterns', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pattern)
    });

    if (response.ok) {
      loadPatterns(selectedCategory || undefined);
      setShowPatternModal(false);
    }
  };

  return (
    <div className="intent-manager">
      <h2>Intent Classification Manager</h2>

      <Tabs defaultActiveKey="categories">
        <Tab eventKey="categories" title="Categories">
          <Card className="mt-3">
            <Card.Body>
              <Table striped bordered hover>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Display Name</th>
                    <th>Priority</th>
                    <th>Confidence</th>
                    <th>Cache TTL</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((category) => (
                    <tr key={category.id}>
                      <td>
                        {category.icon && <i className={`fa fa-${category.icon}`} />}
                        {' '}{category.name}
                      </td>
                      <td>{category.display_name}</td>
                      <td>{category.priority}</td>
                      <td>{(category.confidence_threshold * 100).toFixed(0)}%</td>
                      <td>{category.cache_ttl}s</td>
                      <td>
                        <Badge variant={category.enabled ? 'success' : 'secondary'}>
                          {category.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                      </td>
                      <td>
                        <Button
                          size="sm"
                          variant="outline-primary"
                          onClick={() => {
                            setSelectedCategory(category.id);
                            loadPatterns(category.id);
                          }}
                        >
                          View Patterns
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </Tab>

        <Tab eventKey="patterns" title="Patterns">
          <Card className="mt-3">
            <Card.Body>
              <div className="d-flex justify-content-between mb-3">
                <h5>
                  Intent Patterns
                  {selectedCategory && (
                    <Badge className="ml-2" variant="info">
                      {categories.find(c => c.id === selectedCategory)?.display_name}
                    </Badge>
                  )}
                </h5>
                <Button
                  variant="primary"
                  onClick={() => setShowPatternModal(true)}
                >
                  Add Pattern
                </Button>
              </div>

              <Table striped bordered hover>
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Pattern</th>
                    <th>Type</th>
                    <th>Weight</th>
                    <th>Examples</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {patterns.map((pattern) => (
                    <tr key={pattern.id}>
                      <td>{pattern.category_name}</td>
                      <td><code>{pattern.pattern}</code></td>
                      <td>{pattern.pattern_type}</td>
                      <td>{pattern.weight}</td>
                      <td>
                        {pattern.examples?.map((ex, i) => (
                          <div key={i} className="small text-muted">{ex}</div>
                        ))}
                      </td>
                      <td>
                        <Button size="sm" variant="outline-danger">
                          Delete
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </Tab>

        <Tab eventKey="test" title="Test">
          <Card className="mt-3">
            <Card.Body>
              <h5>Test Intent Classification</h5>
              <Form>
                <Form.Group>
                  <Form.Label>Test Query</Form.Label>
                  <Form.Control
                    type="text"
                    placeholder="Enter a query to test..."
                    value={testQuery}
                    onChange={(e) => setTestQuery(e.target.value)}
                  />
                </Form.Group>
                <Button onClick={testClassification}>
                  Test Classification
                </Button>
              </Form>

              {testResult && (
                <Alert variant="info" className="mt-3">
                  <h6>Classification Result:</h6>
                  <ul>
                    <li>Category: <strong>{testResult.category}</strong></li>
                    <li>Confidence: <strong>{(testResult.confidence * 100).toFixed(1)}%</strong></li>
                    <li>Cache TTL: {testResult.cache_ttl}s</li>
                    <li>Requires LLM: {testResult.requires_llm ? 'Yes' : 'No'}</li>
                    <li>Matched Patterns: {testResult.matched_patterns?.join(', ') || 'None'}</li>
                    <li>
                      Entities:
                      <pre>{JSON.stringify(testResult.entities, null, 2)}</pre>
                    </li>
                  </ul>
                </Alert>
              )}
            </Card.Body>
          </Card>
        </Tab>

        <Tab eventKey="validation" title="Validation Rules">
          <Card className="mt-3">
            <Card.Body>
              <h5>Response Validation Rules</h5>
              <p>Configure validation rules for each intent category...</p>
            </Card.Body>
          </Card>
        </Tab>
      </Tabs>

      {/* Add Pattern Modal */}
      <Modal show={showPatternModal} onHide={() => setShowPatternModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Add Intent Pattern</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <PatternForm
            categories={categories}
            onSubmit={addPattern}
            defaultCategoryId={selectedCategory}
          />
        </Modal.Body>
      </Modal>
    </div>
  );
};
```

## Integration with Orchestrator

### Updated Orchestrator with Database Classifier

```python
# src/orchestrator/main.py - Updated classify_node

from db_intent_classifier import DatabaseIntentClassifier

# Initialize database classifier
db_classifier = None

async def initialize_classifier():
    """Initialize database-driven classifier on startup"""
    global db_classifier

    # Get database pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    # Get Redis client
    redis_client = await redis.from_url(REDIS_URL)

    # Create classifier
    db_classifier = DatabaseIntentClassifier(db_pool, redis_client)
    await db_classifier.initialize()

    logger.info("Database intent classifier initialized")

async def classify_node(state: OrchestratorState) -> OrchestratorState:
    """Classify intent using database-configured patterns"""

    # Use database classifier
    classification = await db_classifier.classify(state.query)

    # Map to state
    state.intent = IntentCategory(classification['category'])
    state.metadata['confidence'] = classification['confidence']
    state.metadata['entities'] = classification['entities']
    state.metadata['requires_llm'] = classification['requires_llm']
    state.metadata['matched_patterns'] = classification.get('matched_patterns', [])
    state.metadata['cache_ttl'] = classification.get('cache_ttl', 300)

    # Use LLM if required or low confidence
    if classification['requires_llm'] or classification['confidence'] < 0.6:
        state = await _llm_classify_fallback(state)

    logger.info(
        f"Intent classified: {state.intent.value} "
        f"(confidence: {classification['confidence']:.2f}, "
        f"patterns: {len(classification.get('matched_patterns', []))})"
    )

    return state

# Add to FastAPI startup
@app.on_event("startup")
async def startup_event():
    await initialize_classifier()
    logger.info("Orchestrator started with database intent classifier")

@app.on_event("shutdown")
async def shutdown_event():
    if db_classifier:
        await db_classifier.close()
```

## Benefits of This Approach

1. **No Code Changes Required**: Add new intents, patterns, and entities through the admin UI
2. **Real-Time Updates**: Changes propagate to all services via Redis pub/sub
3. **Version Control**: All configuration changes are tracked in the database
4. **Testing Built-In**: Test classification directly in the admin interface
5. **Performance Monitoring**: Track which patterns match and their effectiveness
6. **Rollback Capability**: Configuration history allows reverting changes
7. **A/B Testing**: Can enable/disable patterns to test effectiveness
8. **Multi-Tenant Ready**: Could extend to support different configurations per user/context

## Migration Path

1. **Phase 1**: Deploy database schema
2. **Phase 2**: Seed with existing patterns from code
3. **Phase 3**: Deploy admin API endpoints
4. **Phase 4**: Add admin UI components
5. **Phase 5**: Update orchestrator to use database classifier
6. **Phase 6**: Remove hardcoded patterns from code

This makes the entire intent classification system manageable through the admin interface without any code deployments!