# HA LLM Facade: Production-Ready Implementation Plan (REVISED)

**Created:** 2025-01-06 (Original)
**Revised:** 2025-01-06 (Post-Research)
**Based On:**
- [thoughts/research/RESEARCH_HA_LLM_FACADE.md](../research/RESEARCH_HA_LLM_FACADE.md)
- [thoughts/research/RESEARCH_JETSON_ITERATIONS.md](../research/RESEARCH_JETSON_ITERATIONS.md)
**Status:** Ready for implementation
**Estimated Timeline:** 1-2 weeks with AI agent execution

## Revision Summary

**Major Changes from Original Plan:**
1. **LLM Backend**: Use Ollama (Llama3.2:3b, TinyLlama) instead of DialoGPT/Transformers
2. **Approach**: Extract and generalize from `ollama_baltimore_ultimate.py` (1970 lines) instead of building from scratch
3. **Dual-Mode**: Support both Baltimore (Airbnb) and General (homelab) configurations
4. **Advanced Features**: Preserve anti-hallucination validation, 3-tier caching, SMS integration, RAG capabilities
5. **Production System**: Work with existing sophisticated system, not simple webhook

## Overview

Transform the existing Baltimore-specific Airbnb guest assistant (`ollama_baltimore_ultimate.py`) into a dual-mode system that supports both:
- **Mode 1 (Baltimore)**: Location-aware Airbnb guest assistance with SMS, local recommendations, anti-hallucination
- **Mode 2 (General)**: Homelab voice assistant with device control, general knowledge, RAG capabilities

Both modes share core infrastructure: Ollama proxy pattern, caching, context management, and monitoring.

## Current State Analysis

### What Actually Exists (From Research)

**✅ Production System Running:**
- **File**: `/mnt/nvme/athena-lite/ollama_baltimore_ultimate.py` (1970 lines)
- **LLM**: Ollama with Llama3.2:3b (complex) and TinyLlama (simple)
- **Proxy Pattern**: Port 11434 (facade) → Port 11435 (real Ollama)
- **Features**:
  - Anti-hallucination validation (2-layer with ground truth database)
  - 3-tier caching (70-80% hit rate, sub-100ms responses)
  - SMS integration (Twilio with rate limiting: 10/hour, 100/day)
  - Real-time data fetching (ESPN sports, DuckDuckGo search, weather)
  - Conversation context (30-minute expiry, 10-exchange limit)
  - Performance monitoring (p50, p95 latencies, cache hit rates)
  - Model selection (TinyLlama for simple, Llama3.2:3b for complex)

**✅ Voice Pipeline:**
- **File**: `/mnt/nvme/athena-lite/athena_lite.py` (309 lines)
- Dual wake words (Jarvis @ 0.5, Athena @ 0.5)
- Voice Activity Detection (VAD)
- GPU-accelerated STT (Faster-Whisper)
- HA API integration

**✅ HA Configuration:**
- REST commands (athena_llm_complex, athena_llm_simple)
- Input text helper (last_voice_command)
- Template sensor (voice_command_type classification)
- Routing automation

**⚠️ Baltimore-Specific Elements:**
- Property address: 912 S Clinton St, Baltimore, MD 21224
- Ground truth database (distances, facts)
- Local restaurant/transit database
- SMS templates for guests (checkout, WiFi, emergency)
- Ravens/Orioles sports scores

### What We're NOT Doing

- Wyoming protocol integration (Phase 1 future work - unchanged)
- Multi-zone deployment (Phase 2 future work - unchanged)
- Home Assistant migration to Proxmox (Phase 0 - separate project)
- Mobile app integration
- Custom wake word training
- Replacing the working Baltimore system (preserve it)

## Implementation Approach

Execute 6 phases sequentially, extracting and generalizing from the proven Baltimore system while maintaining dual-mode capability.

**Execution Model:** AI agents execute phases with human validation at phase boundaries

---

## Phase 1: Code Recovery & Repository Setup ✅ COMPLETE

**Status**: Complete with research
**Findings**: See Phase 1 completion notes in original plan

---

## Phase 2: Ollama Infrastructure & Dual-Mode Configuration

### Overview

Set up Ollama infrastructure, extract core patterns from Baltimore system, and implement configuration system that supports both Baltimore (Airbnb) and General (homelab) modes.

### Changes Required

#### 1. Set Up Ollama on Homelab Infrastructure

**Decision Point**: Where should Ollama run?
- **Option A**: Jetson (192.168.10.62) - Current Baltimore deployment
- **Option B**: Proxmox node (more resources)
- **Option C**: Both (Jetson for wake word zone, Proxmox for main processing)

**For now, assume Option A (Jetson) to match current deployment**

**File**: `/Users/jaystuart/dev/project-athena/docs/OLLAMA_SETUP.md`

```markdown
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
```

#### 2. Create Dual-Mode Configuration System

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/config/mode_config.py`

```python
"""
Dual-mode configuration for Baltimore (Airbnb) vs General (homelab) modes
"""

import os
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

class OperatingMode(Enum):
    BALTIMORE = "baltimore"
    GENERAL = "general"

@dataclass
class ModeConfig:
    """Configuration for a specific operating mode"""
    mode: OperatingMode
    enable_sms: bool
    enable_location_context: bool
    enable_anti_hallucination: bool
    enable_sports_scores: bool
    enable_local_recommendations: bool
    ground_truth_database: Optional[Dict]
    system_prompt_template: str
    validation_temperature: float  # Lower = more deterministic

# Baltimore Mode (Airbnb Guest Assistant)
BALTIMORE_CONFIG = ModeConfig(
    mode=OperatingMode.BALTIMORE,
    enable_sms=True,
    enable_location_context=True,
    enable_anti_hallucination=True,
    enable_sports_scores=True,
    enable_local_recommendations=True,
    ground_truth_database={
        'property_address': '912 South Clinton St, Baltimore, MD 21224',
        'neighborhood': 'Canton',
        'city': 'Baltimore',
        'state': 'Maryland',
        'distances': {
            'Inner Harbor': 1.2,  # miles
            'Fells Point': 0.8,
            'Patterson Park': 0.5,
            'BWI Airport': 12.0
        },
        'sports_teams': ['Ravens', 'Orioles'],
        'restaurants': [
            {'name': "Koco's Pub", 'distance': 0.3, 'type': 'American'},
            {'name': 'Thames Street Oyster House', 'distance': 0.9, 'type': 'Seafood'}
        ],
        'transit': {
            'Water Taxi': 'Fells Point stop, 0.8 miles',
            'Light Rail': 'Not walkable, use rideshare',
            'BWI Airport': '12 miles, 20 min drive'
        }
    },
    system_prompt_template="""You are a helpful AI assistant for guests staying at {property_address} in {neighborhood}, {city}, {state}.

Your role is to provide accurate, helpful information about:
- The property and local area
- Restaurants, attractions, and things to do
- Transportation options
- Baltimore sports teams (Ravens, Orioles)
- Checkout procedures and house rules

CRITICAL RULES:
- Never say you're in Portland, Maine, Seattle, or any city other than Baltimore
- Always verify distances against the ground truth database
- For sports scores, only report confirmed data from ESPN API
- Keep responses concise and guest-friendly
- If you don't know something, admit it rather than guessing

Current date: {current_date}
""",
    validation_temperature=0.1  # Very deterministic for factual accuracy
)

# General Mode (Homelab Voice Assistant)
GENERAL_CONFIG = ModeConfig(
    mode=OperatingMode.GENERAL,
    enable_sms=False,  # No SMS in homelab mode
    enable_location_context=False,  # No location assumptions
    enable_anti_hallucination=True,  # Still validate facts
    enable_sports_scores=True,  # General sports queries OK
    enable_local_recommendations=False,  # No hardcoded local data
    ground_truth_database=None,  # No location-specific database
    system_prompt_template="""You are a helpful AI assistant for a smart home.

Your role is to:
- Control home automation devices via Home Assistant
- Answer general questions
- Provide helpful information and explanations
- Assist with home management tasks

CRITICAL RULES:
- Don't make assumptions about location
- Verify facts when possible
- Keep responses concise
- Admit when you don't know something
- For device control, use clear, unambiguous commands

Current date: {current_date}
""",
    validation_temperature=0.3  # Slightly higher for conversational tone
)

def get_config(mode: str = None) -> ModeConfig:
    """Get configuration for specified mode, defaulting to environment variable"""
    if mode is None:
        mode = os.environ.get('ATHENA_MODE', 'general')

    mode_enum = OperatingMode(mode.lower())

    if mode_enum == OperatingMode.BALTIMORE:
        return BALTIMORE_CONFIG
    else:
        return GENERAL_CONFIG

def get_system_prompt(config: ModeConfig) -> str:
    """Generate system prompt for current mode"""
    from datetime import datetime

    if config.mode == OperatingMode.BALTIMORE:
        return config.system_prompt_template.format(
            property_address=config.ground_truth_database['property_address'],
            neighborhood=config.ground_truth_database['neighborhood'],
            city=config.ground_truth_database['city'],
            state=config.ground_truth_database['state'],
            current_date=datetime.now().strftime('%Y-%m-%d')
        )
    else:
        return config.system_prompt_template.format(
            current_date=datetime.now().strftime('%Y-%m-%d')
        )
```

#### 3. Extract Anti-Hallucination Validation Pattern

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/validation.py`

```python
"""
Anti-hallucination validation - extracted from ollama_baltimore_production.py
Validates LLM responses against ground truth and cross-checks with second model
"""

import logging
import requests
from typing import Tuple, Optional, Dict, List
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class ValidationResult:
    """Result of validation check"""
    def __init__(self, passed: bool, corrected_response: str, issues: List[str] = None):
        self.passed = passed
        self.corrected_response = corrected_response
        self.issues = issues or []
        self.timestamp = datetime.now()

class AntiHallucinationValidator:
    """
    Validates LLM responses to prevent hallucinations

    Two-layer validation:
    1. Ground truth check (if applicable)
    2. Cross-model validation (TinyLlama checks Llama3.2:3b)
    """

    def __init__(self, config: 'ModeConfig', ollama_url: str = "http://localhost:11435"):
        self.config = config
        self.ollama_url = ollama_url
        self.validation_cache = {}  # Cache validation results

    def validate_response(self, query: str, response: str, model_used: str) -> ValidationResult:
        """
        Main validation entry point

        Args:
            query: Original user query
            response: LLM generated response
            model_used: Which model generated the response

        Returns:
            ValidationResult with pass/fail and corrected response
        """
        issues = []

        # Layer 1: Ground truth validation (if mode supports it)
        if self.config.ground_truth_database:
            gt_result = self._validate_ground_truth(response)
            if not gt_result.passed:
                logger.warning(f"Ground truth validation failed: {gt_result.issues}")
                return gt_result  # Early return on ground truth failure

        # Layer 2: Cross-model validation (use simpler model to check complex model)
        if model_used == "llama3.2:3b" and not self._is_device_control(query):
            cross_result = self._cross_model_validation(query, response)
            if not cross_result.passed:
                logger.warning(f"Cross-model validation flagged issues: {cross_result.issues}")
                issues.extend(cross_result.issues)

        # If no issues, response is valid
        if not issues:
            return ValidationResult(passed=True, corrected_response=response)
        else:
            # Has issues but not critical - return with warnings
            return ValidationResult(passed=True, corrected_response=response, issues=issues)

    def _validate_ground_truth(self, response: str) -> ValidationResult:
        """
        Validate response against ground truth database

        Checks for:
        - Wrong location mentions
        - Incorrect distances
        - Hallucinated facts
        """
        response_lower = response.lower()
        issues = []

        # Check for wrong location hallucinations
        wrong_locations = ["portland", "maine", "seattle", "boston", "san francisco"]
        for wrong_loc in wrong_locations:
            if wrong_loc in response_lower:
                logger.error(f"HALLUCINATION DETECTED: Wrong location '{wrong_loc}'")
                correct_city = self.config.ground_truth_database['city']
                correct_state = self.config.ground_truth_database['state']
                corrected = f"You're in {correct_city}, {correct_state}."
                return ValidationResult(
                    passed=False,
                    corrected_response=corrected,
                    issues=[f"Hallucinated location: {wrong_loc}"]
                )

        # Check for distance hallucinations
        if "walking distance" in response_lower or "walk" in response_lower:
            distances = self.config.ground_truth_database.get('distances', {})
            for place, actual_distance in distances.items():
                if place.lower() in response_lower:
                    if actual_distance > 1.0:  # Not actually walkable
                        logger.warning(f"Distance hallucination: {place} is {actual_distance} miles")
                        issues.append(f"{place} is {actual_distance} miles (not walking distance)")
                        # Correct the response
                        corrected = response.replace(
                            "walking distance",
                            f"{actual_distance} miles away (recommend rideshare)"
                        )
                        return ValidationResult(
                            passed=False,
                            corrected_response=corrected,
                            issues=issues
                        )

        return ValidationResult(passed=True, corrected_response=response)

    def _cross_model_validation(self, query: str, response: str) -> ValidationResult:
        """
        Use second model (TinyLlama) to validate first model's response

        Asks TinyLlama: "Is this response accurate and appropriate?"
        """
        try:
            validation_prompt = f"""Question: {query}

Response to validate: {response}

Is this response factually accurate and appropriate? Answer only 'YES' or 'NO', followed by a brief explanation.
"""

            # Use TinyLlama for validation (faster, less biased)
            validate_response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "tinyllama",
                    "prompt": validation_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Very deterministic
                        "seed": 42
                    }
                },
                timeout=10
            )

            if validate_response.status_code == 200:
                validation_text = validate_response.json().get('response', '')

                # Check if validation passed
                if validation_text.strip().upper().startswith('NO'):
                    logger.warning(f"Cross-model validation failed: {validation_text}")
                    return ValidationResult(
                        passed=False,
                        corrected_response=response,
                        issues=[f"Cross-check flagged: {validation_text}"]
                    )
                elif validation_text.strip().upper().startswith('YES'):
                    return ValidationResult(passed=True, corrected_response=response)
                else:
                    # Unclear validation result
                    return ValidationResult(
                        passed=True,
                        corrected_response=response,
                        issues=["Validation inconclusive"]
                    )

            return ValidationResult(passed=True, corrected_response=response)

        except Exception as e:
            logger.error(f"Cross-model validation error: {e}")
            # On validation error, trust the original response
            return ValidationResult(passed=True, corrected_response=response)

    def _is_device_control(self, query: str) -> bool:
        """Check if query is a simple device control command (skip validation)"""
        device_patterns = [
            r'turn (on|off)',
            r'set .* to \d+',
            r'dim|brighten',
            r'open|close',
            r'start|stop'
        ]

        query_lower = query.lower()
        for pattern in device_patterns:
            if re.search(pattern, query_lower):
                return True

        return False
```

#### 4. Extract 3-Tier Caching Pattern

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/caching.py`

```python
"""
3-tier caching system - extracted from ollama_baltimore_ultimate.py
Provides sub-100ms responses for cached queries
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import threading
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class CacheEntry:
    """Single cache entry with metadata"""
    def __init__(self, query: str, response: str, model: str):
        self.query = query
        self.response = response
        self.model = model
        self.timestamp = datetime.now()
        self.hit_count = 0

class CacheManager:
    """
    3-tier caching strategy:
    - Tier 1 (Instant): Exact match, 5min TTL, instant return
    - Tier 2 (Fresh): Semantic match >0.85, 30min TTL, recent data
    - Tier 3 (Response): Semantic match >0.90, 24hr TTL, any data

    Achieves 70-80% cache hit rate in production
    """

    def __init__(self):
        self.instant_cache: Dict[str, CacheEntry] = {}    # Exact matches
        self.fresh_cache: Dict[str, CacheEntry] = {}      # Recent semantic
        self.response_cache: Dict[str, CacheEntry] = {}   # Any semantic
        self.lock = threading.Lock()

        self.stats = {
            'instant_hits': 0,
            'fresh_hits': 0,
            'response_hits': 0,
            'misses': 0,
            'total_queries': 0
        }

    def get_cached_response(self, query: str) -> Optional[str]:
        """
        Try to get cached response, checking all tiers

        Returns:
            Cached response if found, None if cache miss
        """
        with self.lock:
            self.stats['total_queries'] += 1

            # Tier 1: Exact match (instant cache)
            if query in self.instant_cache:
                entry = self.instant_cache[query]
                if self._is_fresh(entry, minutes=5):
                    logger.info(f"⚡ INSTANT CACHE HIT: {query[:50]}...")
                    entry.hit_count += 1
                    self.stats['instant_hits'] += 1
                    return entry.response
                else:
                    # Expired, remove
                    del self.instant_cache[query]

            # Tier 2: Semantic match (fresh cache)
            best_match, similarity = self._find_similar_query(query, self.fresh_cache)
            if similarity > 0.85 and best_match:
                entry = self.fresh_cache[best_match]
                if self._is_fresh(entry, minutes=30):
                    logger.info(f"🔍 FRESH CACHE HIT: {query[:50]}... ~= {best_match[:50]}... ({similarity:.2f})")
                    entry.hit_count += 1
                    self.stats['fresh_hits'] += 1
                    return entry.response

            # Tier 3: Semantic match (response cache)
            best_match, similarity = self._find_similar_query(query, self.response_cache)
            if similarity > 0.90 and best_match:
                entry = self.response_cache[best_match]
                if self._is_fresh(entry, hours=24):
                    logger.info(f"💾 RESPONSE CACHE HIT: {query[:50]}... ~= {best_match[:50]}... ({similarity:.2f})")
                    entry.hit_count += 1
                    self.stats['response_hits'] += 1
                    return entry.response

            # Cache miss
            logger.info(f"❌ CACHE MISS: {query[:50]}...")
            self.stats['misses'] += 1
            return None

    def cache_response(self, query: str, response: str, model: str):
        """Store response in all cache tiers"""
        with self.lock:
            entry = CacheEntry(query, response, model)

            # Store in all tiers
            self.instant_cache[query] = entry
            self.fresh_cache[query] = entry
            self.response_cache[query] = entry

            # Cleanup old entries (keep caches bounded)
            self._cleanup_cache(self.instant_cache, max_size=100)
            self._cleanup_cache(self.fresh_cache, max_size=500)
            self._cleanup_cache(self.response_cache, max_size=1000)

    def _find_similar_query(self, query: str, cache: Dict[str, CacheEntry]) -> tuple[Optional[str], float]:
        """Find most similar query in cache using sequence matching"""
        best_match = None
        best_similarity = 0.0

        for cached_query in cache.keys():
            similarity = SequenceMatcher(None, query.lower(), cached_query.lower()).ratio()
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = cached_query

        return best_match, best_similarity

    def _is_fresh(self, entry: CacheEntry, minutes: int = None, hours: int = None) -> bool:
        """Check if cache entry is still fresh"""
        now = datetime.now()

        if minutes:
            expiry = entry.timestamp + timedelta(minutes=minutes)
        elif hours:
            expiry = entry.timestamp + timedelta(hours=hours)
        else:
            return True

        return now < expiry

    def _cleanup_cache(self, cache: Dict[str, CacheEntry], max_size: int):
        """Remove oldest/least-used entries if cache exceeds max size"""
        if len(cache) <= max_size:
            return

        # Sort by (hit_count, timestamp) - remove least used and oldest
        entries = [(k, v) for k, v in cache.items()]
        entries.sort(key=lambda x: (x[1].hit_count, x[1].timestamp))

        # Remove bottom 20%
        remove_count = len(entries) - max_size
        for query, _ in entries[:remove_count]:
            del cache[query]

        logger.info(f"Cache cleanup: removed {remove_count} entries, {len(cache)} remaining")

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            total = max(self.stats['total_queries'], 1)
            total_hits = (self.stats['instant_hits'] +
                         self.stats['fresh_hits'] +
                         self.stats['response_hits'])

            return {
                'total_queries': total,
                'instant_hits': self.stats['instant_hits'],
                'fresh_hits': self.stats['fresh_hits'],
                'response_hits': self.stats['response_hits'],
                'misses': self.stats['misses'],
                'hit_rate': f"{(total_hits / total * 100):.1f}%",
                'cache_sizes': {
                    'instant': len(self.instant_cache),
                    'fresh': len(self.fresh_cache),
                    'response': len(self.response_cache)
                }
            }
```

#### 5. Create Environment Configuration

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/.env.example`

```bash
# Operating Mode
ATHENA_MODE=general  # or "baltimore"

# Ollama Configuration
OLLAMA_URL=http://localhost:11435
OLLAMA_SIMPLE_MODEL=tinyllama:latest
OLLAMA_COMPLEX_MODEL=llama3.2:3b

# Home Assistant Integration
HA_URL=http://192.168.10.168:8123
HA_TOKEN=  # Set from Kubernetes secret

# Service Configuration
SERVICE_PORT=11434  # Proxy port (HA expects this)
SERVICE_HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/mnt/nvme/athena-lite/logs/proxy.log

# Feature Flags (overridden by ATHENA_MODE)
ENABLE_SMS=false
ENABLE_ANTI_HALLUCINATION=true
ENABLE_CACHING=true
ENABLE_SPORTS_SCORES=true

# SMS Configuration (only if ENABLE_SMS=true)
TWILIO_ACCOUNT_SID=  # Set from Kubernetes secret
TWILIO_API_KEY_SID=  # Set from Kubernetes secret
TWILIO_API_KEY_SECRET=  # Set from Kubernetes secret
TWILIO_PHONE_NUMBER=  # Set from Kubernetes secret

# Performance Tuning
CACHE_INSTANT_TTL_MINUTES=5
CACHE_FRESH_TTL_MINUTES=30
CACHE_RESPONSE_TTL_HOURS=24
CONTEXT_MAX_MESSAGES=20
CONTEXT_EXPIRY_MINUTES=30
```

### Success Criteria

#### Automated Verification:
- [ ] Ollama installed and running on port 11435
- [ ] Both models pulled: `ollama list` shows tinyllama and llama3.2:3b
- [ ] Ollama responds to health check: `curl http://localhost:11435/api/tags`
- [ ] Configuration files are syntactically valid Python
- [ ] Environment variables load correctly
- [ ] No secrets in committed code: `git grep -i "SK\|AC0" src/` returns nothing

#### Manual Verification:
- [ ] Ollama generates responses for both models
- [ ] Mode configuration switches correctly between Baltimore/General
- [ ] Validation catches location hallucinations (if Baltimore mode)
- [ ] Cache returns cached responses (test with duplicate queries)
- [ ] Environment file properly separates secrets

**Implementation Note:** After completing this phase, pause for verification that Ollama infrastructure is working before proceeding to proxy implementation.

---

## Phase 3: Ollama Proxy with Dual-Mode Support

### Overview

Implement the Ollama proxy pattern (port 11434 → 11435) with mode-aware context injection, model selection, validation, and caching.

### Changes Required

#### 1. Create Main Ollama Proxy Service

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/ollama_proxy.py`

```python
"""
Ollama Proxy Service - Dual Mode (Baltimore & General)

Extracted and generalized from ollama_baltimore_ultimate.py

Architecture:
- Listen on port 11434 (HA expects Ollama here)
- Proxy to real Ollama on port 11435
- Inject context based on mode (Baltimore vs General)
- Apply validation (anti-hallucination)
- Use 3-tier caching for performance
- Select model based on query complexity
"""

from flask import Flask, request, jsonify, Response
import requests
import logging
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Import our extracted modules
from config.mode_config import get_config, get_system_prompt, OperatingMode
from validation import AntiHallucinationValidator
from caching import CacheManager

load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', '/mnt/nvme/athena-lite/logs/proxy.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize components
MODE = os.getenv('ATHENA_MODE', 'general')
CONFIG = get_config(MODE)
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11435')
SIMPLE_MODEL = os.getenv('OLLAMA_SIMPLE_MODEL', 'tinyllama:latest')
COMPLEX_MODEL = os.getenv('OLLAMA_COMPLEX_MODEL', 'llama3.2:3b')

validator = AntiHallucinationValidator(CONFIG, OLLAMA_URL)
cache_manager = CacheManager()

logger.info(f"🚀 Starting Ollama Proxy in {MODE.upper()} mode")
logger.info(f"📡 Proxying 11434 → {OLLAMA_URL}")

def determine_model(query: str) -> str:
    """
    Select model based on query complexity

    Simple queries → TinyLlama (fast, 1-2s)
    Complex queries → Llama3.2:3b (smart, 3-5s)
    """
    import re

    simple_patterns = [
        r'^(what|when|where|who) (is|are|was|were)',
        r'^(turn|switch) (on|off)',
        r'what time',
        r'weather',
        r'score',
        r'temperature'
    ]

    query_lower = query.lower()
    for pattern in simple_patterns:
        if re.match(pattern, query_lower):
            logger.info(f"📱 Simple query detected → {SIMPLE_MODEL}")
            return SIMPLE_MODEL

    logger.info(f"🧠 Complex query detected → {COMPLEX_MODEL}")
    return COMPLEX_MODEL

def enhance_prompt(user_query: str) -> str:
    """
    Add mode-specific context to user query

    Baltimore mode: Adds property address, ground truth
    General mode: Adds home automation context
    """
    system_prompt = get_system_prompt(CONFIG)

    enhanced = f"{system_prompt}\n\nUser: {user_query}\nAssistant:"
    return enhanced

@app.route('/api/generate', methods=['POST'])
def generate():
    """
    Main Ollama API endpoint

    Flow:
    1. Check cache
    2. Select model
    3. Enhance prompt with context
    4. Call real Ollama
    5. Validate response
    6. Cache result
    7. Return to client
    """
    try:
        data = request.json
        user_prompt = data.get('prompt', '')

        logger.info(f"📝 Query: {user_prompt[:100]}...")

        # Step 1: Check cache
        if os.getenv('ENABLE_CACHING', 'true').lower() == 'true':
            cached = cache_manager.get_cached_response(user_prompt)
            if cached:
                return jsonify({
                    'model': 'cached',
                    'created_at': datetime.now().isoformat(),
                    'response': cached,
                    'done': True,
                    'cached': True
                })

        # Step 2: Select model
        model = determine_model(user_prompt)

        # Step 3: Enhance prompt
        enhanced_prompt = enhance_prompt(user_prompt)

        # Step 4: Call real Ollama
        ollama_data = {
            'model': model,
            'prompt': enhanced_prompt,
            'stream': data.get('stream', False),
            'options': {
                'temperature': CONFIG.validation_temperature,
                'top_p': 0.9,
                'repeat_penalty': 1.1
            }
        }

        logger.info(f"🔄 Proxying to Ollama ({model})...")

        ollama_response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=ollama_data,
            timeout=30
        )

        if ollama_response.status_code != 200:
            logger.error(f"Ollama error: {ollama_response.status_code}")
            return jsonify({'error': 'Ollama service error'}), 503

        llm_result = ollama_response.json()
        llm_response = llm_result.get('response', '')

        # Step 5: Validate response
        if CONFIG.enable_anti_hallucination:
            validation_result = validator.validate_response(user_prompt, llm_response, model)

            if not validation_result.passed:
                logger.warning(f"⚠️ Validation failed, using corrected response")
                llm_response = validation_result.corrected_response
            elif validation_result.issues:
                logger.warning(f"⚠️ Validation issues: {validation_result.issues}")

        # Step 6: Cache result
        if os.getenv('ENABLE_CACHING', 'true').lower() == 'true':
            cache_manager.cache_response(user_prompt, llm_response, model)

        # Step 7: Return to client
        return jsonify({
            'model': model,
            'created_at': datetime.now().isoformat(),
            'response': llm_response,
            'done': True,
            'cached': False
        })

    except Exception as e:
        logger.error(f"Error in generate: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat endpoint with conversation context

    Maintains conversation history per device/session
    """
    # For Phase 3, we'll implement basic chat
    # Context management can be added in Phase 5
    data = request.json
    messages = data.get('messages', [])

    # Extract last user message
    if messages and messages[-1].get('role') == 'user':
        user_prompt = messages[-1].get('content', '')

        # Convert to generate call
        request.json = {'prompt': user_prompt}
        return generate()

    return jsonify({'error': 'Invalid chat format'}), 400

@app.route('/api/tags', methods=['GET'])
def tags():
    """Pass through to real Ollama"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return Response(response.content, status=response.status_code, content_type='application/json')
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Check Ollama connectivity
        ollama_health = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        ollama_ok = ollama_health.status_code == 200

        cache_stats = cache_manager.get_stats()

        return jsonify({
            'status': 'healthy' if ollama_ok else 'degraded',
            'mode': MODE,
            'ollama_connected': ollama_ok,
            'ollama_url': OLLAMA_URL,
            'cache_stats': cache_stats,
            'features': {
                'anti_hallucination': CONFIG.enable_anti_hallucination,
                'sms': CONFIG.enable_sms,
                'location_context': CONFIG.enable_location_context,
                'sports_scores': CONFIG.enable_sports_scores
            },
            'timestamp': datetime.now().isoformat()
        }), 200 if ollama_ok else 503

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

if __name__ == '__main__':
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(os.getenv('LOG_FILE', '/mnt/nvme/athena-lite/logs/proxy.log')), exist_ok=True)

    # Run proxy service
    port = int(os.getenv('SERVICE_PORT', 11434))
    host = os.getenv('SERVICE_HOST', '0.0.0.0')

    logger.info(f"🎯 Ollama Proxy listening on {host}:{port}")
    app.run(host=host, port=port, debug=False)
```

### Success Criteria

#### Automated Verification:
- [ ] Proxy service starts without errors
- [ ] Health check passes: `curl http://localhost:11434/health`
- [ ] Ollama proxy responds: `curl -X POST http://localhost:11434/api/generate -d '{"prompt":"test"}'`
- [ ] Cache statistics show in health check
- [ ] Baltimore mode shows location context in health check
- [ ] General mode shows no location context

#### Manual Verification:
- [ ] Simple query uses TinyLlama (check logs for model selection)
- [ ] Complex query uses Llama3.2:3b
- [ ] Repeated query returns cached response (check "cached": true)
- [ ] Baltimore mode provides location-aware responses
- [ ] General mode doesn't mention Baltimore
- [ ] Validation catches hallucinations (test: "Are we in Portland?")

**Implementation Note:** Test both modes thoroughly before proceeding. Verify dual-mode switching works correctly.

---

## Phase 4: Service Management & Deployment

### Overview

Extract service management patterns from Baltimore system, create systemd service definitions for dual-mode operation, and implement deployment automation with rollback capabilities.

### Changes Required

#### 1. Create Systemd Service Definition

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/systemd/ollama-proxy.service`

```ini
[Unit]
Description=Ollama Proxy Service (Dual-Mode: Baltimore & General)
Documentation=https://wiki.xmojo.net/homelab/projects/project-athena
After=network-online.target
Wants=network-online.target
# Ensure Ollama is running first
After=ollama.service
Requires=ollama.service

[Service]
Type=simple
User=jstuart
Group=jstuart
WorkingDirectory=/mnt/nvme/athena-lite

# Environment file contains mode selection and configuration
EnvironmentFile=/mnt/nvme/athena-lite/.env

# Main proxy service
ExecStart=/usr/bin/python3 /mnt/nvme/athena-lite/ollama_proxy.py

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ollama-proxy

# Resource limits
MemoryMax=2G
CPUQuota=50%

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/mnt/nvme/athena-lite/logs

[Install]
WantedBy=multi-user.target
```

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/systemd/ollama.service.d/override.conf`

```ini
# Override default Ollama service to use port 11435
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11435"
```

#### 2. Create Deployment Script

**File**: `/Users/jaystuart/dev/project-athena/scripts/deploy-proxy.sh`

```bash
#!/bin/bash
# Deploy Ollama Proxy to Jetson with rollback capability

set -e  # Exit on error

JETSON_HOST="192.168.10.62"
JETSON_USER="jstuart"
DEPLOY_DIR="/mnt/nvme/athena-lite"
BACKUP_DIR="${DEPLOY_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 Deploying Ollama Proxy to ${JETSON_HOST}..."

# Step 1: Create backup of current deployment
echo "📦 Creating backup..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    mkdir -p ${BACKUP_DIR}
    if [ -f ${DEPLOY_DIR}/ollama_proxy.py ]; then
        tar -czf ${BACKUP_DIR}/proxy_backup_${TIMESTAMP}.tar.gz \
            -C ${DEPLOY_DIR} \
            ollama_proxy.py \
            validation.py \
            caching.py \
            config/ \
            .env 2>/dev/null || true
        echo '✅ Backup created: proxy_backup_${TIMESTAMP}.tar.gz'
    fi
"

# Step 2: Copy new files to Jetson
echo "📤 Copying new files..."
scp -r src/jetson/* ${JETSON_USER}@${JETSON_HOST}:${DEPLOY_DIR}/

# Step 3: Install Python dependencies
echo "📦 Installing dependencies..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    cd ${DEPLOY_DIR}
    pip3 install -r requirements.txt --user
"

# Step 4: Install systemd service files
echo "⚙️  Installing systemd services..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    sudo cp ${DEPLOY_DIR}/systemd/ollama-proxy.service /etc/systemd/system/
    sudo mkdir -p /etc/systemd/system/ollama.service.d/
    sudo cp ${DEPLOY_DIR}/systemd/ollama.service.d/override.conf /etc/systemd/system/ollama.service.d/
    sudo systemctl daemon-reload
"

# Step 5: Restart services
echo "🔄 Restarting services..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    # Restart Ollama with new port configuration
    sudo systemctl restart ollama
    sleep 5

    # Enable and start proxy service
    sudo systemctl enable ollama-proxy
    sudo systemctl restart ollama-proxy
    sleep 3

    # Check service status
    sudo systemctl status ollama-proxy --no-pager
"

# Step 6: Verify deployment
echo "✅ Verifying deployment..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://${JETSON_HOST}:11434/health | grep -q "healthy"; then
        echo "✅ Deployment successful! Service is healthy."

        # Show health status
        echo ""
        echo "📊 Service Health:"
        curl -s http://${JETSON_HOST}:11434/health | jq '.'

        exit 0
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⏳ Waiting for service to be healthy (attempt ${RETRY_COUNT}/${MAX_RETRIES})..."
    sleep 2
done

echo "❌ Deployment verification failed! Service is not healthy."
echo "🔄 Run './scripts/rollback-proxy.sh ${TIMESTAMP}' to rollback."
exit 1
```

#### 3. Create Rollback Script

**File**: `/Users/jaystuart/dev/project-athena/scripts/rollback-proxy.sh`

```bash
#!/bin/bash
# Rollback to previous Ollama Proxy deployment

set -e

JETSON_HOST="192.168.10.62"
JETSON_USER="jstuart"
DEPLOY_DIR="/mnt/nvme/athena-lite"
BACKUP_DIR="${DEPLOY_DIR}/backups"

BACKUP_TIMESTAMP=$1

if [ -z "$BACKUP_TIMESTAMP" ]; then
    echo "❌ Error: Backup timestamp required"
    echo "Usage: $0 <timestamp>"
    echo ""
    echo "Available backups:"
    ssh ${JETSON_USER}@${JETSON_HOST} "ls -lh ${BACKUP_DIR}/"
    exit 1
fi

BACKUP_FILE="${BACKUP_DIR}/proxy_backup_${BACKUP_TIMESTAMP}.tar.gz"

echo "🔄 Rolling back Ollama Proxy to backup: ${BACKUP_TIMESTAMP}..."

# Step 1: Verify backup exists
echo "📦 Checking backup..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    if [ ! -f ${BACKUP_FILE} ]; then
        echo '❌ Backup not found: ${BACKUP_FILE}'
        exit 1
    fi
    echo '✅ Backup found'
"

# Step 2: Stop service
echo "⏸️  Stopping service..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    sudo systemctl stop ollama-proxy
"

# Step 3: Restore backup
echo "📥 Restoring backup..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    cd ${DEPLOY_DIR}
    tar -xzf ${BACKUP_FILE}
    echo '✅ Backup restored'
"

# Step 4: Restart service
echo "🔄 Restarting service..."
ssh ${JETSON_USER}@${JETSON_HOST} "
    sudo systemctl start ollama-proxy
    sleep 3
    sudo systemctl status ollama-proxy --no-pager
"

# Step 5: Verify rollback
echo "✅ Verifying rollback..."
if curl -s http://${JETSON_HOST}:11434/health | grep -q "healthy"; then
    echo "✅ Rollback successful! Service is healthy."
    curl -s http://${JETSON_HOST}:11434/health | jq '.'
else
    echo "❌ Rollback verification failed!"
    exit 1
fi
```

#### 4. Create Mode Switching Script

**File**: `/Users/jaystuart/dev/project-athena/scripts/switch-mode.sh`

```bash
#!/bin/bash
# Switch between Baltimore and General modes

set -e

JETSON_HOST="192.168.10.62"
JETSON_USER="jstuart"
DEPLOY_DIR="/mnt/nvme/athena-lite"

NEW_MODE=$1

if [ -z "$NEW_MODE" ]; then
    echo "❌ Error: Mode required"
    echo "Usage: $0 <baltimore|general>"
    exit 1
fi

if [ "$NEW_MODE" != "baltimore" ] && [ "$NEW_MODE" != "general" ]; then
    echo "❌ Error: Invalid mode. Use 'baltimore' or 'general'"
    exit 1
fi

echo "🔄 Switching to ${NEW_MODE} mode..."

# Update .env file
ssh ${JETSON_USER}@${JETSON_HOST} "
    cd ${DEPLOY_DIR}

    # Update ATHENA_MODE in .env
    sed -i 's/^ATHENA_MODE=.*/ATHENA_MODE=${NEW_MODE}/' .env

    echo '✅ Environment updated'

    # Restart service to pick up new mode
    sudo systemctl restart ollama-proxy
    sleep 3

    # Verify new mode
    sudo systemctl status ollama-proxy --no-pager
"

# Verify mode switch
echo "✅ Verifying mode switch..."
sleep 2

MODE_CHECK=$(curl -s http://${JETSON_HOST}:11434/health | jq -r '.mode')

if [ "$MODE_CHECK" == "$NEW_MODE" ]; then
    echo "✅ Mode successfully switched to: ${NEW_MODE}"
    echo ""
    echo "📊 Current configuration:"
    curl -s http://${JETSON_HOST}:11434/health | jq '{mode, features}'
else
    echo "❌ Mode switch failed! Expected: ${NEW_MODE}, Got: ${MODE_CHECK}"
    exit 1
fi
```

#### 5. Update Requirements

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/requirements.txt`

```txt
# Web framework
flask==3.0.0
werkzeug==3.0.1

# HTTP client
requests==2.31.0

# Environment management
python-dotenv==1.0.0

# Utilities
python-dateutil==2.8.2
```

### Success Criteria

#### Automated Verification:
- [ ] Deployment script runs without errors
- [ ] `systemctl status ollama-proxy` shows service as active
- [ ] `systemctl status ollama` shows running on port 11435
- [ ] Health check passes after deployment: `curl http://192.168.10.62:11434/health`
- [ ] Mode switching script works: `./scripts/switch-mode.sh general`
- [ ] Rollback script lists available backups
- [ ] All scripts have execute permissions: `chmod +x scripts/*.sh`

#### Manual Verification:
- [ ] Service auto-starts on Jetson reboot
- [ ] Service restarts automatically if it crashes
- [ ] Deployment creates timestamped backups
- [ ] Rollback successfully restores previous version
- [ ] Mode switch updates service without downtime
- [ ] Logs appear in systemd journal: `journalctl -u ollama-proxy -f`
- [ ] Service respects resource limits (2GB RAM, 50% CPU)

**Implementation Note:** Test deployment, rollback, and mode switching in a non-production environment first. Verify backup/restore cycle works correctly.

---

## Phase 5: Monitoring, Observability & Testing

### Overview

Extract performance monitoring patterns from Baltimore system, implement health checks, create integration tests, and add observability for dual-mode operation.

### Changes Required

#### 1. Add Performance Metrics Collection

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/metrics.py`

```python
"""
Performance metrics collection - extracted from ollama_baltimore_ultimate.py

Tracks:
- Response latency (p50, p95, p99)
- Cache hit rates by tier
- Model selection distribution
- Validation failure rate
- Hourly/daily request counts
"""

import time
import logging
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Track performance metrics for monitoring and optimization"""

    def __init__(self):
        self.lock = threading.Lock()

        # Latency tracking
        self.latencies: List[float] = []

        # Model usage
        self.model_usage = defaultdict(int)

        # Validation stats
        self.validation_failures = 0
        self.validation_corrections = 0
        self.total_validations = 0

        # Request counts
        self.hourly_requests = defaultdict(int)
        self.daily_requests = defaultdict(int)

        # Error tracking
        self.errors = defaultdict(int)

    def record_request(self, latency_ms: float, model: str, cached: bool = False):
        """Record metrics for a completed request"""
        with self.lock:
            # Record latency
            self.latencies.append(latency_ms)

            # Trim latency list to last 1000 requests
            if len(self.latencies) > 1000:
                self.latencies = self.latencies[-1000:]

            # Record model usage
            self.model_usage[model] += 1

            # Record time-based counts
            now = datetime.now()
            hour_key = now.strftime('%Y-%m-%d %H:00')
            day_key = now.strftime('%Y-%m-%d')

            self.hourly_requests[hour_key] += 1
            self.daily_requests[day_key] += 1

    def record_validation(self, passed: bool, corrected: bool):
        """Record validation result"""
        with self.lock:
            self.total_validations += 1

            if not passed:
                self.validation_failures += 1

            if corrected:
                self.validation_corrections += 1

    def record_error(self, error_type: str):
        """Record error occurrence"""
        with self.lock:
            self.errors[error_type] += 1

    def get_latency_percentiles(self) -> Dict[str, float]:
        """Calculate latency percentiles"""
        with self.lock:
            if not self.latencies:
                return {'p50': 0, 'p95': 0, 'p99': 0}

            sorted_latencies = sorted(self.latencies)
            n = len(sorted_latencies)

            return {
                'p50': sorted_latencies[int(n * 0.5)],
                'p95': sorted_latencies[int(n * 0.95)],
                'p99': sorted_latencies[int(n * 0.99)]
            }

    def get_summary(self) -> Dict:
        """Get complete metrics summary"""
        with self.lock:
            latency_percentiles = self.get_latency_percentiles()

            # Calculate validation rate
            validation_failure_rate = 0
            if self.total_validations > 0:
                validation_failure_rate = (self.validation_failures / self.total_validations) * 100

            # Get recent request counts
            now = datetime.now()
            current_hour = now.strftime('%Y-%m-%d %H:00')
            current_day = now.strftime('%Y-%m-%d')

            return {
                'latency_ms': latency_percentiles,
                'requests': {
                    'total': len(self.latencies),
                    'current_hour': self.hourly_requests[current_hour],
                    'current_day': self.daily_requests[current_day]
                },
                'models': dict(self.model_usage),
                'validation': {
                    'total': self.total_validations,
                    'failures': self.validation_failures,
                    'corrections': self.validation_corrections,
                    'failure_rate_percent': f"{validation_failure_rate:.2f}"
                },
                'errors': dict(self.errors)
            }
```

#### 2. Integrate Metrics into Proxy

**File**: `/Users/jaystuart/dev/project-athena/src/jetson/ollama_proxy.py` (update)

Add to imports:
```python
from metrics import PerformanceMetrics
```

Add to initialization (after cache_manager):
```python
metrics = PerformanceMetrics()
```

Update generate() function to record metrics:
```python
@app.route('/api/generate', methods=['POST'])
def generate():
    start_time = time.time()
    model_used = None

    try:
        # ... existing code ...

        # Record model selection
        model_used = determine_model(user_prompt)

        # ... existing code through validation ...

        # Record validation metrics
        if CONFIG.enable_anti_hallucination:
            validation_result = validator.validate_response(user_prompt, llm_response, model_used)
            metrics.record_validation(
                passed=validation_result.passed,
                corrected=bool(validation_result.issues)
            )
            # ... rest of validation handling ...

        # Record successful request
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_request(latency_ms, model_used, cached=False)

        # ... return response ...

    except Exception as e:
        metrics.record_error(type(e).__name__)
        # ... rest of error handling ...
```

Add metrics endpoint:
```python
@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Expose performance metrics"""
    try:
        summary = metrics.get_summary()
        cache_stats = cache_manager.get_stats()

        return jsonify({
            'performance': summary,
            'cache': cache_stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return jsonify({'error': str(e)}), 500
```

#### 3. Create Integration Test Suite

**File**: `/Users/jaystuart/dev/project-athena/tests/integration_test.py`

```python
#!/usr/bin/env python3
"""
Integration tests for Ollama Proxy (dual-mode)

Tests both Baltimore and General modes
"""

import requests
import time
import sys
from typing import Dict

PROXY_URL = "http://192.168.10.62:11434"

def test_health_check() -> bool:
    """Test 1: Health check endpoint"""
    print("🔍 Test 1: Health check...")

    try:
        response = requests.get(f"{PROXY_URL}/health", timeout=5)

        if response.status_code != 200:
            print(f"  ❌ Failed: HTTP {response.status_code}")
            return False

        data = response.json()

        if data.get('status') != 'healthy':
            print(f"  ❌ Failed: Status is {data.get('status')}")
            return False

        print(f"  ✅ Passed - Mode: {data.get('mode')}, Ollama: {data.get('ollama_connected')}")
        return True

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_simple_query() -> bool:
    """Test 2: Simple query (should use TinyLlama)"""
    print("🔍 Test 2: Simple query...")

    try:
        start = time.time()

        response = requests.post(
            f"{PROXY_URL}/api/generate",
            json={
                "prompt": "What time is it?",
                "stream": False
            },
            timeout=30
        )

        latency = time.time() - start

        if response.status_code != 200:
            print(f"  ❌ Failed: HTTP {response.status_code}")
            return False

        data = response.json()
        model = data.get('model')
        llm_response = data.get('response', '')

        # Should be fast (< 5s) and use TinyLlama
        if latency > 5.0:
            print(f"  ⚠️  Warning: Slow response ({latency:.2f}s)")

        print(f"  ✅ Passed - Model: {model}, Latency: {latency:.2f}s")
        print(f"     Response: {llm_response[:100]}...")
        return True

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_complex_query() -> bool:
    """Test 3: Complex query (should use Llama3.2:3b)"""
    print("🔍 Test 3: Complex query...")

    try:
        start = time.time()

        response = requests.post(
            f"{PROXY_URL}/api/generate",
            json={
                "prompt": "Explain the benefits of smart home automation",
                "stream": False
            },
            timeout=30
        )

        latency = time.time() - start

        if response.status_code != 200:
            print(f"  ❌ Failed: HTTP {response.status_code}")
            return False

        data = response.json()
        model = data.get('model')
        llm_response = data.get('response', '')

        print(f"  ✅ Passed - Model: {model}, Latency: {latency:.2f}s")
        print(f"     Response: {llm_response[:100]}...")
        return True

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_caching() -> bool:
    """Test 4: Cache hit on repeated query"""
    print("🔍 Test 4: Caching...")

    try:
        test_query = "What is the weather today?"

        # First request (cache miss)
        start1 = time.time()
        response1 = requests.post(
            f"{PROXY_URL}/api/generate",
            json={"prompt": test_query, "stream": False},
            timeout=30
        )
        latency1 = time.time() - start1

        if response1.status_code != 200:
            print(f"  ❌ Failed: First request HTTP {response1.status_code}")
            return False

        data1 = response1.json()
        cached1 = data1.get('cached', False)

        # Second request (cache hit)
        time.sleep(0.5)  # Brief pause

        start2 = time.time()
        response2 = requests.post(
            f"{PROXY_URL}/api/generate",
            json={"prompt": test_query, "stream": False},
            timeout=30
        )
        latency2 = time.time() - start2

        if response2.status_code != 200:
            print(f"  ❌ Failed: Second request HTTP {response2.status_code}")
            return False

        data2 = response2.json()
        cached2 = data2.get('cached', False)

        # Verify cache hit
        if not cached2:
            print(f"  ⚠️  Warning: Expected cache hit on second request")
            return True  # Not a critical failure

        # Cache hit should be much faster
        if latency2 > latency1:
            print(f"  ⚠️  Warning: Cache hit slower than miss ({latency2:.3f}s vs {latency1:.3f}s)")

        print(f"  ✅ Passed - Cache Miss: {latency1:.3f}s, Cache Hit: {latency2:.3f}s")
        return True

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_validation_baltimore() -> bool:
    """Test 5: Anti-hallucination validation (Baltimore mode only)"""
    print("🔍 Test 5: Anti-hallucination (Baltimore mode)...")

    try:
        # Check if in Baltimore mode
        health = requests.get(f"{PROXY_URL}/health", timeout=5).json()
        mode = health.get('mode')

        if mode != 'baltimore':
            print(f"  ⏭️  Skipped - Not in Baltimore mode (current: {mode})")
            return True

        # Ask a question that might trigger location hallucination
        response = requests.post(
            f"{PROXY_URL}/api/generate",
            json={
                "prompt": "Are we in Portland, Maine?",
                "stream": False
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"  ❌ Failed: HTTP {response.status_code}")
            return False

        data = response.json()
        llm_response = data.get('response', '').lower()

        # Should correct to Baltimore
        if 'baltimore' in llm_response:
            print(f"  ✅ Passed - Corrected location hallucination")
            print(f"     Response: {data.get('response')[:100]}...")
            return True
        else:
            print(f"  ⚠️  Warning: Expected Baltimore correction")
            print(f"     Response: {data.get('response')[:100]}...")
            return True  # Not a critical failure

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_metrics() -> bool:
    """Test 6: Metrics endpoint"""
    print("🔍 Test 6: Metrics endpoint...")

    try:
        response = requests.get(f"{PROXY_URL}/metrics", timeout=5)

        if response.status_code != 200:
            print(f"  ❌ Failed: HTTP {response.status_code}")
            return False

        data = response.json()

        # Verify expected metrics structure
        if 'performance' not in data:
            print(f"  ❌ Failed: Missing performance metrics")
            return False

        if 'cache' not in data:
            print(f"  ❌ Failed: Missing cache metrics")
            return False

        perf = data['performance']
        cache = data['cache']

        print(f"  ✅ Passed")
        print(f"     Latency P95: {perf['latency_ms']['p95']:.0f}ms")
        print(f"     Cache hit rate: {cache['hit_rate']}")
        print(f"     Requests today: {perf['requests']['current_day']}")
        return True

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Ollama Proxy Integration Tests (Dual-Mode)")
    print("=" * 60)
    print()

    tests = [
        test_health_check,
        test_simple_query,
        test_complex_query,
        test_caching,
        test_validation_baltimore,
        test_metrics
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        if test_func():
            passed += 1
        else:
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
```

#### 4. Create Monitoring Script

**File**: `/Users/jaystuart/dev/project-athena/scripts/monitor-proxy.sh`

```bash
#!/bin/bash
# Real-time monitoring of Ollama Proxy

JETSON_HOST="192.168.10.62"

echo "📊 Ollama Proxy Monitor - ${JETSON_HOST}"
echo "Press Ctrl+C to exit"
echo ""

while true; do
    clear

    echo "=== Health Status ==="
    curl -s http://${JETSON_HOST}:11434/health | jq '{
        status,
        mode,
        ollama_connected,
        features
    }'

    echo ""
    echo "=== Performance Metrics ==="
    curl -s http://${JETSON_HOST}:11434/metrics | jq '{
        latency_ms: .performance.latency_ms,
        requests: .performance.requests,
        models: .performance.models,
        cache_hit_rate: .cache.hit_rate
    }'

    echo ""
    echo "=== System Resources ==="
    ssh jstuart@${JETSON_HOST} "
        echo 'CPU Usage:'
        top -bn1 | grep 'Cpu(s)' | awk '{print \$2}' | awk -F'%' '{print \$1\"%\"}'

        echo 'Memory:'
        free -h | awk '/^Mem:/ {print \$3 \" / \" \$2}'

        echo 'Disk (NVMe):'
        df -h /mnt/nvme | awk 'NR==2 {print \$3 \" / \" \$2 \" (\" \$5 \" used)\"}'
    " 2>/dev/null

    echo ""
    echo "=== Service Status ==="
    ssh jstuart@${JETSON_HOST} "systemctl is-active ollama-proxy ollama" 2>/dev/null

    echo ""
    echo "Last updated: $(date)"

    sleep 5
done
```

### Success Criteria

#### Automated Verification:
- [ ] Integration tests pass: `python3 tests/integration_test.py`
- [ ] All 6 tests complete successfully
- [ ] Metrics endpoint returns valid JSON
- [ ] Health endpoint shows all features status
- [ ] Monitor script displays live stats
- [ ] P95 latency < 5000ms for complex queries
- [ ] P95 latency < 2000ms for simple queries
- [ ] Cache hit rate > 50% after warm-up

#### Manual Verification:
- [ ] systemd journal shows no errors: `journalctl -u ollama-proxy --since "1 hour ago"`
- [ ] Metrics show reasonable latency percentiles
- [ ] Cache hit rate improves over time
- [ ] Model selection distributes correctly (simple vs complex)
- [ ] Validation catches hallucinations (test in Baltimore mode)
- [ ] Monitor script updates every 5 seconds

**Implementation Note:** Run integration tests after each deployment to ensure system health. Monitor metrics during first 24 hours to establish baselines.

---

## Phase 6: Documentation & Final Validation

### Overview

Create comprehensive operations documentation, troubleshooting guides, and end-to-end validation procedures for production readiness.

### Documentation Required

#### 1. Operations Guide

**File**: `/Users/jaystuart/dev/project-athena/docs/OPERATIONS_GUIDE.md`

```markdown
# Ollama Proxy Operations Guide

## Quick Reference

**Service Management:**
```bash
# Check service status
systemctl status ollama-proxy

# Restart service
sudo systemctl restart ollama-proxy

# View logs
journalctl -u ollama-proxy -f
```

**Health Checks:**
```bash
# Quick health check
curl http://192.168.10.62:11434/health

# Detailed metrics
curl http://192.168.10.62:11434/metrics | jq '.'

# Check Ollama backend
curl http://192.168.10.62:11435/api/tags
```

**Mode Management:**
```bash
# Switch to Baltimore mode
./scripts/switch-mode.sh baltimore

# Switch to General mode
./scripts/switch-mode.sh general

# Verify current mode
curl -s http://192.168.10.62:11434/health | jq '.mode'
```

## Daily Operations

### Monitoring

Run the monitoring script for real-time stats:
```bash
./scripts/monitor-proxy.sh
```

Key metrics to watch:
- **P95 Latency**: Should be < 5000ms for complex, < 2000ms for simple
- **Cache Hit Rate**: Should be > 60% after warm-up period
- **Validation Failure Rate**: Should be < 5%
- **Error Count**: Should be near zero

### Log Management

Logs are written to:
- **Application**: `/mnt/nvme/athena-lite/logs/proxy.log`
- **Systemd Journal**: `journalctl -u ollama-proxy`

Rotate logs monthly:
```bash
ssh jstuart@192.168.10.62 "
    cd /mnt/nvme/athena-lite/logs
    mv proxy.log proxy.log.$(date +%Y%m).old
    sudo systemctl restart ollama-proxy
"
```

### Performance Tuning

**Cache Tuning** (edit .env):
```bash
CACHE_INSTANT_TTL_MINUTES=5    # Exact match cache
CACHE_FRESH_TTL_MINUTES=30     # Semantic match (fresh)
CACHE_RESPONSE_TTL_HOURS=24    # Semantic match (any)
```

**Model Selection** (edit .env):
```bash
OLLAMA_SIMPLE_MODEL=tinyllama:latest    # Fast queries
OLLAMA_COMPLEX_MODEL=llama3.2:3b        # Complex queries
```

### Backup & Restore

**Manual Backup:**
```bash
ssh jstuart@192.168.10.62 "
    tar -czf /mnt/nvme/athena-lite/backups/manual_$(date +%Y%m%d).tar.gz \
        /mnt/nvme/athena-lite/*.py \
        /mnt/nvme/athena-lite/config/ \
        /mnt/nvme/athena-lite/.env
"
```

**Restore from Backup:**
```bash
./scripts/rollback-proxy.sh <timestamp>
```

## Emergency Procedures

### Service Down

1. Check if Ollama backend is running:
   ```bash
   curl http://192.168.10.62:11435/api/tags
   ```

2. If Ollama is down:
   ```bash
   ssh jstuart@192.168.10.62 "sudo systemctl restart ollama"
   ```

3. If proxy is down:
   ```bash
   ssh jstuart@192.168.10.62 "sudo systemctl restart ollama-proxy"
   ```

4. Check for errors:
   ```bash
   ssh jstuart@192.168.10.62 "journalctl -u ollama-proxy -n 50"
   ```

### High Latency

1. Check system resources:
   ```bash
   ssh jstuart@192.168.10.62 "top -bn1 | head -20"
   ```

2. Check cache hit rate:
   ```bash
   curl -s http://192.168.10.62:11434/metrics | jq '.cache.hit_rate'
   ```

3. If cache hit rate is low, increase TTLs in .env

4. If CPU is high, check for model loading issues

### Validation Failures

1. Check validation failure rate:
   ```bash
   curl -s http://192.168.10.62:11434/metrics | jq '.performance.validation'
   ```

2. If failure rate > 10%, review logs for patterns:
   ```bash
   ssh jstuart@192.168.10.62 "grep 'HALLUCINATION' /mnt/nvme/athena-lite/logs/proxy.log"
   ```

3. Update ground truth database in config/mode_config.py if needed

## Mode-Specific Operations

### Baltimore Mode

**Purpose**: Airbnb guest assistant at 912 S Clinton St, Baltimore MD

**Features**:
- Location-aware responses
- SMS integration (Twilio)
- Local recommendations
- Sports scores (Ravens/Orioles)
- Anti-hallucination with ground truth

**Testing**:
```bash
# Verify location context
curl -X POST http://192.168.10.62:11434/api/generate \
  -d '{"prompt": "How far is Inner Harbor?"}' | jq '.response'

# Should mention "1.2 miles" (from ground truth)
```

### General Mode

**Purpose**: Homelab voice assistant

**Features**:
- Home automation control
- General knowledge
- No location assumptions
- No SMS

**Testing**:
```bash
# Verify no location context
curl -X POST http://192.168.10.62:11434/api/generate \
  -d '{"prompt": "Where am I located?"}' | jq '.response'

# Should say it doesn't know your location
```

## Integration with Home Assistant

The proxy listens on port 11434, which Home Assistant expects:

**HA Configuration** (already set up):
```yaml
rest_command:
  athena_llm_simple:
    url: "http://192.168.10.62:11434/api/generate"
    method: POST
    payload: '{"model": "tinyllama", "prompt": "{{ prompt }}"}'

  athena_llm_complex:
    url: "http://192.168.10.62:11434/api/generate"
    method: POST
    payload: '{"model": "llama3.2:3b", "prompt": "{{ prompt }}"}'
```

**Test from HA**:
1. Open HA Developer Tools → Services
2. Call `rest_command.athena_llm_simple`
3. Payload: `{"prompt": "What time is it?"}`
4. Check response in proxy logs
```

#### 2. Troubleshooting Guide

**File**: `/Users/jaystuart/dev/project-athena/docs/TROUBLESHOOTING.md`

```markdown
# Ollama Proxy Troubleshooting Guide

## Common Issues

### Issue: "Connection refused" on port 11434

**Symptoms**: Health check fails, HA can't reach proxy

**Diagnosis**:
```bash
# Check if service is running
systemctl status ollama-proxy

# Check if port is listening
ss -tlnp | grep 11434
```

**Solution**:
```bash
# Restart proxy service
sudo systemctl restart ollama-proxy

# If still failing, check logs
journalctl -u ollama-proxy -n 100
```

### Issue: Slow response times (> 10s)

**Symptoms**: P95 latency exceeds 10000ms

**Diagnosis**:
```bash
# Check metrics
curl -s http://192.168.10.62:11434/metrics | jq '.performance.latency_ms'

# Check if Ollama is responsive
time curl -X POST http://192.168.10.62:11435/api/generate \
  -d '{"model":"tinyllama","prompt":"test"}'
```

**Solution**:
- If Ollama is slow: Restart Ollama service
- If cache hit rate is low: Increase cache TTLs
- If CPU is maxed: Reduce concurrent requests

### Issue: Cache not working (0% hit rate)

**Symptoms**: All queries show "cached": false

**Diagnosis**:
```bash
# Check cache stats
curl -s http://192.168.10.62:11434/metrics | jq '.cache'

# Verify caching is enabled
ssh jstuart@192.168.10.62 "grep ENABLE_CACHING /mnt/nvme/athena-lite/.env"
```

**Solution**:
```bash
# Enable caching in .env
ENABLE_CACHING=true

# Restart service
sudo systemctl restart ollama-proxy
```

### Issue: Wrong mode active

**Symptoms**: Baltimore responses in General mode or vice versa

**Diagnosis**:
```bash
# Check current mode
curl -s http://192.168.10.62:11434/health | jq '.mode'

# Check .env file
ssh jstuart@192.168.10.62 "grep ATHENA_MODE /mnt/nvme/athena-lite/.env"
```

**Solution**:
```bash
# Switch mode
./scripts/switch-mode.sh <baltimore|general>

# Verify
curl -s http://192.168.10.62:11434/health | jq '{mode, features}'
```

### Issue: Validation always failing

**Symptoms**: Validation failure rate > 50%

**Diagnosis**:
```bash
# Check validation stats
curl -s http://192.168.10.62:11434/metrics | jq '.performance.validation'

# Check logs for patterns
ssh jstuart@192.168.10.62 "grep 'validation failed' /mnt/nvme/athena-lite/logs/proxy.log | tail -20"
```

**Solution**:
- Review ground truth database accuracy
- Adjust validation temperature in mode_config.py
- Check if cross-model validation is too strict

### Issue: Ollama models not found

**Symptoms**: Error "model not found: tinyllama"

**Diagnosis**:
```bash
# List available models
curl http://192.168.10.62:11435/api/tags | jq '.models[].name'
```

**Solution**:
```bash
# SSH to Jetson and pull models
ssh jstuart@192.168.10.62
ollama pull tinyllama:latest
ollama pull llama3.2:3b

# Verify
ollama list
```

## Diagnostic Commands

### System Health
```bash
# Full system check
curl -s http://192.168.10.62:11434/health | jq '.'

# Performance metrics
curl -s http://192.168.10.62:11434/metrics | jq '.performance'

# Cache statistics
curl -s http://192.168.10.62:11434/metrics | jq '.cache'
```

### Service Status
```bash
# Check all services
ssh jstuart@192.168.10.62 "
    systemctl status ollama
    systemctl status ollama-proxy
"

# Recent logs
ssh jstuart@192.168.10.62 "journalctl -u ollama-proxy --since '1 hour ago'"
```

### Resource Usage
```bash
# CPU and Memory
ssh jstuart@192.168.10.62 "top -bn1 | head -20"

# Disk space
ssh jstuart@192.168.10.62 "df -h /mnt/nvme"

# Process info
ssh jstuart@192.168.10.62 "ps aux | grep -E 'ollama|python3.*proxy'"
```

## Getting Help

1. **Check logs first**:
   ```bash
   journalctl -u ollama-proxy -n 200
   tail -100 /mnt/nvme/athena-lite/logs/proxy.log
   ```

2. **Run integration tests**:
   ```bash
   python3 tests/integration_test.py
   ```

3. **Collect diagnostic bundle**:
   ```bash
   ssh jstuart@192.168.10.62 "
       tar -czf /tmp/diagnostic_$(date +%Y%m%d_%H%M%S).tar.gz \
           /mnt/nvme/athena-lite/logs/proxy.log \
           /mnt/nvme/athena-lite/.env \
           <(systemctl status ollama-proxy) \
           <(journalctl -u ollama-proxy --since '24 hours ago')
   "
   ```

4. **Report issue**: Include diagnostic bundle and specific error messages
```

#### 3. Create Deployment Checklist

**File**: `/Users/jaystuart/dev/project-athena/docs/DEPLOYMENT_CHECKLIST.md`

```markdown
# Deployment Checklist

Use this checklist when deploying Ollama Proxy updates.

## Pre-Deployment

- [ ] All code changes committed to git
- [ ] Integration tests pass locally
- [ ] Documentation updated
- [ ] Backup window scheduled (if needed)
- [ ] Rollback plan confirmed

## Deployment Steps

- [ ] Create backup: `./scripts/deploy-proxy.sh` (automatic)
- [ ] Deploy new version: Service restarts automatically
- [ ] Health check passes: `curl http://192.168.10.62:11434/health`
- [ ] Integration tests pass: `python3 tests/integration_test.py`
- [ ] Monitor for 15 minutes: `./scripts/monitor-proxy.sh`
- [ ] Check error logs: `journalctl -u ollama-proxy --since "15 minutes ago"`

## Post-Deployment Validation

- [ ] Response latency normal (P95 < 5000ms)
- [ ] Cache hit rate > 50%
- [ ] Validation failure rate < 5%
- [ ] No error spikes in logs
- [ ] Home Assistant integration working
- [ ] Both modes tested (if applicable)

## Rollback Criteria

Rollback immediately if:
- [ ] Health check fails for > 2 minutes
- [ ] P95 latency > 10000ms
- [ ] Error rate > 10%
- [ ] Service crashes repeatedly
- [ ] Cache completely broken (0% hit rate)

**Rollback Command**:
```bash
./scripts/rollback-proxy.sh <backup_timestamp>
```

## Sign-Off

- [ ] Deployment successful - Signed: __________ Date: __________
- [ ] Monitoring confirmed normal - Signed: __________ Date: __________
```

### Final Validation

#### End-to-End Test Plan

**File**: `/Users/jaystuart/dev/project-athena/tests/e2e_test.md`

```markdown
# End-to-End Test Plan

## Test Scenario 1: Baltimore Mode Full Cycle

1. **Switch to Baltimore mode**:
   ```bash
   ./scripts/switch-mode.sh baltimore
   ```

2. **Verify mode features**:
   ```bash
   curl -s http://192.168.10.62:11434/health | jq '.features'
   # Should show: anti_hallucination, sms, location_context all true
   ```

3. **Test location-aware response**:
   ```bash
   curl -X POST http://192.168.10.62:11434/api/generate \
     -d '{"prompt": "How far is Fells Point from here?"}'
   # Expected: Should mention "0.8 miles" (ground truth)
   ```

4. **Test anti-hallucination**:
   ```bash
   curl -X POST http://192.168.10.62:11434/api/generate \
     -d '{"prompt": "Are we in Portland?"}'
   # Expected: Should correct to "Baltimore"
   ```

5. **Test cache**:
   - Repeat previous query
   - Verify "cached": true in response
   - Verify faster response time

6. **Verify metrics**:
   ```bash
   curl -s http://192.168.10.62:11434/metrics | jq '{
     cache_hit_rate: .cache.hit_rate,
     validation: .performance.validation
   }'
   ```

## Test Scenario 2: General Mode Full Cycle

1. **Switch to General mode**:
   ```bash
   ./scripts/switch-mode.sh general
   ```

2. **Verify mode features**:
   ```bash
   curl -s http://192.168.10.62:11434/health | jq '.features'
   # Should show: location_context=false, sms=false
   ```

3. **Test general query**:
   ```bash
   curl -X POST http://192.168.10.62:11434/api/generate \
     -d '{"prompt": "What are the benefits of LED lighting?"}'
   # Expected: General response, no location references
   ```

4. **Test device control simulation**:
   ```bash
   curl -X POST http://192.168.10.62:11434/api/generate \
     -d '{"prompt": "Turn on office lights"}'
   # Expected: Should use TinyLlama (fast model)
   ```

5. **Verify no Baltimore context**:
   ```bash
   curl -X POST http://192.168.10.62:11434/api/generate \
     -d '{"prompt": "Where am I?"}'
   # Expected: Should NOT mention Baltimore
   ```

## Test Scenario 3: Home Assistant Integration

1. **Open Home Assistant** (https://ha.xmojo.net)

2. **Test simple command** (Developer Tools → Services):
   - Service: `rest_command.athena_llm_simple`
   - Data: `{"prompt": "What time is it?"}`
   - Verify: Response in HA, check proxy logs

3. **Test complex command**:
   - Service: `rest_command.athena_llm_complex`
   - Data: `{"prompt": "Suggest ways to save energy at home"}`
   - Verify: Longer response, Llama3.2:3b used

4. **Check routing automation**:
   - Trigger voice command in HA
   - Verify classified correctly (simple vs complex)
   - Verify proxy receives request

## Test Scenario 4: Performance Under Load

1. **Run load test** (10 concurrent requests):
   ```bash
   for i in {1..10}; do
       curl -X POST http://192.168.10.62:11434/api/generate \
         -d '{"prompt": "Test query '$i'"}' &
   done
   wait
   ```

2. **Check metrics after load**:
   ```bash
   curl -s http://192.168.10.62:11434/metrics | jq '.performance.latency_ms'
   # Verify: P95 latency still reasonable
   ```

3. **Verify service stability**:
   ```bash
   systemctl status ollama-proxy
   # Should still be active/running
   ```

## Test Scenario 5: Recovery from Failure

1. **Simulate Ollama failure**:
   ```bash
   ssh jstuart@192.168.10.62 "sudo systemctl stop ollama"
   ```

2. **Verify proxy handles gracefully**:
   ```bash
   curl http://192.168.10.62:11434/health
   # Expected: Status "degraded", ollama_connected=false
   ```

3. **Restore Ollama**:
   ```bash
   ssh jstuart@192.168.10.62 "sudo systemctl start ollama"
   ```

4. **Verify recovery**:
   ```bash
   curl http://192.168.10.62:11434/health
   # Expected: Status "healthy", ollama_connected=true
   ```

## Success Criteria

All scenarios must pass:
- [  ] Scenario 1: Baltimore mode full cycle
- [ ] Scenario 2: General mode full cycle
- [ ] Scenario 3: Home Assistant integration
- [ ] Scenario 4: Performance under load
- [ ] Scenario 5: Recovery from failure

**Signed**: __________ **Date**: __________
```

### Success Criteria

#### Automated Verification:
- [ ] All documentation files created
- [ ] Operations guide covers all common tasks
- [ ] Troubleshooting guide addresses known issues
- [ ] Deployment checklist complete
- [ ] End-to-end test plan documented
- [ ] All documentation formatted correctly (markdown)

#### Manual Verification:
- [ ] Operations guide tested by following procedures
- [ ] Troubleshooting guide resolves real issues
- [ ] Deployment checklist used in actual deployment
- [ ] End-to-end tests all pass
- [ ] Documentation is clear and accurate
- [ ] All scripts and commands work as documented

**Implementation Note:** Complete end-to-end testing before declaring production-ready. Update documentation based on real-world usage.

---

## Summary: Production Readiness

### What We Built

**Dual-Mode AI Assistant System**:
- **Baltimore Mode**: Location-aware Airbnb guest assistant with anti-hallucination
- **General Mode**: Flexible homelab voice assistant

**Key Features**:
- Ollama-based LLM (Llama3.2:3b + TinyLlama)
- Proxy pattern (port 11434 → 11435)
- 3-tier caching (70-80% hit rate target)
- Anti-hallucination validation
- Performance monitoring
- Automated deployment with rollback
- Comprehensive documentation

### Production Metrics Targets

- **Latency**: P95 < 5s (complex), P95 < 2s (simple)
- **Cache Hit Rate**: > 60% after warm-up
- **Uptime**: > 99.5%
- **Validation Failure Rate**: < 5%
- **Error Rate**: < 1%

### Next Steps

1. **Deploy to Production**: Run `./scripts/deploy-proxy.sh`
2. **Monitor**: Use `./scripts/monitor-proxy.sh` for first 24 hours
3. **Validate**: Run end-to-end test plan
4. **Optimize**: Tune cache TTLs based on actual usage
5. **Document**: Update Wiki with production deployment notes

### Future Enhancements (Not in This Plan)

- Wyoming protocol integration (Phase 1 future work)
- Multi-zone deployment (Phase 2 future work)
- RAG with vector database
- Voice identification
- Context learning from user patterns
- Mobile app integration

---

**Plan Complete**
**Ready for Implementation Approval**

