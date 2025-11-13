#!/usr/bin/env python3
"""
Run database migrations for Project Athena
Creates all necessary tables for intent configuration, validation, and RAG services
"""

import asyncio
import asyncpg
import os
import sys
import json
from datetime import datetime

# Database connection - using homelab PostgreSQL at postgres-01.xmojo.net
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://psadmin:Ibucej1!@postgres-01.xmojo.net:5432/athena')
ADMIN_DATABASE_URL = os.getenv('ADMIN_DATABASE_URL', 'postgresql://psadmin:Ibucej1!@postgres-01.xmojo.net:5432/athena_admin')


async def create_databases():
    """Create databases if they don't exist"""
    # Parse the connection string to get components
    main_db_parts = DATABASE_URL.split('/')
    admin_db_parts = ADMIN_DATABASE_URL.split('/')

    base_url = '/'.join(main_db_parts[:-1]) + '/postgres'

    try:
        # Connect to postgres database to create others
        conn = await asyncpg.connect(base_url)

        # Create main database
        try:
            await conn.execute("CREATE DATABASE athena")
            print("✅ Created database: athena")
        except asyncpg.DuplicateDatabaseError:
            print("✓ Database 'athena' already exists")

        # Create admin database
        try:
            await conn.execute("CREATE DATABASE athena_admin")
            print("✅ Created database: athena_admin")
        except asyncpg.DuplicateDatabaseError:
            print("✓ Database 'athena_admin' already exists")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Error creating databases: {e}")
        return False


async def run_athena_migrations():
    """Run migrations for main Athena database"""
    print("\n🔧 Running Athena database migrations...")

    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Intent categories table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS intent_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                description TEXT,
                priority INTEGER DEFAULT 100,
                enabled BOOLEAN DEFAULT true,
                requires_llm BOOLEAN DEFAULT false,
                confidence_threshold DECIMAL(3,2) DEFAULT 0.70,
                cache_ttl INTEGER DEFAULT 300,
                color VARCHAR(7),
                icon VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: intent_categories")

        # Intent patterns table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS intent_patterns (
                id SERIAL PRIMARY KEY,
                category_id INTEGER REFERENCES intent_categories(id) ON DELETE CASCADE,
                pattern_group VARCHAR(50),
                pattern TEXT NOT NULL,
                pattern_type VARCHAR(20) DEFAULT 'exact',
                weight DECIMAL(3,2) DEFAULT 1.0,
                case_sensitive BOOLEAN DEFAULT false,
                enabled BOOLEAN DEFAULT true,
                examples TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100)
            )
        ''')
        print("✓ Created table: intent_patterns")

        # Intent entities table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS intent_entities (
                id SERIAL PRIMARY KEY,
                category_id INTEGER REFERENCES intent_categories(id) ON DELETE CASCADE,
                entity_type VARCHAR(50) NOT NULL,
                entity_value VARCHAR(100) NOT NULL,
                synonyms TEXT[],
                metadata JSONB,
                enabled BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category_id, entity_type, entity_value)
            )
        ''')
        print("✓ Created table: intent_entities")

        # Validation rules table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS validation_rules (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                rule_type VARCHAR(50) NOT NULL,
                intent_category VARCHAR(50),
                pattern TEXT,
                action VARCHAR(50) DEFAULT 'flag',
                severity VARCHAR(20) DEFAULT 'warning',
                message TEXT,
                enabled BOOLEAN DEFAULT true,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: validation_rules")

        # Multi-intent configuration
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS multi_intent_config (
                id SERIAL PRIMARY KEY,
                enabled BOOLEAN DEFAULT true,
                max_intents_per_query INTEGER DEFAULT 3,
                separators TEXT[] DEFAULT ARRAY['and', 'then', 'also'],
                context_preservation BOOLEAN DEFAULT true,
                parallel_processing BOOLEAN DEFAULT false,
                combination_strategy VARCHAR(50) DEFAULT 'concatenate',
                min_words_per_intent INTEGER DEFAULT 2,
                context_words_to_preserve TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: multi_intent_config")

        # Intent chain rules
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS intent_chain_rules (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                trigger_pattern TEXT,
                intent_sequence TEXT[],
                description TEXT,
                examples TEXT[],
                require_all BOOLEAN DEFAULT false,
                stop_on_error BOOLEAN DEFAULT true,
                enabled BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: intent_chain_rules")

        # RAG service configurations
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rag_services (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                display_name VARCHAR(100),
                service_type VARCHAR(50),
                endpoint_url TEXT,
                api_key_encrypted TEXT,
                headers JSONB,
                query_template TEXT,
                response_parser TEXT,
                cache_ttl INTEGER DEFAULT 300,
                timeout INTEGER DEFAULT 5000,
                rate_limit INTEGER DEFAULT 100,
                enabled BOOLEAN DEFAULT true,
                health_check_url TEXT,
                last_health_check TIMESTAMP,
                health_status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: rag_services")

        # RAG service parameters
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rag_service_params (
                id SERIAL PRIMARY KEY,
                service_id INTEGER REFERENCES rag_services(id) ON DELETE CASCADE,
                param_name VARCHAR(50),
                param_type VARCHAR(20),
                default_value TEXT,
                required BOOLEAN DEFAULT false,
                description TEXT,
                validation_regex TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: rag_service_params")

        # RAG response templates
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rag_response_templates (
                id SERIAL PRIMARY KEY,
                service_id INTEGER REFERENCES rag_services(id) ON DELETE CASCADE,
                intent_category VARCHAR(50),
                template_name VARCHAR(100),
                template_text TEXT,
                variables JSONB,
                priority INTEGER DEFAULT 100,
                conditions JSONB,
                enabled BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: rag_response_templates")

        # Query logs for analytics
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS query_logs (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(50),
                query_text TEXT,
                intent_detected VARCHAR(50),
                confidence DECIMAL(3,2),
                response_time_ms INTEGER,
                model_used VARCHAR(50),
                data_source VARCHAR(50),
                validation_passed BOOLEAN,
                user_mode VARCHAR(20),
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: query_logs")

        # Create indexes
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_patterns_category ON intent_patterns(category_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_patterns_enabled ON intent_patterns(enabled)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_entities_category ON intent_entities(category_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_intent ON query_logs(intent_detected)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_created ON query_logs(created_at DESC)')
        print("✓ Created indexes")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Error running Athena migrations: {e}")
        return False


async def run_admin_migrations():
    """Run migrations for admin database"""
    print("\n🔧 Running Admin database migrations...")

    try:
        conn = await asyncpg.connect(ADMIN_DATABASE_URL)

        # Admin users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT true,
                is_superuser BOOLEAN DEFAULT false,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: admin_users")

        # Admin sessions
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES admin_users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: admin_sessions")

        # Configuration audit log
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS config_audit_log (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES admin_users(id),
                action VARCHAR(50) NOT NULL,
                table_name VARCHAR(50) NOT NULL,
                record_id INTEGER,
                old_values JSONB,
                new_values JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: config_audit_log")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Error running Admin migrations: {e}")
        return False


async def seed_initial_data():
    """Seed initial intent patterns and configurations"""
    print("\n🌱 Seeding initial data...")

    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if data already exists
        count = await conn.fetchval("SELECT COUNT(*) FROM intent_categories")
        if count > 0:
            print("✓ Data already seeded")
            await conn.close()
            return True

        # Insert intent categories
        categories = [
            ('control', 'Device Control', 'Smart home device control commands', 200, True, False, 0.85),
            ('weather', 'Weather', 'Weather information queries', 100, True, False, 0.75),
            ('sports', 'Sports', 'Sports scores and information', 100, True, False, 0.75),
            ('airports', 'Airports', 'Flight and airport information', 100, True, False, 0.75),
            ('general_info', 'General Info', 'General information queries', 50, True, True, 0.60),
            ('personal', 'Personal', 'Personal assistant queries', 75, True, True, 0.70),
            ('status', 'Status', 'System and device status queries', 150, True, False, 0.80)
        ]

        for name, display, desc, priority, enabled, requires_llm, threshold in categories:
            await conn.execute('''
                INSERT INTO intent_categories
                (name, display_name, description, priority, enabled, requires_llm, confidence_threshold)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', name, display, desc, priority, enabled, requires_llm, threshold)

        print("✓ Inserted intent categories")

        # Get category IDs
        control_id = await conn.fetchval("SELECT id FROM intent_categories WHERE name = 'control'")
        weather_id = await conn.fetchval("SELECT id FROM intent_categories WHERE name = 'weather'")
        sports_id = await conn.fetchval("SELECT id FROM intent_categories WHERE name = 'sports'")
        airports_id = await conn.fetchval("SELECT id FROM intent_categories WHERE name = 'airports'")

        # Insert intent patterns
        patterns = [
            # Control patterns
            (control_id, 'basic', 'turn on', ['turn on the lights', 'turn on kitchen lights']),
            (control_id, 'basic', 'turn off', ['turn off the TV', 'turn off all lights']),
            (control_id, 'basic', 'toggle', ['toggle the fan', 'toggle bedroom lights']),
            (control_id, 'dimming', 'dim', ['dim the lights', 'dim to 50%']),
            (control_id, 'dimming', 'brighten', ['brighten the lights', 'make it brighter']),
            (control_id, 'temperature', 'set temperature', ['set temperature to 72', 'set thermostat to 68']),
            (control_id, 'temperature', 'warmer', ['make it warmer', 'increase temperature']),
            (control_id, 'temperature', 'cooler', ['make it cooler', 'decrease temperature']),

            # Weather patterns
            (weather_id, 'current', 'weather', ['what is the weather', 'current weather']),
            (weather_id, 'current', 'temperature', ['what is the temperature', 'how hot is it']),
            (weather_id, 'forecast', 'forecast', ['weather forecast', 'forecast for tomorrow']),
            (weather_id, 'forecast', 'rain', ['will it rain', 'is it going to rain']),

            # Sports patterns
            (sports_id, 'teams', 'ravens', ['ravens score', 'did the ravens win', 'ravens game']),
            (sports_id, 'teams', 'orioles', ['orioles score', 'orioles game', 'how did the orioles do']),
            (sports_id, 'scores', 'score', ['what was the score', 'final score']),

            # Airport patterns
            (airports_id, 'flights', 'flight', ['flight status', 'flight information']),
            (airports_id, 'delays', 'delayed', ['is my flight delayed', 'flight delays']),
            (airports_id, 'gates', 'gate', ['what gate', 'gate information']),
        ]

        for cat_id, group, pattern, examples in patterns:
            await conn.execute('''
                INSERT INTO intent_patterns
                (category_id, pattern_group, pattern, examples, enabled)
                VALUES ($1, $2, $3, $4, true)
            ''', cat_id, group, pattern, examples)

        print("✓ Inserted intent patterns")

        # Insert validation rules
        rules = [
            ('no_profanity', 'content', None, r'\b(damn|hell|crap)\b', 'flag', 'warning', 'Mild profanity detected'),
            ('no_hallucination', 'response', None, r'As an AI|I cannot|I don\'t have access', 'replace', 'info', 'Removed AI disclaimer'),
            ('factual_accuracy', 'response', 'weather', r'[0-9]{3,}°', 'validate', 'error', 'Temperature seems unrealistic'),
        ]

        for name, rule_type, category, pattern, action, severity, message in rules:
            await conn.execute('''
                INSERT INTO validation_rules
                (name, rule_type, intent_category, pattern, action, severity, message, enabled)
                VALUES ($1, $2, $3, $4, $5, $6, $7, true)
            ''', name, rule_type, category, pattern, action, severity, message)

        print("✓ Inserted validation rules")

        # Insert multi-intent config
        await conn.execute('''
            INSERT INTO multi_intent_config
            (enabled, max_intents_per_query, separators, context_preservation, parallel_processing)
            VALUES (true, 3, $1, true, false)
        ''', ['and', 'then', 'also', 'plus'])

        print("✓ Inserted multi-intent config")

        # Insert chain rules
        chains = [
            ('goodnight_routine', r'good ?night|bedtime', ['turn off lights', 'lock doors', 'set temperature'],
             'Bedtime routine', ['say goodnight', 'time for bed']),
            ('morning_routine', r'good ?morning|wake up', ['turn on lights', 'weather today', 'news briefing'],
             'Morning routine', ['good morning', 'wake up']),
            ('leaving_home', r'leaving|going out|bye', ['lock doors', 'turn off lights', 'arm security'],
             'Leaving home routine', ['I am leaving', 'goodbye']),
        ]

        for name, trigger, sequence, desc, examples in chains:
            await conn.execute('''
                INSERT INTO intent_chain_rules
                (name, trigger_pattern, intent_sequence, description, examples, enabled)
                VALUES ($1, $2, $3, $4, $5, true)
            ''', name, trigger, sequence, desc, examples)

        print("✓ Inserted chain rules")

        # Insert RAG service configurations
        rag_services = [
            ('weather', 'Weather Service', 'api', 'http://192.168.10.167:8010', None,
             '{"Content-Type": "application/json"}', 600, 5000),
            ('sports', 'Sports Service', 'api', 'http://192.168.10.167:8012', None,
             '{"Content-Type": "application/json"}', 300, 5000),
            ('airports', 'Airports Service', 'api', 'http://192.168.10.167:8011', None,
             '{"Content-Type": "application/json"}', 120, 5000),
        ]

        for name, display, stype, url, key, headers, ttl, timeout in rag_services:
            await conn.execute('''
                INSERT INTO rag_services
                (name, display_name, service_type, endpoint_url, api_key_encrypted,
                 headers, cache_ttl, timeout, enabled)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, true)
            ''', name, display, stype, url, key, headers, ttl, timeout)

        print("✓ Inserted RAG service configurations")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        return False


async def create_admin_user():
    """Create default admin user"""
    print("\n👤 Creating default admin user...")

    try:
        conn = await asyncpg.connect(ADMIN_DATABASE_URL)

        # Check if admin exists
        exists = await conn.fetchval(
            "SELECT id FROM admin_users WHERE username = 'admin'"
        )

        if exists:
            print("✓ Admin user already exists")
        else:
            # Simple hash for demo (should use bcrypt in production)
            import hashlib
            password_hash = hashlib.sha256("admin123".encode()).hexdigest()

            await conn.execute('''
                INSERT INTO admin_users
                (username, email, password_hash, is_superuser)
                VALUES ('admin', 'admin@athena.local', $1, true)
            ''', password_hash)

            print("✅ Created admin user (username: admin, password: admin123)")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False


async def main():
    """Run all migrations"""
    print("=" * 50)
    print("Project Athena Database Migration")
    print("=" * 50)

    # Create databases
    if not await create_databases():
        sys.exit(1)

    # Run migrations
    if not await run_athena_migrations():
        sys.exit(1)

    if not await run_admin_migrations():
        sys.exit(1)

    # Seed data
    if not await seed_initial_data():
        sys.exit(1)

    # Create admin user
    if not await create_admin_user():
        sys.exit(1)

    print("\n✅ All migrations completed successfully!")
    print("\nDatabase ready for use:")
    print(f"  • Athena DB: {DATABASE_URL}")
    print(f"  • Admin DB: {ADMIN_DATABASE_URL}")
    print("\nAdmin credentials:")
    print("  • Username: admin")
    print("  • Password: admin123")


if __name__ == "__main__":
    asyncio.run(main())