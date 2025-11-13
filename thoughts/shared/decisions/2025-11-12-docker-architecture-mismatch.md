# Docker Architecture Mismatch - Lessons Learned

**Date:** 2025-11-12
**Context:** Deploying Athena Admin Phase 2 backend to thor cluster
**Issue:** Docker image built on ARM Mac (Apple Silicon) crashed when deployed to AMD64 Kubernetes cluster

## Problem

When building Docker images locally on an Apple Silicon Mac (ARM64 architecture) and deploying to an AMD64/x86_64 Kubernetes cluster, pods crash with:

```
exec /usr/local/bin/python: exec format error
```

This error occurs because the compiled binaries in the Docker image are for the wrong CPU architecture.

## Root Cause

- **Local Mac:** ARM64 (Apple Silicon M1/M2/M3/M4)
- **Thor Cluster Nodes:** AMD64 (x86_64)
- **Docker Default:** Builds for the host architecture unless specified

## Solution

Always explicitly specify the target platform when building Docker images for deployment:

### Method 1: Build for specific platform (recommended)

```bash
# Build for AMD64 and load locally
docker buildx build --platform linux/amd64 -t my-image:tag --load .

# Then tag and push
docker tag my-image:tag registry:port/my-image:tag
docker push registry:port/my-image:tag
```

### Method 2: Build and push directly (if registry supports)

```bash
cd /path/to/backend
docker buildx build --platform linux/amd64 \
    -t 192.168.10.222:30500/my-image:latest \
    --push .
```

**Note:** Direct push with `--push` may fail if trying to push to Docker Hub without credentials. Use Method 1 for local registries.

## Verification Commands

```bash
# Check cluster architecture
kubectl get nodes -o jsonpath='{.items[0].status.nodeInfo.architecture}'
# Output: amd64

# Check local machine architecture
uname -m
# Output (Mac): arm64
```

## Prevention Checklist

When deploying to Kubernetes from a Mac:

1. ✅ Check cluster node architecture first: `kubectl get nodes -o wide`
2. ✅ Always use `--platform linux/amd64` when building for AMD64 clusters
3. ✅ Test pod startup after deployment: `kubectl logs <pod-name>`
4. ✅ Watch for "exec format error" - immediate sign of architecture mismatch

## Related Issues

Other common errors encountered during this deployment:

### Import Error: PBKDF2 vs PBKDF2HMAC

**Error:**
```
ImportError: cannot import name 'PBKDF2' from 'cryptography.hazmat.primitives.kdf.pbkdf2'
```

**Fix:**
```python
# Wrong
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

# Correct
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Then use PBKDF2HMAC instead of PBKDF2
kdf = PBKDF2HMAC(...)
```

## References

- Docker Buildx documentation: https://docs.docker.com/buildx/working-with-buildx/
- Multi-platform images: https://docs.docker.com/build/building/multi-platform/
- Thor cluster configuration: `/Users/jaystuart/dev/kubernetes/k8s-home-lab/CLAUDE.md`

## Impact

This issue cost approximately 30 minutes of debugging and 3 rebuild/redeploy cycles. Now documented for future reference.
