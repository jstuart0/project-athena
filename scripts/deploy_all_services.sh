#!/bin/bash

set -e

echo "=========================================="
echo "Project Athena - Full Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check current directory
if [ ! -f "README.md" ] || [ ! -d "src" ]; then
    echo -e "${RED}Error: Must run from project root directory${NC}"
    exit 1
fi

PROJECT_ROOT=$(pwd)

echo -e "${GREEN}Step 1: Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
else
    echo -e "${YELLOW}Warning: .env file not found, using defaults${NC}"

    # Create default .env file
    cat > .env << EOF
# Home Assistant
HA_URL=https://192.168.10.168:8123
HA_TOKEN=${HA_TOKEN:-your-ha-token-here}

# LLM Service (Ollama on Mac Studio)
LLM_SERVICE_URL=http://192.168.10.167:11434
OLLAMA_URL=http://192.168.10.167:11434

# Database
DATABASE_URL=postgresql://psadmin:${DB_PASSWORD:-password}@192.168.10.14:5432/athena
REDIS_URL=redis://192.168.10.181:6379

# RAG Services (Mac Studio)
RAG_WEATHER_URL=http://192.168.10.167:8010
RAG_AIRPORTS_URL=http://192.168.10.167:8011
RAG_SPORTS_URL=http://192.168.10.167:8012

# Orchestrator
ORCHESTRATOR_SERVICE_URL=http://192.168.10.167:8001

# Gateway
GATEWAY_API_KEY=athena-gateway-key-2024
GATEWAY_PORT=8000
ORCHESTRATOR_PORT=8001

# Admin Interface
ADMIN_DATABASE_URL=postgresql://psadmin:${DB_PASSWORD:-password}@192.168.10.14:5432/athena_admin
EOF
    echo -e "${YELLOW}Created default .env file - please update with actual values${NC}"
fi

echo ""
echo -e "${GREEN}Step 2: Creating/updating database...${NC}"

# Check if PostgreSQL is accessible
if pg_isready -h 192.168.10.14 -p 5432 -U psadmin &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is accessible${NC}"

    # Create databases if they don't exist
    PGPASSWORD=${DB_PASSWORD:-password} psql -h 192.168.10.14 -U psadmin -d postgres << EOF 2>/dev/null || true
CREATE DATABASE athena;
CREATE DATABASE athena_admin;
EOF
    echo -e "${GREEN}✓ Databases created/verified${NC}"
else
    echo -e "${YELLOW}Warning: Cannot connect to PostgreSQL at 192.168.10.14${NC}"
    echo -e "${YELLOW}Database setup will need to be done manually${NC}"
fi

echo ""
echo -e "${GREEN}Step 3: Building Docker images...${NC}"

# Build Gateway
echo "Building Gateway image..."
docker build -t athena-gateway:latest -f src/gateway/Dockerfile src/gateway/
echo -e "${GREEN}✓ Gateway image built${NC}"

# Build Orchestrator
echo "Building Orchestrator image..."
docker build -t athena-orchestrator:latest -f src/orchestrator/Dockerfile src/orchestrator/
echo -e "${GREEN}✓ Orchestrator image built${NC}"

echo ""
echo -e "${GREEN}Step 4: Creating Docker Compose configuration...${NC}"

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  orchestrator:
    image: athena-orchestrator:latest
    container_name: athena-orchestrator
    restart: unless-stopped
    ports:
      - "8001:8001"
    environment:
      - HA_URL=${HA_URL}
      - HA_TOKEN=${HA_TOKEN}
      - OLLAMA_URL=${OLLAMA_URL}
      - LLM_SERVICE_URL=${LLM_SERVICE_URL}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - RAG_WEATHER_URL=${RAG_WEATHER_URL}
      - RAG_AIRPORTS_URL=${RAG_AIRPORTS_URL}
      - RAG_SPORTS_URL=${RAG_SPORTS_URL}
      - LOG_LEVEL=INFO
    networks:
      - athena-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - ./src/shared:/app/shared:ro
      - ./src/orchestrator:/app:ro

  gateway:
    image: athena-gateway:latest
    container_name: athena-gateway
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ORCHESTRATOR_SERVICE_URL=${ORCHESTRATOR_SERVICE_URL:-http://orchestrator:8001}
      - LLM_SERVICE_URL=${LLM_SERVICE_URL}
      - GATEWAY_API_KEY=${GATEWAY_API_KEY}
      - LOG_LEVEL=INFO
    networks:
      - athena-network
    depends_on:
      - orchestrator
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - ./src/gateway:/app:ro

networks:
  athena-network:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
EOF

echo -e "${GREEN}✓ Docker Compose configuration created${NC}"

echo ""
echo -e "${GREEN}Step 5: Stopping existing services...${NC}"

# Stop and remove existing containers
docker-compose down 2>/dev/null || true
docker stop athena-gateway athena-orchestrator 2>/dev/null || true
docker rm athena-gateway athena-orchestrator 2>/dev/null || true

echo -e "${GREEN}✓ Existing services stopped${NC}"

echo ""
echo -e "${GREEN}Step 6: Starting services...${NC}"

# Start services with docker-compose
if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo -e "${GREEN}Step 7: Waiting for services to be ready...${NC}"

# Function to check service health
check_service() {
    local service_name=$1
    local service_url=$2
    local max_attempts=30
    local attempt=1

    echo -n "Waiting for $service_name..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s $service_url > /dev/null; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e " ${RED}✗${NC}"
    return 1
}

# Check services
check_service "Orchestrator" "http://localhost:8001/health"
check_service "Gateway" "http://localhost:8000/health"

echo ""
echo -e "${GREEN}Step 8: Running database migrations...${NC}"

# Create Python script to run migrations
cat > /tmp/run_migrations.py << 'EOF'
#!/usr/bin/env python3
import asyncio
import asyncpg
import os
import sys

async def run_migrations():
    try:
        # Get database URL from environment
        db_url = os.getenv('DATABASE_URL', 'postgresql://psadmin:password@192.168.10.14:5432/athena')

        # Connect to database
        conn = await asyncpg.connect(db_url)

        print("Creating intent configuration tables...")

        # Create tables
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

        print("✓ Intent configuration tables created")

        # Insert seed data if tables are empty
        count = await conn.fetchval("SELECT COUNT(*) FROM intent_categories")

        if count == 0:
            print("Seeding initial intent data...")

            # Insert categories
            await conn.execute('''
                INSERT INTO intent_categories (name, display_name, description, priority, cache_ttl)
                VALUES
                ('control', 'Device Control', 'Smart home device control commands', 200, 0),
                ('weather', 'Weather', 'Weather information queries', 100, 600),
                ('sports', 'Sports', 'Sports scores and information', 100, 300),
                ('airports', 'Airports', 'Flight and airport information', 100, 120),
                ('general_info', 'General Info', 'General information queries', 50, 300)
            ''')

            # Get category IDs
            control_id = await conn.fetchval("SELECT id FROM intent_categories WHERE name = 'control'")
            weather_id = await conn.fetchval("SELECT id FROM intent_categories WHERE name = 'weather'")
            sports_id = await conn.fetchval("SELECT id FROM intent_categories WHERE name = 'sports'")

            # Insert patterns
            patterns = [
                (control_id, 'basic', 'turn on', ['turn on the lights']),
                (control_id, 'basic', 'turn off', ['turn off the TV']),
                (control_id, 'dimming', 'dim', ['dim the lights to 50%']),
                (weather_id, 'current', 'weather', ['what is the weather']),
                (weather_id, 'forecast', 'forecast', ['weather forecast for tomorrow']),
                (sports_id, 'teams', 'ravens', ['ravens score', 'did the ravens win']),
                (sports_id, 'teams', 'orioles', ['orioles game', 'orioles score'])
            ]

            for cat_id, group, pattern, examples in patterns:
                await conn.execute('''
                    INSERT INTO intent_patterns (category_id, pattern_group, pattern, examples)
                    VALUES ($1, $2, $3, $4)
                ''', cat_id, group, pattern, examples)

            print("✓ Initial intent data seeded")

        await conn.close()
        print("✓ Database migrations completed successfully")
        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migrations())
    sys.exit(0 if success else 1)
EOF

# Run migrations
python3 /tmp/run_migrations.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database migrations completed${NC}"
else
    echo -e "${YELLOW}Warning: Database migrations may have failed${NC}"
fi

echo ""
echo -e "${GREEN}Step 9: Running health checks...${NC}"

# Health check function
run_health_check() {
    local service=$1
    local url=$2

    echo -n "Checking $service health... "
    response=$(curl -s $url)

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC}"
        echo "  Response: $(echo $response | head -c 100)..."
    else
        echo -e "${RED}✗${NC}"
    fi
}

run_health_check "Gateway" "http://localhost:8000/health"
run_health_check "Orchestrator" "http://localhost:8001/health"
run_health_check "Gateway Models" "http://localhost:8000/v1/models"
run_health_check "Orchestrator Metrics" "http://localhost:8001/metrics"

echo ""
echo -e "${GREEN}Step 10: Running integration tests...${NC}"

# Create simple integration test
cat > /tmp/test_integration.py << 'EOF'
#!/usr/bin/env python3
import requests
import json
import sys

def test_gateway():
    """Test gateway OpenAI endpoint"""
    try:
        response = requests.post(
            "http://localhost:8000/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer athena-gateway-key-2024"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "Hello, this is a test"}
                ]
            },
            timeout=10
        )

        if response.status_code == 200:
            print("✓ Gateway test passed")
            return True
        else:
            print(f"✗ Gateway test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Gateway test error: {e}")
        return False

def test_orchestrator():
    """Test orchestrator directly"""
    try:
        response = requests.post(
            "http://localhost:8001/query",
            headers={"Content-Type": "application/json"},
            json={
                "query": "What time is it?",
                "mode": "owner"
            },
            timeout=10
        )

        if response.status_code == 200:
            print("✓ Orchestrator test passed")
            return True
        else:
            print(f"✗ Orchestrator test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Orchestrator test error: {e}")
        return False

if __name__ == "__main__":
    gateway_ok = test_gateway()
    orchestrator_ok = test_orchestrator()

    if gateway_ok and orchestrator_ok:
        print("\n✓ All integration tests passed")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
EOF

python3 /tmp/test_integration.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${YELLOW}Warning: Some integration tests failed${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Services deployed:"
echo "  • Gateway:      http://localhost:8000"
echo "  • Orchestrator: http://localhost:8001"
echo ""
echo "Available endpoints:"
echo "  • OpenAI API:   http://localhost:8000/v1/chat/completions"
echo "  • Health:       http://localhost:8000/health"
echo "  • Metrics:      http://localhost:8001/metrics"
echo "  • Models:       http://localhost:8000/v1/models"
echo ""
echo "Next steps:"
echo "  1. Configure Home Assistant to use http://192.168.10.167:8000/v1"
echo "  2. Test with: curl -X POST http://localhost:8000/v1/chat/completions \\"
echo "                     -H 'Content-Type: application/json' \\"
echo "                     -H 'Authorization: Bearer athena-gateway-key-2024' \\"
echo "                     -d '{\"model\":\"gpt-3.5-turbo\",\"messages\":[{\"role\":\"user\",\"content\":\"Turn on the lights\"}]}'"
echo ""
echo "View logs:"
echo "  • docker logs -f athena-gateway"
echo "  • docker logs -f athena-orchestrator"
echo ""
echo "Stop services:"
echo "  • docker-compose down"
echo ""

# Clean up temp files
rm -f /tmp/run_migrations.py /tmp/test_integration.py