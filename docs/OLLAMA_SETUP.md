# Ollama Setup Guide

## Installation on Jetson

```bash
# SSH to Jetson
ssh jstuart@192.168.10.62

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version

# Pull required models
ollama pull llama3.2:3b      # Complex queries (3.2GB)
ollama pull tinyllama:latest  # Simple queries (637MB)

# Configure Ollama to listen on port 11435 (not default 11434)
sudo systemctl edit ollama

# Add override:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11435"

# Restart Ollama
sudo systemctl restart ollama

# Verify
curl http://localhost:11435/api/tags
```

## Model Selection Strategy

**TinyLlama (637MB, ~1-2s response)**:
- Device control commands
- Simple factual queries
- Weather, time, quick lookups
- What/when/where questions

**Llama3.2:3b (3.2GB, ~3-5s response)**:
- Complex reasoning
- Multi-step instructions
- Explanations and help
- Context-dependent queries

## Testing

```bash
# Test TinyLlama
curl http://localhost:11435/api/generate -d '{
  "model": "tinyllama",
  "prompt": "What time is it?",
  "stream": false
}'

# Test Llama3.2
curl http://localhost:11435/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Explain how to optimize my office lighting for productivity",
  "stream": false
}'
```
