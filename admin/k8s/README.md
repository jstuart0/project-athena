# Project Athena - Admin Interface Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the admin interface to the thor cluster.

## Architecture

**Backend:**
- FastAPI service
- Monitors Mac Studio services at 192.168.10.167
- Provides REST API for service status

**Frontend:**
- Static HTML dashboard
- Nginx web server
- Proxies API requests to backend

**Access:**
- URL: https://admin.xmojo.net
- TLS: Automatic via cert-manager
- Ingress: Traefik

## Prerequisites

1. **thor cluster context:**
   ```bash
   kubectl config use-context thor
   ```

2. **Container images built and pushed:**
   ```bash
   # Build backend
   cd admin/backend
   docker build -t ghcr.io/your-username/athena-admin-backend:latest .
   docker push ghcr.io/your-username/athena-admin-backend:latest

   # Build frontend
   cd ../frontend
   docker build -t ghcr.io/your-username/athena-admin-frontend:latest .
   docker push ghcr.io/your-username/athena-admin-frontend:latest
   ```

3. **DNS configured:**
   - Add A record: `admin.xmojo.net` → `192.168.60.50` (Traefik LoadBalancer)
   - Verify: `nslookup admin.xmojo.net`

## Deployment Steps

### 1. Switch to thor cluster

```bash
kubectl config use-context thor
kubectl cluster-info
```

### 2. Deploy manifests

```bash
cd admin/k8s
kubectl apply -f deployment.yaml
```

### 3. Verify deployment

```bash
# Check namespace
kubectl get ns athena-admin

# Check pods
kubectl get pods -n athena-admin

# Check services
kubectl get svc -n athena-admin

# Check ingress
kubectl get ingress -n athena-admin

# Check TLS certificate
kubectl get certificate -n athena-admin
```

### 4. Wait for TLS certificate

```bash
# Watch certificate status
kubectl get certificate -n athena-admin -w

# Should show: READY=True
```

### 5. Access admin interface

```bash
# Test connection
curl -k https://admin.xmojo.net

# Open in browser
open https://admin.xmojo.net
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl describe pod -n athena-admin <pod-name>

# Check logs
kubectl logs -n athena-admin deployment/athena-admin-backend
kubectl logs -n athena-admin deployment/athena-admin-frontend
```

### Ingress not working

```bash
# Check Traefik service
kubectl get svc -n default | grep traefik

# Check ingress details
kubectl describe ingress -n athena-admin athena-admin-ingress

# Check Traefik logs
kubectl logs -n default deployment/traefik
```

### TLS certificate not issued

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check certificate request
kubectl get certificaterequest -n athena-admin

# Check challenge
kubectl get challenge -n athena-admin
```

### Backend can't reach Mac Studio

```bash
# Test from pod
kubectl exec -n athena-admin deployment/athena-admin-backend -- \
  curl http://192.168.10.167:8001/health

# Check if Mac Studio is accessible from cluster network
```

## Updating Deployment

### Update backend code

```bash
# Make changes to backend/main.py
cd admin/backend

# Rebuild and push
docker build -t ghcr.io/your-username/athena-admin-backend:latest .
docker push ghcr.io/your-username/athena-admin-backend:latest

# Restart deployment
kubectl rollout restart deployment/athena-admin-backend -n athena-admin

# Watch rollout
kubectl rollout status deployment/athena-admin-backend -n athena-admin
```

### Update frontend

```bash
# Make changes to frontend/index.html
cd admin/frontend

# Rebuild and push
docker build -t ghcr.io/your-username/athena-admin-frontend:latest .
docker push ghcr.io/your-username/athena-admin-frontend:latest

# Restart deployment
kubectl rollout restart deployment/athena-admin-frontend -n athena-admin
```

## Scaling

```bash
# Scale backend
kubectl scale deployment/athena-admin-backend -n athena-admin --replicas=3

# Scale frontend
kubectl scale deployment/athena-admin-frontend -n athena-admin --replicas=3
```

## Monitoring

```bash
# Watch pod status
kubectl get pods -n athena-admin -w

# Check resource usage
kubectl top pods -n athena-admin

# View logs (all replicas)
kubectl logs -n athena-admin -l app=athena-admin-backend --tail=100
```

## Cleanup

```bash
# Delete everything
kubectl delete namespace athena-admin

# Or delete individual resources
kubectl delete -f deployment.yaml
```

## Production Checklist

- [ ] Container images built and pushed to registry
- [ ] DNS record created (admin.xmojo.net → 192.168.60.50)
- [ ] Deployed to thor cluster
- [ ] Pods running and healthy
- [ ] TLS certificate issued
- [ ] Admin interface accessible at https://admin.xmojo.net
- [ ] All services showing correct status
- [ ] API calls working (test refresh button)

## Notes

- **MAC_STUDIO_IP:** Currently hardcoded to 192.168.10.167 in deployment
- **Image registry:** Update image URLs in deployment.yaml to your registry
- **Replicas:** Backend and frontend run 2 replicas for HA
- **Resources:** Minimal resources allocated (can be increased if needed)
- **Ingress:** Uses existing Traefik ingress controller on thor
- **TLS:** Automatic via cert-manager with Let's Encrypt

## Future Enhancements

- Add authentication (OAuth2/OIDC via Authentik)
- Add metrics dashboard (Grafana integration)
- Add service logs viewer
- Add query testing interface
- Add service restart controls (with auth)
- Add alert configuration
