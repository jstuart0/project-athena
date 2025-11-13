# Admin Interface Ready to Deploy

## Current Status
**Date:** 2025-11-13
**Status:** Build script updated for sidebar layout - READY for deployment

## What's Ready

### Files Updated for Sidebar Layout
1. **build-and-deploy.sh** - Updated with:
   - Verification that index.html and app.js exist
   - Enhanced nginx configuration with:
     - Gzip compression for text/css/js/json
     - Cache headers for static assets (1 hour expiry)
     - WebSocket support for real-time updates
     - Security headers (X-Frame-Options, X-Content-Type-Options)
   - Proper MIME type handling

2. **Frontend Files** (already exist):
   - `admin/frontend/index.html` - Contains sidebar layout with Tailwind CSS
   - `admin/frontend/app.js` - Frontend JavaScript application
   - `admin/frontend/Dockerfile` - Nginx-based container

3. **Backend Files** (already exist):
   - `admin/backend/main.py` - FastAPI application
   - `admin/backend/app/` - Application modules
   - `admin/backend/requirements.txt` - Python dependencies
   - `admin/backend/Dockerfile` - Python container

4. **Kubernetes Manifests** (already exist):
   - `admin/k8s/deployment.yaml` - Complete K8s deployment
   - `admin/k8s/create-secrets.sh` - Creates required secrets
   - `admin/k8s/postgres.yaml` - PostgreSQL (if needed locally)
   - `admin/k8s/redis.yaml` - Redis (if needed locally)

## Deployment Command

From a machine with kubectl access to Thor cluster:

```bash
# Navigate to the k8s directory
cd /Users/jaystuart/dev/project-athena/admin/k8s

# Make script executable
chmod +x build-and-deploy.sh

# Run the deployment
./build-and-deploy.sh
```

## What the Script Does

1. **Checks Prerequisites**
   - Verifies Docker is installed
   - Verifies kubectl is installed
   - Switches to thor context
   - Verifies cluster access

2. **Builds Docker Images**
   - Backend: athena-admin-backend:v1.0.0
   - Frontend: athena-admin-frontend:v1.0.0 (with sidebar layout)

3. **Pushes to Thor Registry**
   - Registry: 192.168.10.222:30500
   - Tags both with version and latest

4. **Creates Secrets**
   - Database credentials (postgres-01.xmojo.net)
   - Session and JWT secrets
   - OIDC placeholders for Authentik

5. **Deploys to Kubernetes**
   - Namespace: athena-admin
   - Backend: 2 replicas
   - Frontend: 2 replicas
   - Ingress: https://athena-admin.xmojo.net

6. **Verifies Deployment**
   - Waits for rollout completion
   - Shows pod status
   - Shows service and ingress info

## Post-Deployment Tasks

1. **Configure Authentik OIDC** (if using authentication):
   ```bash
   kubectl -n athena-admin edit secret athena-admin-oidc
   ```
   Update OIDC_CLIENT_ID and OIDC_CLIENT_SECRET with real values.

2. **Verify Access**:
   - Frontend: https://athena-admin.xmojo.net
   - Backend API: https://athena-admin.xmojo.net/api

3. **Monitor Logs**:
   ```bash
   kubectl -n athena-admin logs -f deployment/athena-admin-backend
   kubectl -n athena-admin logs -f deployment/athena-admin-frontend
   ```

## Database Configuration

The admin interface uses:
- **Host:** postgres-01.xmojo.net
- **Database:** athena_admin
- **User:** psadmin
- **Password:** Ibucej1! (URL-encoded in connection strings)

## Features in Sidebar Layout

The updated interface includes:
- **Dark theme** with improved visual hierarchy
- **Collapsible sidebar** (240px width)
- **Navigation sections**:
  - Dashboard
  - Intent Configuration
  - RAG Services
  - Validation Rules
  - Multi-Intent Config
  - Query Logs
  - Configuration Audit
- **Responsive design** with Tailwind CSS
- **Real-time updates** via WebSocket support

## Security Notes

- Never commit actual credentials to git
- All secrets are stored in Kubernetes secrets
- OIDC integration provides SSO via Authentik
- Database password is URL-encoded for special characters

## Support

For issues during deployment:
1. Check pod logs for errors
2. Verify database connectivity
3. Ensure Thor cluster is accessible
4. Check ingress and TLS certificates

## Related Services Status

Currently deployed and running:
- **Gateway:** http://192.168.10.167:8000 ✅
- **Orchestrator:** http://192.168.10.167:8001 ✅ (degraded - HA not available)
- **Database:** postgres-01.xmojo.net ✅
- **Redis:** redis://192.168.10.181:6379 ✅
- **Ollama:** http://192.168.10.167:11434 ✅