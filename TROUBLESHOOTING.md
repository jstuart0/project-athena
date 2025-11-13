# Project Athena - Troubleshooting Guide

**Last Updated:** 2025-11-11

---

## Quick Diagnostics

### Check All Services

```bash
ssh jstuart@192.168.10.167 "cd ~/dev/project-athena && /Applications/Docker.app/Contents/Resources/bin/docker ps"
```

**Expected:** 13 containers running, all showing "healthy" or "Up"

### Test End-to-End

```bash
curl -s http://192.168.10.167:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}]}' | jq
```

**Expected:** JSON response with `choices` array containing message

---

## Common Issues

### Issue: "All Docker containers are down"

**Symptoms:**
- `docker ps` shows no athena containers
- Services not responding on any port

**Diagnosis:**
```bash
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
/Applications/Docker.app/Contents/Resources/bin/docker compose ps
```

**Solution:**
```bash
# Start all services
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d

# If that fails, check Docker Desktop
ps aux | grep Docker
open /Applications/Docker.app
```

**Prevention:** Ensure Docker Desktop starts on boot

---

### Issue: "Orchestrator returns error responses"

**Symptoms:**
- Queries return "I apologize, but I'm having trouble generating a response"
- No actual weather/data in responses

**Diagnosis:**
```bash
# Check orchestrator logs
ssh jstuart@192.168.10.167
/Applications/Docker.app/Contents/Resources/bin/docker logs athena-orchestrator --tail 100
```

**Common Causes:**

1. **LiteLLM Gateway not accessible**
   ```bash
   # Test gateway
   curl -s http://192.168.10.167:8000/health

   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   ```

   **Solution:**
   ```bash
   # Restart Ollama (on Mac Studio)
   ps aux | grep ollama
   # If not running:
   /opt/homebrew/opt/ollama/bin/ollama serve &

   # Restart gateway
   /Applications/Docker.app/Contents/Resources/bin/docker compose restart litellm
   ```

2. **RAG services not accessible**
   ```bash
   # Test weather RAG
   curl http://192.168.10.167:8010/health
   ```

   **Solution:**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose restart weather-rag
   ```

3. **Environment variables not loaded**
   ```bash
   # Check if .env file exists
   cat ~/dev/project-athena/config/env/.env | grep HA_TOKEN
   ```

   **Solution:**
   ```bash
   # Redeploy with env file
   cd ~/dev/project-athena
   /Applications/Docker.app/Contents/Resources/bin/docker compose --env-file config/env/.env up -d
   ```

---

### Issue: "Weather queries return no data"

**Symptoms:**
- Weather queries don't mention temperature
- Generic responses instead of weather data

**Diagnosis:**
```bash
# Test weather RAG directly
curl "http://192.168.10.167:8010/weather/current?location=Baltimore"
```

**Common Causes:**

1. **API key missing or invalid**
   ```bash
   # Check API key configured
   ssh jstuart@192.168.10.167 \
     "cat ~/dev/project-athena/config/env/.env | grep OPENWEATHER_API_KEY"
   ```

   **Solution:**
   ```bash
   # Get key from thor cluster
   kubectl -n automation get secret project-athena-credentials \
     -o jsonpath='{.data.openweathermap-api-key}' | base64 -d

   # Update .env file
   nano ~/dev/project-athena/config/env/.env

   # Restart weather service
   /Applications/Docker.app/Contents/Resources/bin/docker compose restart weather-rag
   ```

2. **Rate limit exceeded**
   - Free tier: 1000 calls/day
   - Check logs for rate limit errors

   **Solution:** Wait for reset or deploy Redis caching

---

### Issue: "High latency (>5 seconds)"

**Symptoms:**
- Queries take too long
- Timeout errors

**Diagnosis:**
```bash
# Measure latency
time curl -s http://192.168.10.167:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}]}'
```

**Common Causes:**

1. **Ollama model not loaded**
   - First query loads model into memory (~5-10s)
   - Subsequent queries are fast (<1s)

   **Solution:** No action needed, this is expected

2. **Large model selected**
   - llama3.1:13b is slower than llama3.1:8b

   **Solution:**
   ```bash
   # Use smaller model for most queries
   # Edit apps/gateway/config.yaml
   # Set default to athena-small (phi3:mini)
   ```

3. **External API slow**
   - Weather API, News API, etc. can be slow

   **Solution:** Deploy Redis caching

4. **Mac Studio resource constrained**
   ```bash
   # Check resources
   ssh jstuart@192.168.10.167 "top -l 1 | head -20"
   ```

---

### Issue: "Container keeps restarting"

**Symptoms:**
- `docker ps` shows container with "Restarting"
- Service unavailable

**Diagnosis:**
```bash
# Check logs
/Applications/Docker.app/Contents/Resources/bin/docker logs <container-name>

# Check exit code
/Applications/Docker.app/Contents/Resources/bin/docker inspect <container-name> | grep ExitCode
```

**Common Causes:**

1. **Port already in use**
   ```bash
   lsof -i :8001  # Check if port is taken
   ```

   **Solution:**
   ```bash
   # Kill process using port
   kill <PID>

   # Or change port in docker-compose.yml
   ```

2. **Missing dependency**
   - Check logs for import errors

   **Solution:**
   ```bash
   # Rebuild image
   /Applications/Docker.app/Contents/Resources/bin/docker compose build <service>
   /Applications/Docker.app/Contents/Resources/bin/docker compose up -d <service>
   ```

3. **Configuration error**
   - Check logs for config errors

   **Solution:**
   ```bash
   # Validate configuration
   /Applications/Docker.app/Contents/Resources/bin/docker compose config

   # Fix errors in docker-compose.yml
   ```

---

### Issue: "LiteLLM Gateway 401 Unauthorized"

**Symptoms:**
- Queries to port 8000 return 401
- "Authentication Error, No api key passed in"

**Diagnosis:**
```bash
curl http://192.168.10.167:8000/health
# Returns: {"error":{"message":"Authentication Error...
```

**Cause:** LiteLLM requires API key for all requests (including health check)

**Solution:** This is expected behavior. Use orchestrator (port 8001) instead:
```bash
curl http://192.168.10.167:8001/health  # No auth required
```

Or provide master key:
```bash
curl http://192.168.10.167:8000/health \
  -H "Authorization: Bearer sk-athena-9fd1ef6c8ed1eb0278f5133095c60271"
```

---

### Issue: "Validators service not responding"

**Symptoms:**
- Port 8030 not responding
- Validator tests fail

**Diagnosis:**
```bash
curl http://192.168.10.167:8030/health
```

**Cause:** Validators runs directly (not in Docker yet)

**Solution:**
```bash
# Check if running
ssh jstuart@192.168.10.167 "ps aux | grep validators"

# If not running, start it
ssh jstuart@192.168.10.167 \
  "cd ~/dev/project-athena/apps/validators && nohup python3 main.py > /tmp/validators.log 2>&1 &"
```

---

### Issue: "Integration tests failing"

**Symptoms:**
- `pytest` command fails
- Test assertions fail

**Diagnosis:**
```bash
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
python3 -m pytest tests/integration/test_full_system.py -v
```

**Common Causes:**

1. **pytest not installed**
   ```bash
   pip3 install pytest requests
   ```

2. **Services not running**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker ps
   # Ensure all 13 containers are up
   ```

3. **Wrong base URL**
   - Tests expect services on 192.168.10.167
   - Check network configuration

---

### Issue: "Mac mini services (Qdrant/Redis) not accessible"

**Symptoms:**
- Cannot connect to 192.168.10.181:6333 or :6379
- Services degrade gracefully but no caching

**Diagnosis:**
```bash
ping 192.168.10.181
ssh jstuart@192.168.10.181
```

**Cause:** SSH not enabled on Mac mini

**Solution:**
1. **Enable SSH on Mac mini:**
   - System Settings → General → Sharing
   - Enable "Remote Login"
   - Add your user

2. **Deploy services:**
   ```bash
   scp deployment/mac-mini/docker-compose.yml jstuart@192.168.10.181:~/
   ssh jstuart@192.168.10.181 "docker compose up -d"
   ```

**Workaround:** Services work without Mac mini (no caching, no vector DB)

---

## Performance Issues

### Slow Responses

**Check:**
1. Ollama model loaded? (first query is slow)
2. External API responding? (test directly)
3. Resources available? (`top` command)
4. Network latency? (`ping 192.168.10.168`)

**Optimize:**
1. Use smaller models (phi3:mini)
2. Deploy Redis caching
3. Increase Mac Studio resources
4. Optimize orchestrator routing

### High Memory Usage

**Check:**
```bash
/Applications/Docker.app/Contents/Resources/bin/docker stats
```

**Solution:**
1. Restart containers: `/Applications/Docker.app/Contents/Resources/bin/docker compose restart`
2. Limit container memory in docker-compose.yml
3. Use smaller Ollama models

---

## Emergency Procedures

### Complete System Restart

```bash
# Stop all services
ssh jstuart@192.168.10.167
cd ~/dev/project-athena
/Applications/Docker.app/Contents/Resources/bin/docker compose down

# Verify Ollama is running
curl http://localhost:11434/api/tags

# Restart all services
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d

# Wait for healthy status (30s)
sleep 30

# Run health checks
for port in 8001 8010 8030; do
  curl http://192.168.10.167:$port/health
done
```

### Nuclear Option: Rebuild Everything

```bash
ssh jstuart@192.168.10.167
cd ~/dev/project-athena

# Stop and remove all containers
/Applications/Docker.app/Contents/Resources/bin/docker compose down -v

# Rebuild all images
/Applications/Docker.app/Contents/Resources/bin/docker compose build --no-cache

# Start everything
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d

# Check logs
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f
```

---

## Getting Help

### Collect Diagnostic Info

```bash
# Create diagnostic bundle
ssh jstuart@192.168.10.167
cd ~/dev/project-athena

cat > /tmp/athena-diagnostics.txt <<EOF
=== Docker Status ===
$(/Applications/Docker.app/Contents/Resources/bin/docker ps)

=== Service Logs (last 50 lines each) ===
$(/Applications/Docker.app/Contents/Resources/bin/docker logs --tail 50 athena-orchestrator)
$(/Applications/Docker.app/Contents/Resources/bin/docker logs --tail 50 athena-weather-rag)

=== Ollama Status ===
$(curl -s http://localhost:11434/api/tags)

=== Mac Studio Resources ===
$(top -l 1 | head -20)

=== Configuration ===
Deployed: $(date)
Version: $(git rev-parse HEAD)
EOF

# Share /tmp/athena-diagnostics.txt
```

### Contact

- Documentation: See docs/ directory
- Implementation tracking: IMPLEMENTATION_TRACKING_LIVE.md
- Test results: Run `pytest -v`

---

**Still stuck? Review logs in detail and check recent git commits for changes.**
