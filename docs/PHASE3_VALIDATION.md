# Phase 3 Success Criteria Validation

## Automated Verification Checklist

### ✅ Completed (Local Testing)

- [x] Proxy service starts without errors (syntax validated)
- [x] All imports work correctly
- [x] Configuration system loads both modes
- [x] Cache system functions properly
- [x] Validation system detects hallucinations
- [x] Baltimore mode shows location context
- [x] General mode shows no location context

### ⏳ Requires Jetson Deployment

The following checks require the service to be deployed on the Jetson (192.168.10.62) with Ollama running:

- [ ] Health check passes: `curl http://localhost:11434/health`
- [ ] Ollama proxy responds: `curl -X POST http://localhost:11434/api/generate -d '{"prompt":"test"}'`
- [ ] Cache statistics show in health check
- [ ] Baltimore mode provides location-aware responses (when switched to Baltimore)
- [ ] General mode doesn't mention Baltimore (default mode)

## Manual Verification Checklist

These checks should be performed after deployment to Jetson:

- [ ] Simple query uses TinyLlama (check logs for model selection)
- [ ] Complex query uses Llama3.2:3b
- [ ] Repeated query returns cached response (check "cached": true)
- [ ] Baltimore mode provides location-aware responses
- [ ] General mode doesn't mention Baltimore
- [ ] Validation catches hallucinations (test: "Are we in Portland?")

## Deployment Commands

To deploy and test on Jetson:

```bash
# 1. Copy files to Jetson
scp -r src/jetson/* jstuart@192.168.10.62:/mnt/nvme/athena-lite/

# 2. SSH to Jetson
ssh jstuart@192.168.10.62

# 3. Create .env file from template
cd /mnt/nvme/athena-lite
cp .env.example .env

# 4. Ensure Ollama is running on port 11435
curl http://localhost:11435/api/tags

# 5. Test proxy locally (not as service)
python3 ollama_proxy.py

# 6. In another terminal, test health endpoint
curl http://localhost:11434/health

# 7. Test simple query
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What time is it?", "stream": false}'

# 8. Test complex query
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain how smart home automation works", "stream": false}'
```

## Expected Results

### Health Check Response
```json
{
  "status": "healthy",
  "mode": "general",
  "ollama_connected": true,
  "ollama_url": "http://localhost:11435",
  "cache_stats": {
    "hit_rate": "0.0%",
    "total_queries": 0,
    ...
  },
  "features": {
    "anti_hallucination": true,
    "sms": false,
    "location_context": false,
    "sports_scores": true
  }
}
```

### Generate Response (Simple Query)
```json
{
  "model": "tinyllama:latest",
  "created_at": "2025-01-06T...",
  "response": "It's currently [time]...",
  "done": true,
  "cached": false
}
```

### Generate Response (Cached)
```json
{
  "model": "cached",
  "created_at": "2025-01-06T...",
  "response": "It's currently [time]...",
  "done": true,
  "cached": true
}
```

## Troubleshooting

### "Connection refused" on port 11434
- Check if proxy is running: `ps aux | grep ollama_proxy`
- Check logs: `tail -50 /mnt/nvme/athena-lite/logs/proxy.log`

### "Connection refused" on port 11435
- Check if Ollama is running: `systemctl status ollama`
- Verify Ollama port: `curl http://localhost:11435/api/tags`
- Check Ollama service override is applied

### Import errors
- Install dependencies: `pip3 install -r requirements.txt --user`
- Check Python path includes current directory

### No response from Ollama
- Check Ollama models are downloaded: `ollama list`
- Pull models: `ollama pull tinyllama:latest && ollama pull llama3.2:3b`

## Next Steps

After Phase 3 validation passes, proceed to:
- **Phase 4**: Service Management & Deployment (systemd, deployment scripts)
- **Phase 5**: Monitoring, Observability & Testing (metrics, integration tests)
- **Phase 6**: Documentation & Final Validation
