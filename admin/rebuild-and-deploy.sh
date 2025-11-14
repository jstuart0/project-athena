#!/bin/bash
set -e

echo "=== Rebuilding Frontend with AI Configuration ==="
cd /Users/jaystuart/dev/project-athena/admin/frontend
docker build --platform linux/amd64 -t 192.168.10.222:30500/athena-admin-frontend:latest .
docker push 192.168.10.222:30500/athena-admin-frontend:latest

echo "=== Updating Ingress Configuration ==="
cd /Users/jaystuart/dev/project-athena/admin/k8s
ssh jstuart@192.168.10.167 '/usr/local/bin/kubectl apply -f -' < deployment.yaml

echo "=== Restarting Frontend Deployment ==="
ssh jstuart@192.168.10.167 '/usr/local/bin/kubectl -n athena-admin rollout restart deployment/athena-admin-frontend'

echo "=== Waiting for Rollout ==="
ssh jstuart@192.168.10.167 '/usr/local/bin/kubectl -n athena-admin rollout status deployment/athena-admin-frontend'

echo "=== Deployment Complete ==="
