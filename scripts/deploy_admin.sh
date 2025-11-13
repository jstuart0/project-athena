#!/bin/bash

# Deploy Admin Interface on Mac Studio
set -e

echo "Deploying Admin Interface..."

# Install admin backend dependencies
echo "Installing admin backend dependencies..."
pip3 install --user fastapi uvicorn sqlalchemy asyncpg psycopg2-binary alembic pydantic httpx

# Start admin backend
echo "Starting admin backend on port 8080..."
cd ~/dev/project-athena/admin/backend
export DATABASE_URL="postgresql://psadmin:Ibucej1!@postgres-01.xmojo.net:5432/athena_admin"
export PYTHONPATH="/Users/jstuart/dev/project-athena:/Users/jstuart/dev/project-athena/admin/backend"
export SECRET_KEY="athena-admin-secret-key-2024"
export CORS_ORIGINS='["http://localhost:8080", "http://192.168.10.167:8080", "http://192.168.10.167:8081"]'

# Kill existing admin process if any
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
sleep 2

# Start the admin backend
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 > admin.log 2>&1 &
echo "Admin backend PID: $!"

# Start admin frontend (simple Python HTTP server)
echo "Starting admin frontend on port 8081..."
cd ~/dev/project-athena/admin/frontend

# Kill existing frontend process if any
lsof -ti:8081 | xargs kill -9 2>/dev/null || true
sleep 2

# Start simple HTTP server for frontend
nohup python3 -m http.server 8081 > frontend.log 2>&1 &
echo "Admin frontend PID: $!"

echo ""
echo "Admin Interface deployed!"
echo "  • Admin Backend: http://192.168.10.167:8080"
echo "  • Admin Frontend: http://192.168.10.167:8081"
echo ""
echo "Default credentials:"
echo "  • Username: admin"
echo "  • Password: admin123"
echo ""
echo "Check logs:"
echo "  • tail -f ~/dev/project-athena/admin/backend/admin.log"
echo "  • tail -f ~/dev/project-athena/admin/frontend/frontend.log"