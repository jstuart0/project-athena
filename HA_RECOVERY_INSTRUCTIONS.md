# Home Assistant Recovery Instructions

## What Happened

Home Assistant crashed and is not starting due to invalid configuration that was added to `/config/configuration.yaml`.

## Current Status

- ✅ **Server is online:** 192.168.10.168 is pingable
- ❌ **HA Core is down:** HTTP API on port 8123 not responding
- ❌ **SSH is down:** Port 23 refusing connections
- ❌ **Cannot access remotely:** All remote access methods unavailable

## Root Cause

Invalid OpenAI Conversation configuration was added to `/config/configuration.yaml`:

```yaml
# OpenAI Conversation Integration for Project Athena
# Points to Mac Studio LiteLLM Gateway
openai_conversation:
  - name: "Athena (Mac Studio)"
    api_key: "sk-athena-9fd1ef6c8ed1eb0278f5133095c60271"
    base_url: "http://192.168.10.167:8001/v1"
    model: "athena-medium"
    max_tokens: 500
    temperature: 0.7
```

**The problem:** OpenAI Conversation integration in Home Assistant is configured via the UI, NOT via YAML configuration. Adding this to configuration.yaml caused HA Core to fail validation and refuse to start.

## How to Fix (Requires Physical Access)

You need **physical access** to the Home Assistant server (ODROID-N2 at 192.168.10.168) to fix this.

### Option 1: Direct Console Access (Fastest)

1. **Connect monitor and keyboard** to the HA server at 192.168.10.168
2. **Log in** at the console (username: root, no password typically)
3. **Edit the configuration file:**
   ```bash
   vi /config/configuration.yaml
   # Or use nano if available:
   nano /config/configuration.yaml
   ```
4. **Remove the bad configuration:**
   - Scroll to the end of the file
   - Delete these lines:
     ```yaml
     # OpenAI Conversation Integration for Project Athena
     # Points to Mac Studio LiteLLM Gateway
     openai_conversation:
       - name: "Athena (Mac Studio)"
         api_key: "sk-athena-9fd1ef6c8ed1eb0278f5133095c60271"
         base_url: "http://192.168.10.167:8001/v1"
         model: "athena-medium"
         max_tokens: 500
         temperature: 0.7
     ```
5. **Save the file** (in vi: press ESC, type `:wq`, press ENTER)
6. **Reboot the system:**
   ```bash
   reboot
   ```
7. **Wait 2-3 minutes** for HA to fully restart
8. **Test access:**
   ```bash
   curl -sk https://192.168.10.168:8123/api/
   # Should return: {"message":"API running."}
   ```

### Option 2: Use Recovery Mode

If the HA system has a recovery mode:

1. **Power cycle** the server
2. **Boot into recovery mode** (check ODROID documentation)
3. **Mount the config partition**
4. **Edit /config/configuration.yaml** and remove the bad config
5. **Reboot normally**

### Option 3: SD Card Access (if applicable)

If HA is running from an SD card or removable storage:

1. **Power off** the server
2. **Remove the storage** (SD card or USB drive)
3. **Mount it on another computer**
4. **Edit config/configuration.yaml** and remove the bad config
5. **Safely eject** and reinstall the storage
6. **Power on** the server

## After Recovery

Once HA is back up and accessible:

### Configure OpenAI Conversation (THE RIGHT WAY - Via UI)

1. **Open Home Assistant** at https://ha.xmojo.net
2. **Go to Settings > Devices & Services**
3. **Click "+ Add Integration"**
4. **Search for "OpenAI Conversation"**
5. **Configure it:**
   - API Key: `sk-athena-9fd1ef6c8ed1eb0278f5133095c60271`
   - Base URL: `http://192.168.10.167:8001/v1`
   - Model: `athena-medium`

### Create Assist Pipelines

Follow the complete instructions in **HA_CONFIGURATION_GUIDE.md** to:
1. Create voice pipelines
2. Configure STT/TTS services
3. Test voice integration

## What's Still Good

The following are working and ready:

- ✅ **Piper TTS:** Updated to v2.1.1 (will work when HA restarts)
- ✅ **Whisper STT:** Updated to v3.0.1 (will work when HA restarts)
- ✅ **Mac Studio Services:** All 14 Athena services running perfectly
- ✅ **Admin Interface:** Code ready for deployment
- ✅ **Documentation:** Complete guides available

## Verification Steps After Fix

```bash
# 1. Check HA is accessible
curl -sk https://192.168.10.168:8123/api/
# Should return: {"message":"API running."}

# 2. Check SSH is back
ssh -i ~/.ssh/ha_ssh_key -p 23 root@192.168.10.168 "echo Success"

# 3. Verify add-ons are running
ssh -i ~/.ssh/ha_ssh_key -p 23 root@192.168.10.168 "ha addons | grep -E 'piper|whisper'"
# Should show both as 'started'

# 4. Test HA web interface
open https://ha.xmojo.net
```

## Prevention

**NEVER add integration configuration directly to configuration.yaml unless you are 100% certain it supports YAML configuration.**

Most modern Home Assistant integrations are configured via the UI:
- Settings > Devices & Services > Add Integration

Only certain legacy or advanced integrations support YAML configuration.

## Contact Information

If you need help with recovery or have questions:
- Reference: **HA_CONFIGURATION_GUIDE.md** for proper configuration steps
- Reference: **FINAL_HANDOFF.md** for system overview
- Reference: **TROUBLESHOOTING.md** for other common issues

## Alternative: Fresh Configuration (Last Resort)

If you can't access the config file and need to get HA running quickly:

1. Backup the current config directory (if possible)
2. Restore from the most recent backup before the change
3. HA should start with the old configuration
4. Re-apply the add-on updates (Piper and Whisper) via UI

---

**Created:** November 12, 2025
**Issue:** Invalid OpenAI Conversation YAML configuration
**Status:** Requires physical access to fix
**Impact:** HA Core down, SSH down, all remote access unavailable
