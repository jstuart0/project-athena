# Cloudflare DNS Setup for Athena Admin Interface

The admin interface is deployed and ready, but requires DNS configuration to be accessible.

## Manual DNS Configuration Required

The API tokens stored in Kubernetes are scoped only for DNS challenges (cert-manager) and don't have permissions to create DNS records. You'll need to add the record manually via the Cloudflare dashboard.

## Steps to Add DNS Record

### 1. Log into Cloudflare Dashboard

Go to: https://dash.cloudflare.com/

### 2. Select the xmojo.net zone

Click on **xmojo.net** from your list of domains

### 3. Add DNS Record

Navigate to: **DNS** → **Records**

Click: **Add record**

### 4. Configure the Record

Enter the following details:

| Field | Value |
|-------|-------|
| **Type** | A |
| **Name** | `athena-admin` |
| **IPv4 address** | `192.168.60.50` |
| **Proxy status** | DNS only (gray cloud ☁️) |
| **TTL** | Auto |

**IMPORTANT:** Make sure "Proxy status" is **DNS only** (gray cloud), NOT proxied (orange cloud). The orange cloud would route traffic through Cloudflare's proxy, which won't work for internal services.

### 5. Save the Record

Click **Save**

## Verification

After adding the record, verify DNS propagation:

```bash
# Check DNS resolution
nslookup athena-admin.xmojo.net

# Should return:
# Name:    athena-admin.xmojo.net
# Address: 192.168.60.50
```

**Note:** DNS propagation typically takes 1-5 minutes, but can take up to 15 minutes in some cases.

## Access the Admin Interface

Once DNS is propagated and the certificate is ready, access the interface at:

**https://athena-admin.xmojo.net**

### What You'll See

The admin interface provides:
- Real-time status of all 14 Mac Studio services
- Health indicators (green = healthy, red = unhealthy)
- Auto-refresh every 30 seconds
- Dark theme UI
- Response time monitoring

### Monitored Services

1. Gateway - Port 8000
2. Orchestrator - Port 8001
3. RAG Query - Port 8010
4. RAG Retrieval - Port 8011
5. RAG Indexing - Port 8012
6. Ollama - Port 11434
7. LiteLLM Gateway - Port 4000
8. Qdrant (Mac mini) - Port 6333
9. Redis (Mac mini) - Port 6379
10. Intent Classifier - Port 8020
11. Context Manager - Port 8021
12. Tool Executor - Port 8022
13. Response Formatter - Port 8023
14. Conversation Manager - Port 8024

## Troubleshooting

### DNS Not Resolving

If `nslookup athena-admin.xmojo.net` doesn't return `192.168.60.50`:

1. Wait 5 minutes for DNS propagation
2. Verify the record was saved correctly in Cloudflare dashboard
3. Check that you used the correct IP: `192.168.60.50`
4. Ensure "Proxy status" is set to "DNS only" (gray cloud)

### Certificate Not Ready

If you see certificate errors when accessing the site:

```bash
# Check certificate status
kubectl -n athena-admin get certificate athena-admin-tls

# Should show: READY=True
```

If certificate is not ready:

```bash
# Check certificate details
kubectl -n athena-admin describe certificate athena-admin-tls

# Common issues:
# - DNS not propagated yet
# - Let's Encrypt rate limit (wait 1 hour)
# - cert-manager not running
```

### Site Not Loading

If the site doesn't load after DNS and certificate are ready:

```bash
# Check pods are running
kubectl -n athena-admin get pods

# Should show 4/4 pods Running

# Check ingress
kubectl -n athena-admin get ingress

# Should show ADDRESS: 192.168.60.50
```

### Backend Can't Reach Mac Studio

If the dashboard loads but shows all services as unhealthy:

1. Verify Mac Studio is accessible:
   ```bash
   curl http://192.168.10.167:8000/health
   ```

2. Check backend logs:
   ```bash
   kubectl -n athena-admin logs -f deployment/athena-admin-backend
   ```

3. Ensure all Mac Studio services are running:
   ```bash
   ssh jstuart@192.168.10.167
   docker ps
   ```

## Summary

**What's Ready:**
- ✅ Admin interface deployed to thor cluster
- ✅ All pods running (4/4)
- ✅ TLS certificate provisioned
- ✅ Ingress configured
- ✅ Backend monitoring Mac Studio services

**What's Needed:**
- 📋 Add DNS A record in Cloudflare (manual step)
- 📋 Wait for DNS propagation (1-5 minutes)
- 📋 Access https://athena-admin.xmojo.net

**Once DNS is configured, the admin interface will be fully operational!**

---

**Created:** November 12, 2025
**Deployment:** thor Kubernetes cluster
**Namespace:** athena-admin
