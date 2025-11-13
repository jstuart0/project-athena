#!/bin/bash
# Project Athena - Mac Studio Deployment Script
# Deploys AI processing layer services to Mac Studio

set -e  # Exit on error

echo "================================"
echo "Project Athena - Mac Studio Deploy"
echo "================================"
echo ""

# Configuration
MAC_STUDIO_IP="192.168.10.167"
MAC_STUDIO_USER="jstuart"
REMOTE_DIR="~/athena"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v ssh &> /dev/null; then
    log_error "SSH not found. Please install SSH client."
    exit 1
fi

if ! command -v scp &> /dev/null; then
    log_error "SCP not found. Please install SCP."
    exit 1
fi

# Test SSH connection
log_info "Testing SSH connection to Mac Studio..."
if ! ssh -o ConnectTimeout=5 ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} "echo 'Connection successful'" &> /dev/null; then
    log_error "Cannot connect to Mac Studio at ${MAC_STUDIO_IP}"
    log_error "Please check network connectivity and SSH access"
    exit 1
fi
log_info "✓ SSH connection successful"

# Create remote directory structure
log_info "Creating remote directory structure..."
ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} << 'EOF'
mkdir -p ~/athena/{piper,whisper,gateway,orchestrator}/{data,models,config}
mkdir -p ~/athena/logs
echo "Directory structure created"
EOF
log_info "✓ Remote directories created"

# Copy docker-compose.yml
log_info "Copying docker-compose.yml to Mac Studio..."
scp ${SCRIPT_DIR}/docker-compose.yml ${MAC_STUDIO_USER}@${MAC_STUDIO_IP}:${REMOTE_DIR}/
log_info "✓ docker-compose.yml copied"

# Copy README
log_info "Copying README.md to Mac Studio..."
scp ${SCRIPT_DIR}/README.md ${MAC_STUDIO_USER}@${MAC_STUDIO_IP}:${REMOTE_DIR}/
log_info "✓ README.md copied"

# Check Docker installation
log_info "Checking Docker installation on Mac Studio..."
ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} << 'EOF'
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed on Mac Studio"
    echo "Please install Docker Desktop for Mac first:"
    echo "  https://docs.docker.com/desktop/install/mac-install/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose is not available"
    echo "Please ensure Docker Compose is installed"
    exit 1
fi

echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker compose version)"
EOF

if [ $? -ne 0 ]; then
    log_error "Docker check failed. Please install Docker on Mac Studio."
    exit 1
fi
log_info "✓ Docker is installed"

# Pull Docker images
log_info "Pulling Docker images (this may take a few minutes)..."
ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} << 'EOF'
cd ~/athena
docker compose pull
EOF
log_info "✓ Docker images pulled"

# Start services
log_info "Starting services..."
ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} << 'EOF'
cd ~/athena
docker compose up -d
EOF
log_info "✓ Services started"

# Wait for services to be healthy
log_info "Waiting for services to be healthy (30 seconds)..."
sleep 30

# Check service health
log_info "Checking service health..."
ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP} << 'EOF'
cd ~/athena
echo ""
echo "Container Status:"
docker compose ps
echo ""

# Test service endpoints (if available)
echo "Testing service health endpoints:"

# Gateway
if curl -sf http://localhost:8000/health &> /dev/null; then
    echo "✓ Gateway (8000): HEALTHY"
else
    echo "✗ Gateway (8000): NOT RESPONDING"
fi

# Orchestrator
if curl -sf http://localhost:8001/health &> /dev/null; then
    echo "✓ Orchestrator (8001): HEALTHY"
else
    echo "✗ Orchestrator (8001): NOT RESPONDING"
fi

# Piper TTS (Wyoming protocol - TCP check)
if timeout 2 bash -c "</dev/tcp/localhost/10200" 2>/dev/null; then
    echo "✓ Piper TTS (10200): LISTENING"
else
    echo "✗ Piper TTS (10200): NOT LISTENING"
fi

# Whisper STT (Wyoming protocol - TCP check)
if timeout 2 bash -c "</dev/tcp/localhost/10300" 2>/dev/null; then
    echo "✓ Whisper STT (10300): LISTENING"
else
    echo "✗ Whisper STT (10300): NOT LISTENING"
fi
EOF

echo ""
log_info "================================"
log_info "Deployment Complete!"
log_info "================================"
echo ""
echo "Service URLs:"
echo "  Gateway:      http://192.168.10.167:8000"
echo "  Orchestrator: http://192.168.10.167:8001"
echo "  Piper TTS:    tcp://192.168.10.167:10200 (Wyoming)"
echo "  Whisper STT:  tcp://192.168.10.167:10300 (Wyoming)"
echo ""
echo "View logs:"
echo "  ssh ${MAC_STUDIO_USER}@${MAC_STUDIO_IP}"
echo "  cd ~/athena"
echo "  docker compose logs -f"
echo ""
echo "For troubleshooting, see: ${REMOTE_DIR}/README.md"
echo ""
