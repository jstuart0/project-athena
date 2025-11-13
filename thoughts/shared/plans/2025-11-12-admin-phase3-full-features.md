---
date: 2025-11-12
author: Claude Code (Sonnet 4.5)
commit: 822d785
branch: main
tags: [admin-interface, phase-3, implementation-plan]
status: in-progress
---

# Implementation Plan: Admin Phase 3 - Full Feature Set

## Context

Based on research documented in `2025-11-12-admin-configuration-features.md`, the admin interface is missing several key features:
1. Server Configuration UI
2. RAG Connector Management UI
3. Voice Testing UI

**Important Note:** The original Jetson-based architecture has been deprecated. The current Phase 1 architecture uses:
- **Mac Studio** (192.168.10.167): Gateway, Orchestrator, LLMs (Ollama), RAG services, Wyoming STT/TTS
- **Mac mini** (192.168.10.181): Qdrant vector DB, Redis cache
- **Home Assistant** (192.168.10.168): Voice integration hub, device control

This plan adapts the voice testing concepts from the deprecated Jetson implementation to work with the current Mac-based architecture.

## Architecture Adaptation

### Deprecated (Jetson-based):
```
Wyoming Devices → Jetson (Wake Word) → Mac Studio (STT/LLM/TTS) → HA
```

### Current (Mac-based):
```
Wyoming STT/TTS on Mac Studio → Ollama LLM → HA Integration
RAG Services → Qdrant/Redis on Mac mini
```

## Implementation Plan

### Phase 3.1: Server Configuration UI (4-6 hours)

**Backend Changes:**

1. **Create Server Configuration Model** (`admin/backend/app/models.py`)
```python
class ServerConfig(Base):
    __tablename__ = 'server_configs'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)  # "mac-studio", "mac-mini", "home-assistant"
    hostname = Column(String(128))
    ip_address = Column(String(15), nullable=False)
    role = Column(String(32))  # "compute", "storage", "integration"
    status = Column(String(16), default='unknown')  # online, offline, degraded, unknown
    config = Column(JSONB)  # Flexible JSON config
    last_checked = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

2. **Create Service Registry Model** (`admin/backend/app/models.py`)
```python
class ServiceRegistry(Base):
    __tablename__ = 'service_registry'
    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey('server_configs.id'), nullable=False)
    service_name = Column(String(64), nullable=False)  # "gateway", "ollama", "qdrant"
    port = Column(Integer, nullable=False)
    health_endpoint = Column(String(256))  # "/health", "/api/health"
    protocol = Column(String(8), default='http')  # http, https, tcp
    status = Column(String(16), default='unknown')
    last_response_time = Column(Float)  # milliseconds
    last_checked = Column(DateTime(timezone=True))
```

3. **Create Server Configuration Routes** (`admin/backend/app/routes/servers.py`)
```python
@router.get("", response_model=List[ServerResponse])
async def list_servers()

@router.post("", response_model=ServerResponse, status_code=201)
async def create_server(server_data: ServerCreate)

@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(server_id: int, server_data: ServerUpdate)

@router.get("/{server_id}/services")
async def get_server_services(server_id: int)

@router.post("/{server_id}/check")
async def check_server_health(server_id: int)
```

4. **Create Service Registry Routes** (`admin/backend/app/routes/services.py`)
```python
@router.get("", response_model=List[ServiceResponse])
async def list_services()

@router.post("", response_model=ServiceResponse, status_code=201)
async def register_service(service_data: ServiceCreate)

@router.post("/{service_id}/check")
async def check_service_health(service_id: int)

@router.get("/status/all")
async def get_all_service_status()  # Replaces /api/status endpoint
```

5. **Initialize Default Configuration** (`/tmp/admin-setup.py`)
```python
def create_default_servers(admin_user):
    servers = [
        {
            "name": "mac-studio",
            "hostname": "Jays-Mac-Studio.local",
            "ip_address": "192.168.10.167",
            "role": "compute",
            "config": {"ssh_user": "jstuart", "docker_enabled": True}
        },
        {
            "name": "mac-mini",
            "hostname": "mac-mini.local",
            "ip_address": "192.168.10.181",
            "role": "storage",
            "config": {"docker_enabled": True}
        },
        {
            "name": "home-assistant",
            "hostname": "ha.xmojo.net",
            "ip_address": "192.168.10.168",
            "role": "integration",
            "config": {"api_port": 8123, "ssh_port": 23}
        }
    ]

    services = [
        {"server": "mac-studio", "service_name": "gateway", "port": 8000, "health_endpoint": "/health"},
        {"server": "mac-studio", "service_name": "orchestrator", "port": 8001, "health_endpoint": "/health"},
        {"server": "mac-studio", "service_name": "ollama", "port": 11434, "health_endpoint": "/api/tags"},
        {"server": "mac-studio", "service_name": "weather-rag", "port": 8010, "health_endpoint": "/health"},
        {"server": "mac-studio", "service_name": "airports-rag", "port": 8011, "health_endpoint": "/health"},
        {"server": "mac-studio", "service_name": "sports-rag", "port": 8012, "health_endpoint": "/health"},
        {"server": "mac-studio", "service_name": "whisper-stt", "port": 10300, "health_endpoint": "/"},  # Wyoming
        {"server": "mac-studio", "service_name": "piper-tts", "port": 10200, "health_endpoint": "/"},   # Wyoming
        {"server": "mac-mini", "service_name": "qdrant", "port": 6333, "health_endpoint": "/"},
        {"server": "mac-mini", "service_name": "redis", "port": 6379, "health_endpoint": None},  # TCP check
        {"server": "home-assistant", "service_name": "ha-api", "port": 8123, "health_endpoint": "/api/"},
    ]
```

**Frontend Changes:**

1. **Add "Settings" Tab** (`admin/frontend/app.js`)
```javascript
// Add tab to navigation
<button onclick="showTab('settings')">Settings</button>

// Add tab content
<div id="settings" class="tab-content">
    <div class="section">
        <h2>Server Configuration</h2>
        <button onclick="addServer()">Add Server</button>
        <div id="servers-list"></div>
    </div>

    <div class="section">
        <h2>Service Registry</h2>
        <button onclick="refreshAllServices()">Refresh All</button>
        <div id="services-grid"></div>
    </div>
</div>
```

2. **Server List Component**
```javascript
function loadServers() {
    fetch('/api/servers')
        .then(r => r.json())
        .then(servers => {
            const html = servers.map(server => `
                <div class="server-card ${server.status}">
                    <h3>${server.name}</h3>
                    <p>IP: ${server.ip_address}</p>
                    <p>Role: ${server.role}</p>
                    <p>Status: <span class="status-${server.status}">${server.status}</span></p>
                    <button onclick="checkServer(${server.id})">Check Health</button>
                    <button onclick="editServer(${server.id})">Edit</button>
                </div>
            `).join('');
            document.getElementById('servers-list').innerHTML = html;
        });
}
```

3. **Service Grid Component**
```javascript
function loadServices() {
    fetch('/api/services/status/all')
        .then(r => r.json())
        .then(data => {
            const grid = data.services.map(service => `
                <div class="service-card ${service.status}">
                    <div class="service-name">${service.service_name}</div>
                    <div class="service-server">${service.server_name}</div>
                    <div class="service-port">${service.ip_address}:${service.port}</div>
                    <div class="service-status ${service.status}">
                        ${service.status}
                        ${service.response_time ? `(${service.response_time}ms)` : ''}
                    </div>
                    <button onclick="checkService(${service.id})">Test</button>
                </div>
            `).join('');
            document.getElementById('services-grid').innerHTML = grid;
        });
}
```

### Phase 3.2: RAG Connector Management UI (8-12 hours)

**Backend Changes:**

1. **Create RAG Connector Model** (`admin/backend/app/models.py`)
```python
class RAGConnector(Base):
    __tablename__ = 'rag_connectors'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)  # "weather", "airports", "sports"
    connector_type = Column(String(32))  # "external_api", "vector_db", "cache", "custom"
    service_id = Column(Integer, ForeignKey('service_registry.id'))  # Link to service
    enabled = Column(Boolean, default=True)
    config = Column(JSONB)  # Connector-specific config
    cache_config = Column(JSONB)  # Cache settings (TTL, size limits)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

2. **Create RAG Statistics Model** (`admin/backend/app/models.py`)
```python
class RAGStats(Base):
    __tablename__ = 'rag_stats'
    id = Column(Integer, primary_key=True)
    connector_id = Column(Integer, ForeignKey('rag_connectors.id'))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    requests_count = Column(Integer, default=0)
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    avg_response_time = Column(Float)
    error_count = Column(Integer, default=0)
```

3. **Create RAG Connector Routes** (`admin/backend/app/routes/rag_connectors.py`)
```python
@router.get("", response_model=List[RAGConnectorResponse])
async def list_connectors()

@router.post("", response_model=RAGConnectorResponse, status_code=201)
async def create_connector(connector_data: RAGConnectorCreate)

@router.put("/{connector_id}", response_model=RAGConnectorResponse)
async def update_connector(connector_id: int, connector_data: RAGConnectorUpdate)

@router.post("/{connector_id}/enable")
async def enable_connector(connector_id: int)

@router.post("/{connector_id}/disable")
async def disable_connector(connector_id: int)

@router.post("/{connector_id}/test")
async def test_connector(connector_id: int, test_query: str = None)

@router.get("/{connector_id}/stats")
async def get_connector_stats(connector_id: int, time_range: str = "1h")

@router.get("/{connector_id}/cache")
async def get_cache_info(connector_id: int)
```

4. **Connector Testing Logic**
```python
async def test_weather_connector(config: dict, test_query: str = None):
    """Test weather RAG connector with sample query."""
    city = test_query or "Chicago"
    url = f"http://192.168.10.167:8010/weather?location={city}"
    start = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            elapsed = time.time() - start
            if resp.status == 200:
                data = await resp.json()
                return {
                    "success": True,
                    "response_time": elapsed * 1000,
                    "sample_data": data,
                    "cached": resp.headers.get('X-Cache-Hit', 'false') == 'true'
                }
            else:
                return {"success": False, "error": f"HTTP {resp.status}"}
```

**Frontend Changes:**

1. **Add "RAG Connectors" Tab** (`admin/frontend/app.js`)
```javascript
<div id="rag-connectors" class="tab-content">
    <div class="section">
        <h2>RAG Connectors</h2>
        <button onclick="addConnector()">Add Custom Connector</button>
        <div id="connectors-list"></div>
    </div>
</div>
```

2. **Connector Card Component**
```javascript
function loadConnectors() {
    fetch('/api/rag-connectors')
        .then(r => r.json())
        .then(connectors => {
            const html = connectors.map(conn => `
                <div class="connector-card">
                    <div class="connector-header">
                        <h3>${conn.name}</h3>
                        <label class="switch">
                            <input type="checkbox" ${conn.enabled ? 'checked' : ''}
                                   onchange="toggleConnector(${conn.id}, this.checked)">
                            <span class="slider"></span>
                        </label>
                    </div>
                    <p>${conn.connector_type}</p>
                    <div class="connector-stats" id="stats-${conn.id}"></div>
                    <div class="connector-actions">
                        <button onclick="testConnector(${conn.id})">Test Connection</button>
                        <button onclick="editConnector(${conn.id})">Configure</button>
                        <button onclick="viewCacheStats(${conn.id})">Cache Stats</button>
                    </div>
                    <div id="test-results-${conn.id}" class="test-results"></div>
                </div>
            `).join('');
            document.getElementById('connectors-list').innerHTML = html;

            // Load stats for each connector
            connectors.forEach(conn => loadConnectorStats(conn.id));
        });
}
```

3. **Connector Testing Modal**
```javascript
function testConnector(connectorId) {
    const query = prompt("Enter test query (or leave blank for default):");
    fetch(`/api/rag-connectors/${connectorId}/test`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({test_query: query})
    })
    .then(r => r.json())
    .then(result => {
        const resultsDiv = document.getElementById(`test-results-${connectorId}`);
        if (result.success) {
            resultsDiv.innerHTML = `
                <div class="test-success">
                    ✓ Connection successful
                    <div>Response Time: ${result.response_time.toFixed(2)}ms</div>
                    <div>Cached: ${result.cached ? 'Yes' : 'No'}</div>
                    <details>
                        <summary>Sample Response</summary>
                        <pre>${JSON.stringify(result.sample_data, null, 2)}</pre>
                    </details>
                </div>
            `;
        } else {
            resultsDiv.innerHTML = `
                <div class="test-error">✗ Connection failed: ${result.error}</div>
            `;
        }
    });
}
```

### Phase 3.3: Voice Testing UI (16-20 hours)

**Note:** Adapted from deprecated Jetson implementation to current Mac Studio architecture.

**Backend Changes:**

1. **Create Voice Test Model** (`admin/backend/app/models.py`)
```python
class VoiceTest(Base):
    __tablename__ = 'voice_tests'
    id = Column(Integer, primary_key=True)
    test_type = Column(String(32))  # "stt", "tts", "llm", "full_pipeline", "rag_query"
    test_input = Column(Text)  # Audio file path, text query, etc.
    test_config = Column(JSONB)  # Test parameters
    result = Column(JSONB)  # Test results with timing
    success = Column(Boolean)
    error_message = Column(Text)
    executed_by_id = Column(Integer, ForeignKey('users.id'))
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
```

2. **Create Voice Testing Routes** (`admin/backend/app/routes/voice_tests.py`)
```python
@router.post("/stt/test")
async def test_speech_to_text(audio: UploadFile = File(...))
    """Test Wyoming Whisper STT service on Mac Studio."""

@router.post("/tts/test")
async def test_text_to_speech(text: str, voice: str = "default")
    """Test Wyoming Piper TTS service on Mac Studio."""

@router.post("/llm/test")
async def test_llm_processing(prompt: str, model: str = "phi3:mini-q8")
    """Test Ollama LLM on Mac Studio."""

@router.post("/rag/test")
async def test_rag_query(query: str, connector: str = "weather")
    """Test RAG service with query."""

@router.post("/pipeline/test")
async def test_full_pipeline(text: str)
    """Test full voice pipeline: text → LLM → HA execution."""

@router.get("/tests/history")
async def get_test_history(test_type: str = None, limit: int = 50)
    """Get historical test results."""
```

3. **STT Testing Implementation**
```python
async def test_speech_to_text(audio: UploadFile):
    """Test Wyoming Whisper STT on Mac Studio (192.168.10.167:10300)."""
    # Save uploaded audio
    audio_path = f"/tmp/test_audio_{uuid.uuid4()}.wav"
    with open(audio_path, "wb") as f:
        f.write(await audio.read())

    # Call Wyoming STT service
    start = time.time()
    result = await call_wyoming_stt(audio_path, "192.168.10.167", 10300)
    elapsed = time.time() - start

    return {
        "success": True,
        "transcript": result["text"],
        "confidence": result.get("confidence", 1.0),
        "processing_time": elapsed * 1000,
        "model": "faster-whisper-tiny.en",
        "service": "mac-studio-whisper"
    }
```

4. **LLM Testing Implementation**
```python
async def test_llm_processing(prompt: str, model: str):
    """Test Ollama on Mac Studio (192.168.10.167:11434)."""
    url = "http://192.168.10.167:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    start = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            elapsed = time.time() - start
            if resp.status == 200:
                data = await resp.json()
                return {
                    "success": True,
                    "response": data["response"],
                    "processing_time": elapsed * 1000,
                    "model": model,
                    "tokens": data.get("eval_count", 0),
                    "tokens_per_second": data.get("eval_count", 0) / elapsed if elapsed > 0 else 0
                }
```

5. **Full Pipeline Testing**
```python
async def test_full_pipeline(text: str):
    """Test full voice pipeline adapted for Mac architecture."""
    timings = {}
    results = {}

    # 1. LLM Processing (Ollama on Mac Studio)
    start = time.time()
    llm_result = await test_llm_processing(text, "phi3:mini-q8")
    timings["llm"] = time.time() - start
    results["llm_response"] = llm_result["response"]

    # 2. RAG Enhancement (if query needs context)
    if needs_rag_context(text):
        start = time.time()
        rag_result = await query_rag_services(text)
        timings["rag"] = time.time() - start
        results["rag_context"] = rag_result

    # 3. Home Assistant Integration (execute command if applicable)
    if is_ha_command(results["llm_response"]):
        start = time.time()
        ha_result = await execute_ha_command(results["llm_response"])
        timings["ha_execution"] = time.time() - start
        results["ha_result"] = ha_result

    # 4. TTS Generation (Piper on Mac Studio)
    start = time.time()
    tts_result = await test_text_to_speech(results["llm_response"])
    timings["tts"] = time.time() - start
    results["audio_file"] = tts_result["audio_path"]

    total_time = sum(timings.values())

    return {
        "success": True,
        "timings": timings,
        "total_time": total_time * 1000,
        "results": results,
        "target_met": total_time < 5.0  # Target: under 5 seconds
    }
```

**Frontend Changes:**

1. **Add "Voice Testing" Tab** (`admin/frontend/app.js`)
```javascript
<div id="voice-testing" class="tab-content">
    <div class="section">
        <h2>Component Tests</h2>
        <div class="test-grid">
            <div class="test-card">
                <h3>Speech-to-Text</h3>
                <input type="file" id="stt-audio" accept="audio/*">
                <button onclick="testSTT()">Test STT</button>
                <div id="stt-results"></div>
            </div>

            <div class="test-card">
                <h3>Text-to-Speech</h3>
                <textarea id="tts-text" placeholder="Enter text to synthesize"></textarea>
                <button onclick="testTTS()">Test TTS</button>
                <audio id="tts-audio" controls></audio>
                <div id="tts-results"></div>
            </div>

            <div class="test-card">
                <h3>LLM Processing</h3>
                <textarea id="llm-prompt" placeholder="Enter prompt"></textarea>
                <select id="llm-model">
                    <option value="phi3:mini-q8">Phi-3 Mini (Fast)</option>
                    <option value="llama3.1:8b-q4">Llama 3.1 8B (Balanced)</option>
                </select>
                <button onclick="testLLM()">Test LLM</button>
                <div id="llm-results"></div>
            </div>

            <div class="test-card">
                <h3>RAG Query</h3>
                <textarea id="rag-query" placeholder="Enter query"></textarea>
                <select id="rag-connector">
                    <option value="weather">Weather</option>
                    <option value="airports">Airports</option>
                    <option value="sports">Sports</option>
                </select>
                <button onclick="testRAG()">Test RAG</button>
                <div id="rag-results"></div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Full Pipeline Test</h2>
        <textarea id="pipeline-text" placeholder="Enter query to test full pipeline"></textarea>
        <button onclick="testFullPipeline()">Run Full Pipeline Test</button>
        <div id="pipeline-results"></div>
        <div id="pipeline-timings"></div>
    </div>

    <div class="section">
        <h2>Test History</h2>
        <button onclick="loadTestHistory()">Refresh</button>
        <div id="test-history"></div>
    </div>
</div>
```

2. **STT Test Function**
```javascript
async function testSTT() {
    const fileInput = document.getElementById('stt-audio');
    if (!fileInput.files[0]) {
        alert('Please select an audio file');
        return;
    }

    const formData = new FormData();
    formData.append('audio', fileInput.files[0]);

    const resultsDiv = document.getElementById('stt-results');
    resultsDiv.innerHTML = '<div class="loading">Testing STT...</div>';

    try {
        const response = await fetch('/api/voice-tests/stt/test', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        resultsDiv.innerHTML = `
            <div class="test-success">
                <strong>Transcript:</strong> ${result.transcript}
                <div class="metrics">
                    <span>Processing Time: ${result.processing_time.toFixed(2)}ms</span>
                    <span>Confidence: ${(result.confidence * 100).toFixed(1)}%</span>
                    <span>Model: ${result.model}</span>
                </div>
            </div>
        `;
    } catch (error) {
        resultsDiv.innerHTML = `<div class="test-error">Error: ${error.message}</div>`;
    }
}
```

3. **Full Pipeline Test Visualization**
```javascript
async function testFullPipeline() {
    const text = document.getElementById('pipeline-text').value;
    if (!text) {
        alert('Please enter a query');
        return;
    }

    const resultsDiv = document.getElementById('pipeline-results');
    const timingsDiv = document.getElementById('pipeline-timings');

    resultsDiv.innerHTML = '<div class="loading">Running full pipeline test...</div>';

    try {
        const response = await fetch('/api/voice-tests/pipeline/test', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text})
        });
        const result = await response.json();

        // Display results
        resultsDiv.innerHTML = `
            <div class="pipeline-result ${result.target_met ? 'success' : 'warning'}">
                <h3>Pipeline Results ${result.target_met ? '✓' : '⚠'}</h3>
                <p><strong>Total Time:</strong> ${result.total_time.toFixed(2)}ms
                   (Target: < 5000ms)</p>
                <div class="result-section">
                    <strong>LLM Response:</strong>
                    <p>${result.results.llm_response}</p>
                </div>
                ${result.results.rag_context ? `
                    <div class="result-section">
                        <strong>RAG Context:</strong>
                        <pre>${JSON.stringify(result.results.rag_context, null, 2)}</pre>
                    </div>
                ` : ''}
                ${result.results.ha_result ? `
                    <div class="result-section">
                        <strong>Home Assistant:</strong>
                        <p>${result.results.ha_result}</p>
                    </div>
                ` : ''}
            </div>
        `;

        // Display timing breakdown
        const timingHtml = Object.entries(result.timings).map(([stage, time]) => {
            const percentage = (time / (result.total_time / 1000)) * 100;
            return `
                <div class="timing-bar">
                    <label>${stage}</label>
                    <div class="bar-container">
                        <div class="bar" style="width: ${percentage}%"></div>
                    </div>
                    <span>${(time * 1000).toFixed(2)}ms</span>
                </div>
            `;
        }).join('');

        timingsDiv.innerHTML = `
            <h3>Timing Breakdown</h3>
            ${timingHtml}
        `;
    } catch (error) {
        resultsDiv.innerHTML = `<div class="test-error">Error: ${error.message}</div>`;
    }
}
```

## Database Migrations

Create Alembic migration for new tables:

```python
# admin/backend/alembic/versions/003_add_settings_and_testing.py

def upgrade():
    # Server configuration tables
    op.create_table('server_configs', ...)
    op.create_table('service_registry', ...)

    # RAG connector tables
    op.create_table('rag_connectors', ...)
    op.create_table('rag_stats', ...)

    # Voice testing tables
    op.create_table('voice_tests', ...)

def downgrade():
    op.drop_table('voice_tests')
    op.drop_table('rag_stats')
    op.drop_table('rag_connectors')
    op.drop_table('service_registry')
    op.create_table('server_configs')
```

## Setup Script Updates

Update `/tmp/admin-setup.py` to initialize:
1. Default server configurations (Mac Studio, Mac mini, Home Assistant)
2. Default service registry (all current services)
3. Default RAG connectors (Weather, Airports, Sports)

## Testing Plan

1. **Server Configuration:**
   - Add/edit/delete servers
   - Check server health
   - View service status per server

2. **RAG Connectors:**
   - Enable/disable connectors
   - Test each connector with sample queries
   - View cache statistics
   - Configure connector settings

3. **Voice Testing:**
   - Test STT with sample audio
   - Test TTS with sample text
   - Test LLM with various prompts
   - Test RAG queries
   - Run full pipeline test
   - View test history

## Deployment

1. Run database migrations
2. Run updated setup script
3. Build frontend + backend images (v5)
4. Deploy to thor cluster
5. Verify all new features work
6. Update documentation

## Success Criteria

- [ ] All three tab sections functional
- [ ] Server configuration editable and persisted
- [ ] RAG connectors manageable with live testing
- [ ] Voice testing adapted to Mac architecture
- [ ] All tests produce accurate timing metrics
- [ ] Test history viewable and filterable
- [ ] No regressions in Phase 2 features

## Architecture Notes

**Key Differences from Deprecated Jetson Implementation:**

1. **Wake Word Detection:** Not implemented in current architecture (future enhancement)
2. **STT Service:** Wyoming protocol on Mac Studio (port 10300), not Jetson
3. **TTS Service:** Wyoming protocol on Mac Studio (port 10200), not Jetson
4. **LLM:** Ollama on Mac Studio (port 11434), not edge inference on Jetson
5. **RAG Services:** Mac Studio for API services, Mac mini for storage (Qdrant/Redis)
6. **Testing Focus:** Component-level testing and pipeline testing without wake word stage

The voice testing UI will focus on the components that exist in the current architecture, with placeholders for future wake word testing when that gets implemented.

---

**Estimated Total Effort:** 28-38 hours
**Priority Order:** Server Config → RAG Connectors → Voice Testing
**Target Completion:** 2-3 development sessions
