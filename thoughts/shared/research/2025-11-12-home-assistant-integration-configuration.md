# Home Assistant Integration Configuration - Lessons Learned

**Date:** 2025-11-12
**Topic:** Home Assistant integration configuration methods
**Status:** Lesson Learned
**Severity:** High (caused HA core failure)

## Summary

Modern Home Assistant integrations **must be configured via the UI**, not via YAML configuration files. Attempting to configure integrations like `openai_conversation` directly in `configuration.yaml` can cause Home Assistant Core to fail startup or run with severe performance degradation.

## What Happened

During Project Athena implementation, we attempted to configure the OpenAI Conversation integration by adding YAML configuration to `/config/configuration.yaml`:

```yaml
# OpenAI Conversation Integration for Project Athena
# Points to Mac Studio LiteLLM Gateway
openai_conversation:
  - name: "Athena (Mac Studio)"
    api_key: "sk-athena-9fd1ef6c8ed1eb0278f5133095c60271"
    base_url: "http://192.168.10.167:8001/v1"
    model: "athena-medium"  # Uses llama3.1:8b for complex queries
    max_tokens: 500
    temperature: 0.7
```

**Result:**
- Home Assistant Core either failed to start or ran extremely slowly
- Web UI became unresponsive
- SSH connections became intermittent
- API responses were delayed or timed out

## Root Cause

The OpenAI Conversation integration in modern Home Assistant versions (2025.10.3+) does not support YAML configuration. The integration loads, but the YAML config causes:

1. **Configuration validation issues** - HA tries to process unsupported YAML schema
2. **Startup delays** - Integration initialization hangs or times out
3. **Runtime instability** - Ongoing attempts to reconcile YAML vs UI config

## The Fix

1. **Remove YAML configuration** from `configuration.yaml`:
   ```bash
   # Backup current config
   cp /config/configuration.yaml /config/configuration.yaml.backup

   # Remove the openai_conversation section (last 8 lines in this case)
   head -n -8 /config/configuration.yaml.backup > /config/configuration.yaml
   ```

2. **Restart Home Assistant Core:**
   ```bash
   ha core restart
   ```

3. **Configure via UI instead:**
   - Navigate to Settings → Devices & Services
   - Click "+ Add Integration"
   - Search for "OpenAI Conversation"
   - Enter configuration via the UI form:
     - API Key: [your key]
     - Base URL: http://192.168.10.167:8001/v1
     - Model: athena-medium

## Why YAML Configuration Doesn't Work

### Historical Context

In older Home Assistant versions, most integrations supported YAML configuration. This approach:
- Allowed version control of configuration
- Enabled programmatic setup
- Was familiar to users from other home automation platforms

### Modern Approach (2023+)

Home Assistant shifted to **UI-first configuration** for several reasons:

1. **Better UX** - Form validation, autocomplete, immediate feedback
2. **Dynamic schemas** - Integrations can change config options without breaking YAML
3. **OAuth/Auth flows** - Many integrations require interactive auth (impossible in YAML)
4. **Discoverability** - New users can find and configure integrations without reading docs
5. **Safety** - Prevents invalid configurations from breaking HA startup

### Which Integrations Still Support YAML?

**YAML-supported (legacy integrations):**
- `homeassistant:` - Core configuration
- `automation:` - Automations
- `script:` - Scripts
- `sensor:` - Template sensors
- `binary_sensor:` - Template binary sensors
- Some older integrations explicitly documented as YAML-compatible

**UI-only (modern integrations):**
- `openai_conversation` - AI conversation agents
- `wyoming` - Voice assistant protocols
- Most OAuth-based integrations
- Cloud integrations (Alexa, Google Home, etc.)
- Modern device integrations (Zigbee, Z-Wave, Matter, etc.)

## How to Identify Configuration Method

### Check Integration Documentation

1. Visit Home Assistant documentation: https://www.home-assistant.io/integrations/
2. Search for the integration (e.g., "OpenAI Conversation")
3. Look for configuration section:
   - **"Configuration via UI"** = UI-only
   - **"YAML Configuration"** = YAML supported
   - If unsure, try UI first

### Safe Approach

**Always try UI configuration first:**
1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for the integration
4. If it appears in the UI, configure it there
5. Only use YAML if:
   - Integration documentation explicitly shows YAML examples
   - Integration is not available in UI
   - You're creating template sensors/automations

## Best Practices Going Forward

### DO ✅

- **Use the UI** for all modern integrations
- **Check documentation** before adding YAML config
- **Test in development** before applying to production HA
- **Back up configuration** before making changes
- **Use configuration.yaml for:**
  - Core HA settings (`homeassistant:`)
  - Automations (though UI is recommended)
  - Scripts
  - Template sensors/helpers

### DON'T ❌

- **Don't assume** integrations support YAML
- **Don't add** UI integrations to `configuration.yaml`
- **Don't guess** at YAML schema - check docs first
- **Don't mix** UI and YAML config for the same integration
- **Don't skip** testing configuration changes

## Recovery Procedure

If you accidentally add UI-only integration to YAML:

1. **Access HA via SSH:**
   ```bash
   ssh -i ~/.ssh/ha_key -p 23 root@192.168.10.168
   ```

2. **Back up current config:**
   ```bash
   cp /config/configuration.yaml /config/configuration.yaml.backup-$(date +%Y%m%d)
   ```

3. **Edit configuration.yaml:**
   ```bash
   nano /config/configuration.yaml
   # OR
   vi /config/configuration.yaml
   ```

4. **Remove the problematic section:**
   - Delete the integration YAML block
   - Save the file

5. **Restart HA Core:**
   ```bash
   ha core restart
   ```

6. **Wait 2-3 minutes** for HA to fully restart

7. **Verify HA is running:**
   ```bash
   curl -sk https://192.168.10.168:8123/api/
   # Should return: {"message":"API running."}
   ```

8. **Configure integration via UI** (see above)

## Related Documentation

- Home Assistant Configuration Methods: https://www.home-assistant.io/docs/configuration/
- OpenAI Conversation Integration: https://www.home-assistant.io/integrations/openai_conversation/
- Migrating from YAML to UI: https://www.home-assistant.io/blog/2023/04/18/release-20234/#migrating-integrations-to-the-ui

## Impact on Project Athena

This incident delayed Project Athena voice integration setup by approximately 1 hour. The fix was straightforward once identified.

**Current status:**
- ✅ Home Assistant running normally
- ✅ Configuration cleaned up
- ✅ Ready for UI-based OpenAI Conversation setup
- ✅ Wyoming add-ons (Piper, Whisper) updated and functional

**Remaining work:**
- Configure OpenAI Conversation via HA UI
- Create Assist Pipelines for voice
- Test end-to-end voice queries

## Prevention

**For Future Integrations:**

1. **Read the documentation** first - don't assume YAML support
2. **Use the UI** as default configuration method
3. **Test on dev instance** before production
4. **Document** which integrations are UI-only in project docs

**For Team Members:**

- Share this lesson with anyone working on HA integrations
- Update deployment procedures to mention UI-first approach
- Add warning in documentation about YAML vs UI configuration

## References

- **Issue occurred:** 2025-11-12 00:56 UTC
- **Resolution time:** ~15 minutes
- **Home Assistant version:** 2025.10.3
- **Integration:** openai_conversation
- **Configuration file:** /config/configuration.yaml
- **Backup location:** /config/configuration.yaml.backup-openai

## Tags

`home-assistant` `configuration` `lessons-learned` `openai-conversation` `yaml` `ui-configuration` `troubleshooting` `project-athena`
