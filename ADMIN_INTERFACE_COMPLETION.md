# Admin Interface Deployment - Final Steps

**Status:** 95% Complete - Requires Manual Image Loading on Nodes

## What's Done ✅

1. ✅ Docker images built successfully
2. ✅ Images pushed to thor local registry at `192.168.10.222:30500`
3. ✅ Kubernetes manifests created and deployed
4. ✅ Namespace `athena-admin` created
5. ✅ Services and Ingress configured
6. ✅ Hostname set to `athena-admin.xmojo.net`
7. ✅ SSL/TLS configured via cert-manager

## What's Pending ⏸️

**Issue:** Kubernetes nodes cannot pull from the insecure local registry

**Reason:** Containerd on the thor cluster nodes needs configuration to trust the HTTP registry at `192.168.10.222:30500`

## Solution: Manual Image Loading

Since the automatic containerd configuration is complex, the simplest solution is to manually load the images on each node.

### Step-by-Step Instructions

#### Option 1: Load Images Directly on Nodes (Recommended)

**Images are already exported at:**
- `/tmp/backend.tar.gz` (58MB)
- `/tmp/frontend.tar.gz` (21MB)

**1. Copy images to a thor node:**
```bash
# Get the list of nodes
kubectl get nodes

# Copy to node-01 (or any worker node)
scp /tmp/backend.tar.gz root@192.168.10.11:/tmp/
scp /tmp/frontend.tar.gz root@192.168.10.11:/tmp/
```

**2. SSH to the node and load images:**
```bash
ssh root@192.168.10.11

# Load images into containerd
ctr -n k8s.io image import /tmp/backend.tar.gz
ctr -n k8s.io image import /tmp/frontend.tar.gz

# Verify images are loaded
ctr -n k8s.io image ls | grep athena-admin

# Clean up
rm /tmp/backend.tar.gz /tmp/frontend.tar.gz
```

**3. Repeat for all worker nodes:**
```bash
# For node-02
scp /tmp/*.tar.gz root@192.168.10.12:/tmp/
ssh root@192.168.10.12 "ctr -n k8s.io image import /tmp/backend.tar.gz && ctr -n k8s.io image import /tmp/frontend.tar.gz"

# For node-03
scp /tmp/*.tar.gz root@192.168.10.13:/tmp/
ssh root@192.168.10.13 "ctr -n k8s.io image import /tmp/backend.tar.gz && ctr -n k8s.io image import /tmp/frontend.tar.gz"
```

**4. Delete and recreate the pods:**
```bash
kubectl -n athena-admin delete pods --all

# Wait for pods to recreate
kubectl -n athena-admin get pods -w
```

**5. Verify deployment:**
```bash
# Check all pods are running
kubectl -n athena-admin get pods

# Check services
kubectl -n athena-admin get svc

# Check ingress
kubectl -n athena-admin get ingress
```

#### Option 2: Fix Containerd Configuration (Advanced)

If you want the registry to work properly for future deployments:

**1. Add containerd config on each node:**
```bash
# SSH to each node
ssh root@192.168.10.11

# Create registry config
mkdir -p /etc/containerd/certs.d/192.168.10.222:30500

cat > /etc/containerd/certs.d/192.168.10.222:30500/hosts.toml <<EOF
server = "http://192.168.10.222:30500"

[host."http://192.168.10.222:30500"]
  capabilities = ["pull", "resolve"]
  skip_verify = true
EOF

# Restart containerd
systemctl restart containerd

# Verify containerd restarted
systemctl status containerd
```

**2. Repeat for all nodes** (192.168.10.11, .12, .13)

**3. Delete pods to recreate them:**
```bash
kubectl -n athena-admin delete pods --all
kubectl -n athena-admin get pods -w
```

### Configure Cloudflare DNS

Once the pods are running, add the DNS record:

**1. Log into Cloudflare Dashboard**

**2. Select zone:** `xmojo.net`

**3. Add A record:**
- **Name:** `athena-admin`
- **IPv4 address:** `192.168.60.50` (Traefik load balancer)
- **Proxy status:** DNS only (gray cloud)
- **TTL:** Auto

**4. Wait for DNS propagation** (usually 1-5 minutes)

**5. Verify DNS:**
```bash
nslookup athena-admin.xmojo.net
# Should return: 192.168.60.50
```

### Verify SSL Certificate

Cert-manager will automatically provision an SSL certificate:

**1. Check certificate status:**
```bash
kubectl -n athena-admin get certificate
kubectl -n athena-admin describe certificate athena-admin-tls
```

**2. Wait for certificate to be ready** (usually 1-2 minutes after DNS propag)

**3. Check ingress:**
```bash
kubectl -n athena-admin get ingress athena-admin-ingress
```

### Access the Admin Interface

**Once everything is running:**

1. **Open browser:** https://athena-admin.xmojo.net

2. **You should see:**
   - Athena Admin Dashboard
   - Real-time status of all 14 Mac Studio services
   - Dark theme interface with auto-refresh

3. **If you see SSL errors:**
   - Wait a few minutes for cert-manager to provision certificate
   - Check certificate status: `kubectl -n athena-admin get certificate`

## Current Deployment State

**Kubernetes Resources Created:**
```bash
# View all resources
kubectl -n athena-admin get all

# Expected output:
# - 2 backend pods (replicas)
# - 2 frontend pods (replicas)
# - backend service (ClusterIP)
# - frontend service (ClusterIP)
# - ingress (with TLS)
```

**Images Available:**
- Local: `/tmp/backend.tar.gz` `/tmp/frontend.tar.gz`
- Registry: `192.168.10.222:30500/athena-admin-backend:latest`
- Registry: `192.168.10.222:30500/athena-admin-frontend:latest`

**Manifests:**
- Location: `admin/k8s/deployment.yaml`
- Already applied to thor cluster

## Troubleshooting

### Pods Still in ImagePullBackOff

**Check pod events:**
```bash
kubectl -n athena-admin describe pod <pod-name>
```

**If you see "http: server gave HTTP response to HTTPS client":**
- Images need to be loaded manually (Option 1 above)
- OR containerd needs insecure registry config (Option 2 above)

### Certificate Not Provisioning

**Check certificate:**
```bash
kubectl -n athena-admin describe certificate athena-admin-tls
```

**Common issues:**
- DNS not pointing to correct IP (should be 192.168.60.50)
- cert-manager not installed (check: `kubectl get pods -n cert-manager`)
- Let's Encrypt rate limit (wait 1 hour and try again)

### Site Not Accessible

**Check ingress:**
```bash
kubectl -n athena-admin get ingress
```

**Verify:**
- DNS resolves to 192.168.60.50
- Traefik is running: `kubectl get pods -A | grep traefik`
- Pods are running: `kubectl -n athena-admin get pods`

### Backend Can't Reach Mac Studio

**Check backend logs:**
```bash
kubectl -n athena-admin logs -f deployment/athena-admin-backend
```

**Verify:**
- Mac Studio is accessible: `curl http://192.168.10.167:8000/health`
- All 14 services are running on Mac Studio

## Quick Status Check Commands

```bash
# Overall status
kubectl -n athena-admin get all

# Pod details
kubectl -n athena-admin get pods -o wide

# Pod logs
kubectl -n athena-admin logs -f deployment/athena-admin-backend
kubectl -n athena-admin logs -f deployment/athena-admin-frontend

# Ingress status
kubectl -n athena-admin get ingress athena-admin-ingress

# Certificate status
kubectl -n athena-admin get certificate athena-admin-tls

# Test backend directly (from within cluster)
kubectl -n athena-admin port-forward svc/athena-admin-backend 8080:8080
# Then: curl http://localhost:8080/api/status

# Test DNS
nslookup athena-admin.xmojo.net

# Test SSL
curl -I https://athena-admin.xmojo.net
```

## Next Steps After Deployment

Once the admin interface is running:

1. ✅ Verify all services show as healthy
2. ✅ Bookmark https://athena-admin.xmojo.net
3. ✅ Monitor Mac Studio services through the dashboard
4. 📋 Configure OpenAI Conversation in Home Assistant (next task)
5. 📋 Create Assist Pipelines in Home Assistant
6. 📋 Test end-to-end voice integration

## Summary

**The admin interface is 95% deployed. To complete:**

1. Load images on nodes manually OR configure containerd for insecure registry
2. Delete pods to recreate them
3. Add Cloudflare DNS record for `athena-admin.xmojo.net` → `192.168.60.50`
4. Wait for cert-manager to provision SSL certificate
5. Access https://athena-admin.xmojo.net

**Estimated time to complete:** 10-15 minutes

---

**Created:** 2025-11-12 02:40 AM
**Status:** Ready for manual completion
**Files:** `/tmp/backend.tar.gz`, `/tmp/frontend.tar.gz`
**Cluster:** thor (192.168.10.222:6443)
**Namespace:** athena-admin
