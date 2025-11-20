# SearXNG Deployment Handoff Document

**Date:** 2025-11-19
**Status:** Phase 2 In Progress - Troubleshooting Deployment Issues
**Location:** `/Users/jaystuart/dev/project-athena/admin/k8s/`

## Current Situation

Implementing SearXNG deployment to THOR cluster following plan at:
`thoughts/shared/plans/2025-11-19-searxng-thor-deployment.md`

### Phase 1: COMPLETED ✓

All Kubernetes manifests created and verified:

1. ✅ **searxng-configmap.yaml** - Settings configuration (FIXED: changed boolean `false` to empty strings `""`)
2. ✅ **searxng-secret.yaml** - Secret key placeholder
3. ✅ **searxng-deployment.yaml** - Deployment with security hardening
4. ✅ **searxng-service.yaml** - ClusterIP service
5. ✅ **searxng-middleware.yaml** - Traefik middleware (FIXED: API version from `traefik.containo.us/v1alpha1` to `traefik.io/v1alpha1`)
6. ✅ **deployment.yaml** - Updated with `/searxng` path (middleware annotation removed - not needed)
7. ✅ **deploy-searxng.sh** - Automated deployment script (executable)

### Phase 2: IN PROGRESS 🔄

**Status:** Deployed to THOR but pods are failing

**Resources Created:**
- Namespace: athena-admin (already existed)
- ConfigMap: searxng-config (created, updated once to fix boolean issue)
- Secret: searxng-secret (created by deployment script)
- Middleware: searxng-stripprefix (created)
- Service: searxng (created)
- Deployment: searxng (created, restarted once)
- Ingress: athena-admin-ingress (updated with /searxng path)

**Current Issue:**

Pods are in CrashLoopBackOff. Initial error was:
```
Expected `str`, got `bool` - at `brand.new_issue_url`
ValueError: Invalid settings.yml
```

**Fix Applied:**
Changed ConfigMap settings from boolean `false` to empty strings `""`:
- `brand.new_issue_url: false` → `brand.new_issue_url: ""`
- `brand.docs_url: false` → `brand.docs_url: ""`
- `brand.public_instances: false` → `brand.public_instances: ""`
- `brand.wiki_url: false` → `brand.wiki_url: ""`
- `general.privacypolicy_url: false` → `general.privacypolicy_url: ""`
- `general.donation_url: false` → `general.donation_url: ""`
- `general.contact_url: false` → `general.contact_url: ""`

**Actions Taken:**
1. Applied updated ConfigMap: `kubectl apply -f searxng-configmap.yaml`
2. Restarted deployment: `kubectl -n athena-admin rollout restart deployment/searxng`
3. Deployment rollout timed out after 120s

**Last Known State:**
- Deployment was still rolling out: "1 out of 2 new replicas have been updated"
- Need to check current pod status and logs

## Next Steps

### Immediate Actions

1. **Check current pod status:**
   ```bash
   kubectl -n athena-admin get pods -l app=searxng
   ```

2. **Check logs of new pods:**
   ```bash
   # Get pod name from status above
   kubectl -n athena-admin logs <pod-name> --tail=100
   kubectl -n athena-admin logs <pod-name> -c inject-secret  # Check init container
   ```

3. **Check for any additional errors:**
   ```bash
   kubectl -n athena-admin describe pod <pod-name>
   ```

### Potential Issues to Investigate

1. **Init container permissions:**
   - Logs showed warnings about directory ownership (root:searxng vs searxng:searxng)
   - Init container using busybox may need permission adjustments
   - Consider using `chown` in init container or adjusting fsGroup

2. **Read-only filesystem:**
   - Log showed: `mktemp: (null): Read-only file system`
   - Deployment uses `readOnlyRootFilesystem: true` for security
   - May need additional writable volumes

3. **Settings validation:**
   - Fixed boolean→string issue, but may be other validation errors
   - Check SearXNG documentation for required settings format

4. **Redis connection:**
   - Not tested yet - Mac mini Redis at 192.168.10.181:6379/1
   - SearXNG may fail if Redis is unreachable

### Fixes to Try

**Option 1: Fix init container permissions**
```yaml
# In searxng-deployment.yaml, init container command:
chmod 644 /config-target/settings.yml
chown 977:977 /config-target/settings.yml  # Add this line
```

**Option 2: Add writable temp directory**
```yaml
# In searxng-deployment.yaml, add volume:
- name: tmp
  emptyDir: {}

# In volumeMounts:
- name: tmp
  mountPath: /tmp
```

**Option 3: Adjust fsGroup (already set to 977)**
- Verify fsGroup is working correctly

**Option 4: Test Redis connectivity**
```bash
kubectl run redis-test --rm -i --restart=Never --image=redis:alpine -- \
  redis-cli -h 192.168.10.181 -p 6379 -n 1 PING
```

## Key Configuration Details

### Infrastructure Integration

- **Cluster:** THOR (192.168.10.222:6443)
- **Context:** thor
- **Namespace:** athena-admin
- **Mac mini Redis:** 192.168.10.181:6379/1 (database 1)
- **Public URL:** https://athena-admin.xmojo.net/searxng/
- **Internal URL:** http://searxng.athena-admin.svc.cluster.local:8080

### Security Settings

- **User:** UID 977, GID 977 (non-root)
- **Read-only root filesystem:** true
- **Capabilities:** All dropped
- **Security context:** seccompProfile RuntimeDefault

### Resources

- **Replicas:** 2
- **CPU Request:** 250m, Limit: 1000m
- **Memory Request:** 256Mi, Limit: 512Mi

## Files Modified

### Created Files
```
/Users/jaystuart/dev/project-athena/admin/k8s/
├── searxng-configmap.yaml     (3,673 bytes) - Settings with Mac mini Redis
├── searxng-secret.yaml        (317 bytes) - Secret key placeholder
├── searxng-deployment.yaml    (5,211 bytes) - Deployment with security
├── searxng-service.yaml       (267 bytes) - ClusterIP service
├── searxng-middleware.yaml    (200 bytes) - Traefik StripPrefix middleware
└── deploy-searxng.sh          (7,208 bytes) - Deployment automation
```

### Modified Files
```
/Users/jaystuart/dev/project-athena/admin/k8s/
└── deployment.yaml - Added /searxng path to ingress (lines 230-236)
```

## Verification Commands

```bash
# Check deployment status
kubectl -n athena-admin get deployment searxng

# Check pods
kubectl -n athena-admin get pods -l app=searxng

# Check service
kubectl -n athena-admin get svc searxng

# Check ingress
kubectl -n athena-admin get ingress athena-admin-ingress -o yaml | grep -A 5 "searxng"

# Check middleware
kubectl -n athena-admin get middleware searxng-stripprefix

# View ConfigMap
kubectl -n athena-admin get configmap searxng-config -o yaml

# Test health endpoint (from within cluster)
kubectl run test-health --rm -i --restart=Never --image=curlimages/curl:latest -- \
  curl -v http://searxng.athena-admin.svc.cluster.local:8080/healthz
```

## Rollback Instructions

If deployment continues to fail and needs rollback:

```bash
# Delete all SearXNG resources
kubectl -n athena-admin delete deployment searxng
kubectl -n athena-admin delete service searxng
kubectl -n athena-admin delete configmap searxng-config
kubectl -n athena-admin delete secret searxng-secret
kubectl -n athena-admin delete middleware searxng-stripprefix

# Revert ingress changes (remove /searxng path)
# Edit deployment.yaml and remove lines 230-236
kubectl apply -f deployment.yaml
```

## Reference Documentation

- **Implementation Plan:** `thoughts/shared/plans/2025-11-19-searxng-thor-deployment.md`
- **SearXNG Docs:** https://docs.searxng.org/
- **Traefik CRD Docs:** https://doc.traefik.io/traefik/routing/providers/kubernetes-crd/

## Todo List Status

```
✅ Phase 1: Create SearXNG ConfigMap (searxng-configmap.yaml)
✅ Phase 1: Create SearXNG Secret (searxng-secret.yaml)
✅ Phase 1: Create SearXNG Deployment (searxng-deployment.yaml)
✅ Phase 1: Create SearXNG Service (searxng-service.yaml)
✅ Phase 1: Update Admin Ingress in deployment.yaml
✅ Phase 1: Create Middleware for path stripping
✅ Phase 1: Create deployment script (deploy-searxng.sh)
✅ Phase 1: Run automated verification checks
🔄 Phase 2: Deploy to THOR cluster (IN PROGRESS - troubleshooting pod failures)
⏸️ Phase 2: Verify Mac mini Redis connection
⏸️ Phase 2: Test search functionality
⏸️ Phase 2: Run automated verification checks
⏸️ Phase 3: Update Admin UI frontend
⏸️ Phase 3: Update Admin UI backend
⏸️ Phase 3: Rebuild and deploy frontend/backend
```

## Important Notes

1. **kubectl Access:** kubectl commands work successfully now (macOS Sequoia Local Network permission issue was mentioned earlier but seems resolved)

2. **Middleware Not Currently Used:** The middleware is created but not referenced in ingress annotations. SearXNG's `base_url` setting should handle the /searxng prefix correctly.

3. **Platform:** THOR cluster is linux/amd64 architecture (x86_64)

4. **Previous Error Fixed:** Changed boolean values to empty strings in ConfigMap, but deployment still failing - need to investigate new error

5. **Deployment Script:** Can be used for clean deployment: `./admin/k8s/deploy-searxng.sh`

---

**Handoff Contact:** Continue troubleshooting by checking pod logs and investigating permission/filesystem issues mentioned above.
