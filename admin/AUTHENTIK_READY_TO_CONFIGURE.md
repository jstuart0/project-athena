# Authentik Configuration - Ready to Complete

**Status:** ✅ Credentials generated and applied to Kubernetes
**Date:** November 12, 2025

## What's Been Done

1. ✅ Generated secure OAuth2 credentials
2. ✅ Applied credentials to Kubernetes secret `athena-admin-oidc`
3. ✅ Restarted backend pods with new configuration
4. ✅ Created recovery link for Authentik admin access

## Next Step: Configure Authentik Provider

You need to create the OAuth2/OIDC provider in Authentik using the recovery link below.

### Step 1: Access Authentik via Recovery Link

**Recovery Link (valid for 10 years):**
```
https://auth.xmojo.net/recovery/use-token/BoJ1GlJeoBF9kl7kv7fICGZcBk9BfC2gc8k7dHCAytW2miRtJ9Xr9PvJvAbR
```

This recovery link will:
- Log you in as `akadmin` user
- Give you full admin access to Authentik
- Allow you to configure providers and applications

### Step 2: Create OAuth2/OIDC Provider

Once logged in to Authentik:

1. **Navigate to Applications → Providers**
2. **Click "Create" → Select "OAuth2/OpenID Provider"**

3. **Configure Provider with these EXACT values:**

```
Name: athena-admin
Authorization flow: default-provider-authorization-implicit-consent
Client type: Confidential

Client ID: athena-admin--azFHGbekXU
Client Secret: erGLl9UKytAQUuoA40VoC4eCZ9NN0p8KdpBvc3-xBPE

Redirect URIs: https://athena-admin.xmojo.net/auth/callback
Signing Key: authentik Self-signed Certificate
```

4. **Advanced Settings:**

```
Scopes: openid, profile, email
Subject mode: Based on the User's UUID
Include claims in id_token: ✓ Yes

Token validity:
  - Access token: 600 (10 minutes)
  - Refresh token: 86400 (1 day)
```

5. **Click "Create"**

### Step 3: Create Application

1. **Navigate to Applications → Applications**
2. **Click "Create"**

3. **Configure Application:**

```
Name: Athena Admin
Slug: athena-admin
Provider: athena-admin (select the provider created above)
Launch URL: https://athena-admin.xmojo.net
Icon: (optional)
```

4. **Click "Create"**

### Step 4: Test Authentication

Once the provider and application are created:

```bash
# Test the login flow
open https://athena-admin.xmojo.net/auth/login
```

You should be redirected to Authentik, log in, and then redirected back to the admin interface with a JWT token.

## Verification Commands

```bash
# Check secret is applied
kubectl -n athena-admin get secret athena-admin-oidc -o jsonpath='{.data.OIDC_CLIENT_ID}' | base64 -d

# Check backend pods are running
kubectl -n athena-admin get pods -l app=athena-admin-backend

# Test backend API
curl -s https://athena-admin.xmojo.net/api/status | jq '{overall_health, healthy_services}'
```

## Troubleshooting

### Issue: Recovery link doesn't work

Try generating a new recovery link:

```bash
kubectl config use-context thor
kubectl -n authentik exec deployment/authentik-server -- ak create_recovery_key 10 akadmin
```

### Issue: Authentication fails after setup

1. Verify the provider configuration matches exactly
2. Check that Redirect URI is `https://athena-admin.xmojo.net/auth/callback` (exact match)
3. Verify Client ID and Secret match what's in the Kubernetes secret:

```bash
kubectl -n athena-admin get secret athena-admin-oidc -o jsonpath='{.data.OIDC_CLIENT_ID}' | base64 -d
kubectl -n athena-admin get secret athena-admin-oidc -o jsonpath='{.data.OIDC_CLIENT_SECRET}' | base64 -d
```

4. Check backend logs:

```bash
kubectl -n athena-admin logs -f deployment/athena-admin-backend | grep -E "(auth|oidc)"
```

## User Management

After first successful login, your user will be created with the `viewer` role (read-only).

**To upgrade to admin (owner) role:**

```bash
# Connect to database
kubectl -n athena-admin exec -it deployment/postgres -- psql -U psadmin -d athena_admin

# Update role
UPDATE users SET role = 'owner' WHERE username = 'your_username';

# Verify
SELECT id, username, email, role, active FROM users;

# Exit
\q
```

## Architecture

```
User Browser
    ↓
1. GET /auth/login
    ↓
Backend redirects to Authentik
    ↓
2. User enters credentials at auth.xmojo.net
    ↓
3. Authentik redirects to /auth/callback with authorization code
    ↓
4. Backend exchanges code for tokens with Authentik
    ↓
5. Backend fetches userinfo from Authentik
    ↓
6. Backend creates/updates user in PostgreSQL
    ↓
7. Backend generates internal JWT token
    ↓
8. Backend redirects to frontend with JWT token
    ↓
User is authenticated!
```

## Credentials Summary

**Kubernetes Secret:** `athena-admin-oidc` in namespace `athena-admin`

**Client ID:** `athena-admin--azFHGbekXU`
**Client Secret:** `erGLl9UKytAQUuoA40VoC4eCZ9NN0p8KdpBvc3-xBPE`

**Recovery Token (akadmin):**
```
BoJ1GlJeoBF9kl7kv7fICGZcBk9BfC2gc8k7dHCAytW2miRtJ9Xr9PvJvAbR
```

**Recovery Link:**
```
https://auth.xmojo.net/recovery/use-token/BoJ1GlJeoBF9kl7kv7fICGZcBk9BfC2gc8k7dHCAytW2miRtJ9Xr9PvJvAbR
```

## Status Checklist

- [x] OAuth2 credentials generated
- [x] Kubernetes secret updated
- [x] Backend pods restarted
- [x] Recovery link generated
- [ ] Authentik provider created (manual step - **DO THIS NOW**)
- [ ] Authentik application created (manual step - **DO THIS NOW**)
- [ ] Authentication tested

## Quick Start (TL;DR)

1. Open: https://auth.xmojo.net/recovery/use-token/BoJ1GlJeoBF9kl7kv7fICGZcBk9BfC2gc8k7dHCAytW2miRtJ9Xr9PvJvAbR
2. Create Provider with Client ID: `athena-admin--azFHGbekXU` and Client Secret: `erGLl9UKytAQUuoA40VoC4eCZ9NN0p8KdpBvc3-xBPE`
3. Create Application pointing to that provider
4. Test: https://athena-admin.xmojo.net/auth/login

---

**Everything is ready!** Just need to create the provider and application in Authentik (5 minutes).
