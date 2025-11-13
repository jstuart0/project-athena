# Set Up Authentik Provider - 5 Minutes

Everything is ready! Just need to create the provider in Authentik.

## Step 1: Access Authentik (30 seconds)

**Open this link:**
```
https://auth.xmojo.net/recovery/use-token/bCg4qY90xoxJ6tzzFONc9pJsEBOqktggia293vVXYgd0M6RN6M1aFTnrOCyF
```

This will log you in as the `akadmin` user with full administrative access.

## Step 2: Create Provider (2 minutes)

1. **Click "Applications" in the left sidebar**
2. **Click "Providers" tab**
3. **Click "Create" button**
4. **Select "OAuth2/OpenID Provider"**

**Fill in these EXACT values:**

```
Name: athena-admin

Authorization flow: default-provider-authorization-implicit-consent

Client type: Confidential

Client ID:
athena-admin--azFHGbekXU

Client Secret:
erGLl9UKytAQUuoA40VoC4eCZ9NN0p8KdpBvc3-xBPE

Redirect URIs:
https://athena-admin.xmojo.net/auth/callback

Signing Key: authentik Self-signed Certificate
```

**Advanced settings:**
- Scopes: `openid profile email` (default is fine)
- Subject mode: Based on the User's UUID
- Include claims in id_token: ✓ (checked)
- Access token validity: 600 (10 minutes)
- Refresh token validity: 86400 (1 day)

5. **Click "Create"**

## Step 3: Create Application (2 minutes)

1. **Stay in Applications section**
2. **Click "Applications" tab**
3. **Click "Create" button**

**Fill in:**

```
Name: Athena Admin

Slug: athena-admin

Provider: athena-admin (select from dropdown)

Launch URL: https://athena-admin.xmojo.net
```

4. **Click "Create"**

## Step 4: Test (1 minute)

**Open:**
```
https://athena-admin.xmojo.net/auth/login
```

You should be redirected to Authentik, log in, and then back to the admin dashboard with a JWT token!

## Done!

After first login, your user will be created with the `viewer` role.

**To upgrade to admin:**
```bash
kubectl -n athena-admin exec -it deployment/postgres -- \
    psql -U psadmin -d athena_admin -c \
    "UPDATE users SET role = 'owner' WHERE username = 'your_username';"
```

---

**All the backend configuration is done.** Just need these 3 clicks in Authentik UI!

### Quick Copy-Paste Values

**Client ID:**
```
athena-admin--azFHGbekXU
```

**Client Secret:**
```
erGLl9UKytAQUuoA40VoC4eCZ9NN0p8KdpBvc3-xBPE
```

**Redirect URI:**
```
https://athena-admin.xmojo.net/auth/callback
```
