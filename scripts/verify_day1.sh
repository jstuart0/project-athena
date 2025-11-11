#!/bin/bash
#
# Project Athena - Day 1 Verification Script
#
# This script checks if all Day 1 prerequisites are met:
#   - Network connectivity (Mac Studio, Mac mini, Home Assistant)
#   - Docker running on both Macs
#   - Ollama installed and models downloaded
#   - Mac mini services (Qdrant, Redis) running
#   - Environment configuration (.env file)
#
# Usage:
#   bash scripts/verify_day1.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAC_STUDIO_IP="192.168.10.20"
MAC_MINI_IP="192.168.10.181"
HA_IP="192.168.10.168"
QDRANT_PORT="6333"
REDIS_PORT="6379"
OLLAMA_PORT="11434"

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_check() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

print_info() {
    echo -e "       $1"
}

# Start verification
print_header "Project Athena - Day 1 Verification"

# =============================================================================
# Network Connectivity
# =============================================================================
print_header "1. Network Connectivity"

# Check Mac mini
print_check "Testing Mac mini connectivity (${MAC_MINI_IP})..."
if ping -c 1 -W 2 ${MAC_MINI_IP} &> /dev/null; then
    print_pass "Mac mini is reachable at ${MAC_MINI_IP}"
else
    print_fail "Cannot reach Mac mini at ${MAC_MINI_IP}"
    print_info "Run: ping ${MAC_MINI_IP}"
fi

# Check Home Assistant
print_check "Testing Home Assistant connectivity (${HA_IP})..."
if ping -c 1 -W 2 ${HA_IP} &> /dev/null; then
    print_pass "Home Assistant is reachable at ${HA_IP}"
else
    print_fail "Cannot reach Home Assistant at ${HA_IP}"
    print_info "Run: ping ${HA_IP}"
fi

# =============================================================================
# Local Environment (Mac Studio)
# =============================================================================
print_header "2. Mac Studio Environment"

# Check Homebrew
print_check "Checking Homebrew installation..."
if command -v brew &> /dev/null; then
    brew_version=$(brew --version | head -n1)
    print_pass "Homebrew installed: ${brew_version}"
else
    print_fail "Homebrew not installed"
    print_info "Install: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
fi

# Check Docker
print_check "Checking Docker installation..."
if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    print_pass "Docker installed: ${docker_version}"

    # Check if Docker is running
    print_check "Checking if Docker is running..."
    if docker ps &> /dev/null; then
        print_pass "Docker daemon is running"
    else
        print_fail "Docker is installed but not running"
        print_info "Start Docker Desktop or run: open /Applications/Docker.app"
    fi
else
    print_fail "Docker not installed"
    print_info "Install: brew install docker"
fi

# Check Python
print_check "Checking Python installation..."
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    print_pass "Python installed: ${python_version}"
else
    print_fail "Python3 not installed"
    print_info "Install: brew install python@3.11"
fi

# Check virtual environment
print_check "Checking Python virtual environment..."
if [ -d "venv" ]; then
    print_pass "Virtual environment exists at ./venv"
else
    print_warn "Virtual environment not found"
    print_info "Create: python3 -m venv venv"
fi

# Check Ollama
print_check "Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    ollama_version=$(ollama --version)
    print_pass "Ollama installed: ${ollama_version}"

    # Check if Ollama is running
    print_check "Checking if Ollama is running..."
    if curl -s http://localhost:${OLLAMA_PORT}/api/tags &> /dev/null; then
        print_pass "Ollama service is running on port ${OLLAMA_PORT}"

        # Check models
        print_check "Checking Ollama models..."
        models=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}')

        if echo "$models" | grep -q "phi3:mini-q8"; then
            print_pass "Small model found: phi3:mini-q8"
        else
            print_warn "Small model not found: phi3:mini-q8"
            print_info "Pull: ollama pull phi3:mini-q8"
        fi

        if echo "$models" | grep -q "llama3.1:8b-q4"; then
            print_pass "Medium model found: llama3.1:8b-q4"
        else
            print_warn "Medium model not found: llama3.1:8b-q4"
            print_info "Pull: ollama pull llama3.1:8b-q4"
        fi
    else
        print_fail "Ollama is installed but not running"
        print_info "Start: ollama serve &"
    fi
else
    print_fail "Ollama not installed"
    print_info "Install: brew install ollama"
fi

# =============================================================================
# Mac mini Services
# =============================================================================
print_header "3. Mac mini Services"

# Check Qdrant
print_check "Checking Qdrant service..."
if curl -sf http://${MAC_MINI_IP}:${QDRANT_PORT}/healthz &> /dev/null; then
    qdrant_version=$(curl -s http://${MAC_MINI_IP}:${QDRANT_PORT}/healthz | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_pass "Qdrant is running (version: ${qdrant_version})"
else
    print_fail "Qdrant is not accessible at ${MAC_MINI_IP}:${QDRANT_PORT}"
    print_info "Deploy: cd deployment/mac-mini && docker compose up -d"
fi

# Check Redis
print_check "Checking Redis service..."
if command -v redis-cli &> /dev/null; then
    if redis-cli -h ${MAC_MINI_IP} PING 2>/dev/null | grep -q "PONG"; then
        print_pass "Redis is running and responding to PING"
    else
        print_fail "Redis is not accessible at ${MAC_MINI_IP}:${REDIS_PORT}"
        print_info "Deploy: cd deployment/mac-mini && docker compose up -d"
    fi
else
    print_warn "redis-cli not installed locally (Redis may still be running on Mac mini)"
    print_info "Install: brew install redis"
fi

# =============================================================================
# Configuration Files
# =============================================================================
print_header "4. Configuration Files"

# Check .env file
print_check "Checking .env configuration..."
if [ -f "config/env/.env" ]; then
    print_pass "Environment file exists: config/env/.env"

    # Check critical variables
    if grep -q "HA_TOKEN=your_long_lived_token_here" config/env/.env; then
        print_warn "HA_TOKEN not configured (still has placeholder)"
        print_info "Get token from: https://${HA_IP}:8123 → Profile → Long-Lived Access Tokens"
    else
        print_pass "HA_TOKEN appears to be configured"
    fi

    if grep -q "OPENWEATHER_API_KEY=get_this_today" config/env/.env; then
        print_warn "OPENWEATHER_API_KEY not configured (still has placeholder)"
        print_info "Get key from: https://openweathermap.org/api"
    else
        print_pass "OPENWEATHER_API_KEY appears to be configured"
    fi
else
    print_fail "Environment file not found: config/env/.env"
    print_info "Copy template: cp config/env/.env.template config/env/.env"
    print_info "Then edit config/env/.env with actual values"
fi

# Check .gitignore
print_check "Checking .gitignore for .env protection..."
if [ -f ".gitignore" ]; then
    if grep -q "config/env/.env" .gitignore || grep -q "*.env" .gitignore; then
        print_pass ".env files are protected in .gitignore"
    else
        print_warn ".env files may not be protected in .gitignore"
        print_info "Add: echo 'config/env/.env' >> .gitignore"
    fi
else
    print_warn ".gitignore not found"
fi

# =============================================================================
# API Keys
# =============================================================================
print_header "5. API Keys (Phase 1)"

if [ -f "config/env/.env" ]; then
    source config/env/.env 2>/dev/null || true

    # OpenWeatherMap
    print_check "Testing OpenWeatherMap API key..."
    if [ ! -z "$OPENWEATHER_API_KEY" ] && [ "$OPENWEATHER_API_KEY" != "get_this_today" ]; then
        if curl -sf "https://api.openweathermap.org/data/2.5/weather?q=Baltimore&appid=${OPENWEATHER_API_KEY}&units=imperial" &> /dev/null; then
            print_pass "OpenWeatherMap API key is valid"
        else
            print_fail "OpenWeatherMap API key is invalid or not working"
        fi
    else
        print_warn "OpenWeatherMap API key not configured"
        print_info "See: docs/API_KEY_GUIDE.md"
    fi

    # FlightAware
    print_check "Checking FlightAware API key..."
    if [ ! -z "$FLIGHTAWARE_API_KEY" ] && [ "$FLIGHTAWARE_API_KEY" != "get_this_week" ]; then
        print_pass "FlightAware API key is configured"
    else
        print_warn "FlightAware API key not configured"
        print_info "See: docs/API_KEY_GUIDE.md"
    fi

    # TheSportsDB
    print_check "Checking TheSportsDB API key..."
    if [ ! -z "$THESPORTSDB_API_KEY" ]; then
        print_pass "TheSportsDB API key is configured"
    else
        print_warn "TheSportsDB API key not configured"
        print_info "See: docs/API_KEY_GUIDE.md"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
print_header "Verification Summary"

echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${YELLOW}Warnings: ${WARNINGS}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All Day 1 checks passed! You're ready to proceed.${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Some warnings found. Review above and address if needed.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please address the issues above before proceeding.${NC}"
    exit 1
fi
