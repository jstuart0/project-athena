# Guest Mode, Permission Scoping, and Quality Tracking - Implementation Plan
**Date:** 2025-11-11
**Status:** Planning - Part of Architecture Pivot
**Related:**
- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md)
- [Admin Interface Specification](2025-11-11-admin-interface-specification.md) - UI for mode control, feedback, config management

## Executive Summary

This plan extends the new Project Athena architecture with:
1. **Automatic Guest Mode detection** via Airbnb calendar integration
2. **Permission scoping** (guest vs owner mode) with configurable allowlists/denylists
3. **Quality tracking and feedback loops** for continuous improvement
4. **Privacy-first design** with automatic data purging on checkout

## A) Goals

### 1. Guest Mode Features

**Auto-detected:**
- Integrate with Airbnb calendar (iCal feed) or PMS webhooks (Hostaway/Guesty)
- Automatically activate during booked stays (with configurable buffer time)
- Seamless activation/deactivation without manual intervention

**Manually overrideable:**
- Owner voice PIN ("Jarvis, switch to owner mode. PIN 1234")
- Home Assistant UI toggle
- Mobile app quick action (optional)
- Override takes precedence over calendar state

**Configurable:**
- Per-mode allowlists/denylists for HA entities, domains, scenes
- Info category restrictions (what guests can ask about)
- Brightness/volume caps
- Quiet hours enforcement
- SMS/email sharing controls
- Data retention policies

**Low-risk:**
- Privacy-first defaults (no owner data exposure)
- Automatic PII scrubbing in guest mode
- Data purge on checkout
- No access to security systems, locks, owner-only spaces

### 2. Owner Mode Features

**Full functionality:**
- No feature restrictions
- Access to all HA entities/domains/scenes
- All info categories available
- Extended data retention
- Optional PII preservation
- Relaxed anti-hallucination guardrails

### 3. Observability & Quality Tracking

**Track requests/responses:**
- Full envelope metadata (timestamp, mode, room, device, latency)
- Routing decisions (models used, tools called, sources retrieved)
- Success/failure rates
- Guardrail triggers and denials

**Feedback workflow:**
- Voice: "Jarvis, that answer was wrong"
- HA UI: Thumbs down + reason
- Admin page: Review recent answers, bulk retest
- Automatic bad answer clustering

**Metrics & dashboards:**
- Per-mode success rates
- Latency breakdowns by stage
- Denial counts by reason
- Cross-model validation usage
- Category hit rates
- Feedback trends

**Improvement loop:**
- Nightly analysis of failed queries
- Identify patterns (missing sources, low confidence, rate limits)
- Suggest fixes (add domains, tune prompts, adjust thresholds)
- A/B validation against test suite

---

## B) Mode Determination Logic

### Priority Order (First Match Wins)

```python
def determine_mode(now: datetime, request_context: dict) -> str:
    """
    Determine if system should be in guest or owner mode.

    Priority:
    1. Manual override (highest priority)
    2. Active Airbnb booking (calendar/PMS)
    3. Default mode (guest for safety)
    """

    # 1. Check manual override
    if force_guest_override := get_override_state():
        return "guest" if force_guest_override.value else "owner"

    # 2. Check active booking
    active_stay = get_active_stay(now)
    if active_stay:
        # Apply buffer: checkin - 2h to checkout + 1h
        checkin_with_buffer = active_stay.checkin - timedelta(hours=2)
        checkout_with_buffer = active_stay.checkout + timedelta(hours=1)

        if checkin_with_buffer <= now <= checkout_with_buffer:
            return "guest"

    # 3. Default mode (configurable, guest for safety)
    return config.get("default_mode", "guest")
```

### Booking Detection Sources

**Option A: iCal Import (Simple & Reliable)**
- Airbnb provides iCal URL for each listing
- Poll every 10 minutes
- Cache events in vector DB or PostgreSQL
- Normalize to: `{stay_id, start, end, guest_name?, notes?}`
- **Recommended for MVP**

**Option B: PMS Webhook (Advanced)**
- Integration with Hostaway, Guesty, or similar PMS
- Receive real-time create/cancel/modify events
- Instant mode switching (no polling delay)
- **Future enhancement**

**Fallback: Manual Toggle**
- HA helper: `input_boolean.guest_mode_override`
- Web UI button
- Always available as backup

### Configuration Buffer Times

```yaml
mode_detection:
  airbnb_calendar_url: "https://airbnb.com/calendar/ical/..."
  poll_interval_minutes: 10

  buffer:
    before_checkin_hours: 2    # Activate guest mode 2h before checkin
    after_checkout_hours: 1    # Keep guest mode 1h after checkout

  override:
    pin: "1234"                # Voice PIN for owner mode
    timeout_minutes: 60        # Auto-revert to auto mode after 60min
    persist_until_toggle: false # Or stay in owner mode until manually disabled
```

---

## C) Configuration Surface

### Security Modes Configuration

**File:** `config/security_modes.yaml`

```yaml
modes:
  guest:
    enabled: true

    # Home Assistant Control Scope
    scope:
      # Scenes guests can activate
      allow_scenes:
        - "Movie Night (Living Room)"
        - "Relax (Bedroom)"
        - "Good Morning"
        - "Good Night"

      # HA domains allowed (light, switch, media_player, etc.)
      allow_domains:
        - "light"
        - "media_player"
        - "switch"
        - "scene"
        - "script"

      # Specific entities to deny (owner spaces, security)
      deny_entities:
        - "lock.*"                        # All locks
        - "garage.*"                      # Garage controls
        - "alarm_control_panel.*"         # Security system
        - "climate.master_bedroom"        # Owner bedroom climate
        - "cover.master_bedroom_*"        # Owner bedroom blinds
        - "camera.*"                      # All cameras
        - "binary_sensor.*.motion"        # Motion sensors (privacy)
        - "device_tracker.*"              # Location tracking

      # Caps and limits
      max_brightness: 85                  # Max light brightness (percent)
      max_volume: 60                      # Max media volume (percent)

      # Quiet hours (no media, whisper TTS)
      quiet_hours:
        enabled: true
        start: "22:00"                    # 10 PM
        end: "07:00"                      # 7 AM
        deny_domains:
          - "media_player"                # No music/TV during quiet hours
        tts_voice: "piper_whisper_quiet"  # Quieter TTS voice

    # Information Categories (RAG)
    info_categories:
      allow:
        - "weather"
        - "news"
        - "events"
        - "transport"
        - "airports"
        - "flights"
        - "sports"
        - "recipes"
        - "streaming"
        - "dining"
        - "property_info"               # Baltimore property details
        - "neighborhood"                # Local area info
      deny:
        - "owner_calendar"              # Owner's personal calendar
        - "owner_contacts"              # Owner's contacts
        - "security_logs"               # Security system logs
        - "camera_feeds"                # Camera access
        - "personal_preferences"        # Owner preferences/history

    # Sharing Capabilities
    sharing:
      sms_enabled: true
      email_enabled: true
      phone_whitelist: []               # Empty = allow any (guest-provided)
      max_sms_per_day: 10               # Rate limit
      max_email_per_day: 5
      redact_personal_data: true        # Scrub PII before sharing
      allowed_content_types:
        - "directions"
        - "recommendations"
        - "recipes"
        - "event_info"
        - "transit_info"

    # Data Retention & Privacy
    retention:
      request_logs_days: 14             # Keep logs for 14 days
      response_logs_days: 14
      pii_scrub: true                   # Always scrub PII in guest mode
      purge_on_checkout: true           # Auto-purge after checkout + buffer
      purge_delay_hours: 1              # Wait 1h after checkout
      keep_anonymized_metrics: true     # Keep aggregate stats

    # Validation & Guardrails
    validation:
      anti_hallucination: "strict"      # Strictest guardrails
      cross_model_validation: "auto_high_stakes"  # Auto-enable for critical queries
      retrieval_confidence_threshold: 0.75        # High confidence required
      web_search_scope:
        - "trusted_news"                # Only trusted news sources
        - "official_airports"           # Official airport sites
        - "city_sites"                  # Baltimore city sites
        - "event_apis"                  # Ticketmaster, Meetup, etc.
      blocked_domains:
        - "owner_email_domain.com"      # Block owner's email domain
        - "private_docs.*"              # Block private doc sites

  owner:
    enabled: true

    scope:
      allow_domains: ["*"]              # All domains
      deny_entities: []                 # Nothing denied
      max_brightness: null              # No limits
      max_volume: null
      quiet_hours:
        enabled: false                  # No quiet hours for owner

    info_categories:
      allow: ["*"]                      # All categories
      deny: []

    sharing:
      sms_enabled: true
      email_enabled: true
      phone_whitelist: []               # No restrictions
      max_sms_per_day: null             # Unlimited
      max_email_per_day: null
      redact_personal_data: false       # Keep full data

    retention:
      request_logs_days: 90             # Longer retention
      response_logs_days: 90
      pii_scrub: false                  # Optional, preserve PII
      purge_on_checkout: false          # Never auto-purge
      keep_anonymized_metrics: true

    validation:
      anti_hallucination: "balanced"    # Less strict
      cross_model_validation: "manual"  # Only when explicitly requested
      retrieval_confidence_threshold: 0.60
      web_search_scope: ["*"]           # No restrictions
      blocked_domains: []
```

### Property-Specific Configuration

**File:** `config/property_baltimore.yaml`

```yaml
property:
  address: "912 South Clinton St, Baltimore, MD 21224"
  latitude: 39.2809
  longitude: -76.5936
  timezone: "America/New_York"

  airbnb:
    listing_id: "your-listing-id"
    calendar_ics_url: "https://airbnb.com/calendar/ical/..."
    pms_integration: null              # Or "hostaway", "guesty", etc.

  zones:
    guest_accessible:
      - "kitchen"
      - "living_room"
      - "dining_room"
      - "guest_bedroom_alpha"
      - "guest_bedroom_beta"
      - "main_bath"
      - "basement_bath"

    guest_audio_only:                  # Can hear TTS, but no occupancy tracking
      - "dining_room"

    owner_private:                     # Never activate in guest mode
      - "master_bedroom"
      - "master_bath"
      - "office"

  nearby:
    airports:
      - code: "BWI"
        name: "Baltimore/Washington International"
        distance_miles: 9
      - code: "PHL"
        name: "Philadelphia International"
        distance_miles: 95
      - code: "IAD"
        name: "Washington Dulles International"
        distance_miles: 55
      - code: "DCA"
        name: "Ronald Reagan Washington National"
        distance_miles: 45

    neighborhoods:
      - "Fells Point"
      - "Canton"
      - "Harbor East"
      - "Inner Harbor"

    attractions:
      - "National Aquarium"
      - "Fort McHenry"
      - "Baltimore Museum of Art"
      - "Oriole Park at Camden Yards"
      - "M&T Bank Stadium"
```

---

## D) Architecture Flow with Mode Awareness

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    HA Voice Preview Devices                     │
│              (Wyoming satellites with wake words)               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              Home Assistant @ 192.168.10.168                    │
│  Assist Pipelines: Control (HA native) | Knowledge (OpenAI)    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         Gateway @ 192.168.10.167:8000 (Mac Studio)               │
│  1. Receive request with room, device_id                        │
│  2. Call Mode Service → get current mode                        │
│  3. Add mode metadata to request                                │
│  4. Forward to Orchestrator                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         Mode Service (NEW) @ 192.168.10.167:8001                 │
│  GET /mode/current → {mode: "guest"|"owner", reason, stay_id}  │
│  POST /mode/override → set manual override                      │
│                                                                 │
│  Sources:                                                       │
│  1. Check manual override (HA helper + API state)              │
│  2. Check Airbnb calendar cache (PostgreSQL)                   │
│  3. Return default mode (guest)                                │
│                                                                 │
│  Background job:                                                │
│  - Poll Airbnb iCal every 10 minutes                           │
│  - Update booking cache                                        │
│  - Emit mode change events                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         LangGraph Orchestrator (Mac Studio)                     │
│                                                                 │
│  NEW: Preflight Node (before classify)                         │
│    1. Load mode policy from security_modes.yaml                │
│    2. Compute effective permissions                            │
│    3. Annotate graph context with policy                       │
│    4. Early rejection if request violates policy               │
│                                                                 │
│  classify → route → retrieve → synthesize → validate → share   │
│    ↓          ↓         ↓          ↓           ↓         ↓     │
│   All nodes are mode-aware and enforce policy                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         Feedback Service (NEW) @ 192.168.10.167:8002             │
│  POST /feedback → record good/bad answer                        │
│  GET /feedback/review → admin review queue                      │
│                                                                 │
│  Storage: PostgreSQL table answer_feedback                     │
│  Background: Nightly analysis job                              │
└─────────────────────────────────────────────────────────────────┘
```

### Request Flow with Mode Enforcement

```
1. Guest says: "Jarvis, unlock the front door"

2. HA Voice Device → STT → "unlock the front door"

3. HA Assist Pipeline (Control) → Gateway

4. Gateway → Mode Service
   → Returns: {mode: "guest", reason: "active_booking", stay_id: "abc123"}

5. Gateway → Orchestrator with mode metadata

6. Orchestrator Preflight Node:
   - Loads guest policy
   - Checks: "unlock" → domain "lock" → DENIED in guest mode
   - Returns friendly refusal:
     "For guest privacy and safety, I can't control locks.
      I can help with lights, scenes, music, and more.
      Try saying 'turn on the living room lights' or 'play relaxing music.'"

7. Response → TTS → Guest hears friendly denial

---

1. Guest says: "Athena, what's the weather tomorrow?"

2. HA Voice Device → STT → "what's the weather tomorrow"

3. HA Assist Pipeline (Knowledge) → Gateway → Orchestrator

4. Mode Service: {mode: "guest", ...}

5. Orchestrator:
   - Preflight: "weather" category → ALLOWED for guests ✓
   - classify: "info" query
   - route: small model (simple query)
   - retrieve: weather API (Baltimore) with TTL cache
   - synthesize: "Tomorrow in Baltimore: 68°F, partly cloudy..."
   - validate: STRICT mode, retrieval confidence 0.85 (PASS)
   - share: N/A (no "text me" requested)

6. Response → TTS → Guest hears weather forecast

---

1. Guest says: "Athena, text me directions to the National Aquarium"

2. HA Knowledge Pipeline → Gateway → Orchestrator

3. Mode Service: {mode: "guest", ...}

4. Orchestrator:
   - Preflight: "directions" + "sms" → ALLOWED for guests ✓
   - classify: "info" + "share" query
   - route: medium model
   - retrieve: Google Maps directions, property context
   - synthesize: "The National Aquarium is 2.1 miles away..."
   - validate: STRICT, retrieval confidence 0.92 (PASS)
   - share: Enqueue SMS with directions + map link

5. Response + SMS sent

6. Log: Redact guest phone number in stored logs (PII scrub)
```

### Metadata Flow

**Gateway adds to every request:**
```json
{
  "text": "what's the weather tomorrow",
  "metadata": {
    "mode": "guest",
    "mode_reason": "active_booking",
    "stay_id": "abc123",
    "room": "kitchen",
    "device_id": "jarvis-kitchen-50",
    "timestamp": "2025-11-15T10:30:00Z",
    "request_id": "req_xyz789"
  }
}
```

**Orchestrator annotates graph context:**
```python
context = {
    "mode": "guest",
    "policy": {
        "allow_domains": ["light", "media_player", "switch", "scene"],
        "deny_entities": ["lock.*", "alarm_control_panel.*", ...],
        "max_brightness": 85,
        "quiet_hours_active": False,
        "info_categories_allow": ["weather", "news", ...],
        "anti_hallucination": "strict",
        "cross_model_auto": True,
        "sharing_enabled": True,
        "pii_scrub": True
    },
    "property": {
        "address": "912 South Clinton St, Baltimore, MD 21224",
        "lat": 39.2809,
        "lon": -76.5936,
        "timezone": "America/New_York"
    }
}
```

---

## E) Airbnb / Booking Integration

### Calendar Connector (iCal Polling - MVP)

**Component:** `apps/calendar_connector/`

**Responsibilities:**
- Poll Airbnb iCal URL every 10 minutes
- Parse iCalendar format (RFC 5545)
- Normalize events to booking records
- Store in PostgreSQL `bookings` table
- Emit mode change events when stay starts/ends

**Schema:**

```sql
CREATE TABLE bookings (
    stay_id VARCHAR(64) PRIMARY KEY,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    guest_name VARCHAR(255),
    guest_count INTEGER,
    booking_source VARCHAR(64) DEFAULT 'airbnb_ical',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cancelled BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_bookings_time_range ON bookings(start_time, end_time);
```

**Configuration:**

```yaml
# config/calendar_connector.yaml
calendar:
  airbnb:
    ical_url: "${AIRBNB_CALENDAR_URL}"  # From environment
    poll_interval_seconds: 600          # 10 minutes
    user_agent: "Project-Athena/1.0"

  normalization:
    extract_guest_name: true            # Try to parse from event summary
    default_guest_count: 2

  storage:
    database_url: "${POSTGRES_URL}"
    table: "bookings"
```

**Polling Logic:**

```python
import asyncio
import icalendar
import requests
from datetime import datetime, timezone

class CalendarConnector:
    def __init__(self, config):
        self.ical_url = config['calendar']['airbnb']['ical_url']
        self.poll_interval = config['calendar']['airbnb']['poll_interval_seconds']
        self.db = Database(config['storage']['database_url'])

    async def poll_loop(self):
        while True:
            try:
                await self.fetch_and_sync()
            except Exception as e:
                logger.error(f"Calendar poll failed: {e}")

            await asyncio.sleep(self.poll_interval)

    async def fetch_and_sync(self):
        # Fetch iCal
        response = requests.get(self.ical_url, timeout=30)
        response.raise_for_status()

        # Parse
        cal = icalendar.Calendar.from_ical(response.content)

        bookings = []
        for event in cal.walk('VEVENT'):
            stay_id = str(event.get('UID'))
            start = event.get('DTSTART').dt
            end = event.get('DTEND').dt
            summary = str(event.get('SUMMARY', ''))

            # Normalize to timezone-aware datetime
            if not hasattr(start, 'tzinfo'):
                start = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
            if not hasattr(end, 'tzinfo'):
                end = datetime.combine(end, datetime.min.time()).replace(tzinfo=timezone.utc)

            bookings.append({
                'stay_id': stay_id,
                'start_time': start,
                'end_time': end,
                'guest_name': self.extract_guest_name(summary),
                'notes': summary
            })

        # Sync to database (upsert)
        await self.db.upsert_bookings(bookings)

        logger.info(f"Synced {len(bookings)} bookings")

    def extract_guest_name(self, summary: str) -> str:
        # Try to parse "Reserved for John Doe" or similar
        if "Reserved for" in summary:
            return summary.split("Reserved for")[1].strip()
        return None
```

### PMS Webhook Integration (Future)

**Component:** `apps/pms_webhook/`

**Supported Providers:**
- Hostaway (webhook API)
- Guesty (webhook API)
- Hospitable (webhook API)
- Others via generic webhook format

**Webhook Events:**
- `booking.created`
- `booking.updated`
- `booking.cancelled`
- `checkin.completed`
- `checkout.completed`

**Configuration:**

```yaml
# config/pms_webhook.yaml
pms:
  provider: "hostaway"  # or "guesty", "hospitable", "generic"

  hostaway:
    webhook_secret: "${HOSTAWAY_WEBHOOK_SECRET}"
    endpoint: "/webhooks/hostaway"
    verify_signature: true

  mapping:
    stay_id_field: "reservationId"
    start_field: "arrivalDate"
    end_field: "departureDate"
    guest_name_field: "guestName"
```

**Webhook Handler:**

```python
from fastapi import FastAPI, Request, HTTPException
import hmac

app = FastAPI()

@app.post("/webhooks/hostaway")
async def hostaway_webhook(request: Request):
    # Verify signature
    signature = request.headers.get('X-Hostaway-Signature')
    body = await request.body()

    if not verify_signature(signature, body, config.webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event
    event = await request.json()
    event_type = event['type']

    if event_type == 'booking.created':
        await handle_booking_created(event['data'])
    elif event_type == 'booking.updated':
        await handle_booking_updated(event['data'])
    elif event_type == 'booking.cancelled':
        await handle_booking_cancelled(event['data'])

    return {"status": "ok"}

async def handle_booking_created(data):
    booking = {
        'stay_id': data['reservationId'],
        'start_time': parse_datetime(data['arrivalDate']),
        'end_time': parse_datetime(data['departureDate']),
        'guest_name': data.get('guestName'),
        'guest_count': data.get('numberOfGuests', 2),
        'booking_source': 'hostaway_webhook'
    }

    await db.upsert_bookings([booking])
    await emit_mode_change_event()
```

### Manual Override

**Home Assistant Helper:**

```yaml
# configuration.yaml in Home Assistant
input_boolean:
  guest_mode_override:
    name: "Guest Mode Override"
    icon: mdi:account-lock
```

**Mode Service Integration:**

```python
async def check_ha_override() -> Optional[bool]:
    """
    Check HA input_boolean.guest_mode_override state.
    Returns: True (force guest), False (force owner), None (auto)
    """
    token = config.ha_token
    url = f"{config.ha_url}/api/states/input_boolean.guest_mode_override"

    response = await http_client.get(url, headers={"Authorization": f"Bearer {token}"})
    data = response.json()

    if data['state'] == 'on':
        return True  # Force guest mode
    elif data['attributes'].get('owner_override') == True:
        return False  # Force owner mode
    else:
        return None  # Auto mode
```

---

## F) Permission Enforcement Points

### 1. Preflight Policy Gate (Orchestrator)

**New LangGraph Node:** `preflight_check`

```python
from langgraph.graph import StateGraph
from typing import TypedDict, Annotated

class GraphState(TypedDict):
    text: str
    mode: str
    policy: dict
    room: str
    intent: Optional[str]
    response: Optional[str]
    citations: list
    validation: dict

def preflight_check(state: GraphState) -> GraphState:
    """
    Enforce mode-based policy before processing request.
    Early rejection for policy violations.
    """
    mode = state['mode']
    text = state['text'].lower()
    policy = load_policy(mode)  # From security_modes.yaml

    # Check for control requests
    if is_control_request(text):
        # Extract target entity/domain
        target = extract_control_target(text)

        # Check domain allowlist
        if target['domain'] not in policy['scope']['allow_domains']:
            return {
                **state,
                'response': format_denial(
                    reason='domain_not_allowed',
                    domain=target['domain'],
                    allowed_domains=policy['scope']['allow_domains']
                ),
                'intent': 'denied'
            }

        # Check entity denylist
        if matches_pattern(target['entity_id'], policy['scope']['deny_entities']):
            return {
                **state,
                'response': format_denial(
                    reason='entity_restricted',
                    entity=target['entity_id'],
                    mode=mode
                ),
                'intent': 'denied'
            }

        # Check quiet hours
        if policy['scope'].get('quiet_hours', {}).get('enabled'):
            now = datetime.now(timezone.utc)
            if is_quiet_hours(now, policy['scope']['quiet_hours']):
                if target['domain'] in policy['scope']['quiet_hours']['deny_domains']:
                    return {
                        **state,
                        'response': format_denial(
                            reason='quiet_hours',
                            start=policy['scope']['quiet_hours']['start'],
                            end=policy['scope']['quiet_hours']['end']
                        ),
                        'intent': 'denied'
                    }

    # Check for info requests
    if is_info_request(text):
        category = classify_info_category(text)

        if category not in policy['info_categories']['allow']:
            return {
                **state,
                'response': format_denial(
                    reason='category_not_allowed',
                    category=category,
                    allowed_categories=policy['info_categories']['allow']
                ),
                'intent': 'denied'
            }

    # Annotate state with policy for downstream nodes
    state['policy'] = policy
    return state

def format_denial(reason: str, **kwargs) -> str:
    """
    Generate friendly denial messages.
    """
    templates = {
        'domain_not_allowed': (
            "For guest privacy and safety, I can't control {domain} devices. "
            "I can help with {allowed_domains}. "
            "Try asking about lights, music, or entertainment."
        ),
        'entity_restricted': (
            "That device isn't available in guest mode for privacy and security. "
            "I can help with lights, scenes, music, and more."
        ),
        'quiet_hours': (
            "It's quiet hours ({start} to {end}). "
            "I'm keeping things quiet for other guests. "
            "I can still help with lights at low levels."
        ),
        'category_not_allowed': (
            "I don't have access to {category} information in guest mode. "
            "I can help with {allowed_categories}."
        )
    }

    template = templates.get(reason, "I can't help with that in guest mode.")
    return template.format(**kwargs)
```

### 2. HA Function Calling Schema (Optional HA Bridge)

**If using HA Bridge for advanced multi-step automations:**

```python
def get_ha_functions(mode: str, policy: dict) -> list:
    """
    Return only allowed HA functions based on mode.
    """
    if mode == "owner":
        # All functions available
        return [
            {
                "name": "turn_on",
                "description": "Turn on a device or entity",
                "parameters": {
                    "entity_id": {"type": "string"},
                    "brightness": {"type": "integer", "min": 0, "max": 100},
                    "volume": {"type": "integer", "min": 0, "max": 100}
                }
            },
            # ... all other functions
        ]

    elif mode == "guest":
        # Filtered functions with caps
        return [
            {
                "name": "turn_on",
                "description": "Turn on a light or switch",
                "parameters": {
                    "entity_id": {
                        "type": "string",
                        "pattern": "^(light|switch)\\."  # Only lights and switches
                    },
                    "brightness": {
                        "type": "integer",
                        "min": 0,
                        "max": policy['scope']['max_brightness']  # Cap at 85
                    }
                }
            },
            {
                "name": "activate_scene",
                "description": "Activate a scene",
                "parameters": {
                    "scene_name": {
                        "type": "string",
                        "enum": policy['scope']['allow_scenes']  # Only allowed scenes
                    }
                }
            },
            # No lock, climate, alarm functions exposed
        ]

async def call_ha_function(function: str, args: dict, policy: dict):
    """
    Execute HA function call with policy enforcement.
    """
    # Validate entity against policy
    if 'entity_id' in args:
        if not is_entity_allowed(args['entity_id'], policy):
            raise PermissionError(f"Entity {args['entity_id']} not allowed in {policy['mode']} mode")

    # Apply caps
    if 'brightness' in args:
        max_brightness = policy['scope'].get('max_brightness')
        if max_brightness:
            args['brightness'] = min(args['brightness'], max_brightness)

    if 'volume' in args:
        max_volume = policy['scope'].get('max_volume')
        if max_volume:
            args['volume'] = min(args['volume'], max_volume)

    # Execute via HA API
    return await ha_client.call_service(function, args)
```

### 3. RAG/Web Search Tools

**Retrieve Node with Mode Awareness:**

```python
async def retrieve(state: GraphState) -> GraphState:
    """
    Retrieve context from RAG sources, filtered by mode policy.
    """
    category = state['category']
    policy = state['policy']

    # Check category allowlist
    if category not in policy['info_categories']['allow']:
        return {
            **state,
            'contexts': [],
            'error': f"Category {category} not allowed in {state['mode']} mode"
        }

    # Get allowed sources for this category + mode
    sources = get_allowed_sources(category, policy)

    # Retrieve from each source
    contexts = []
    for source in sources:
        try:
            result = await source.retrieve(state['text'], limit=5)
            contexts.extend(result)
        except Exception as e:
            logger.warning(f"Source {source.name} failed: {e}")

    # Apply web search domain filtering if needed
    if state.get('needs_web_search'):
        allowed_domains = policy['validation']['web_search_scope']
        contexts = filter_contexts_by_domain(contexts, allowed_domains)

    return {
        **state,
        'contexts': contexts,
        'retrieval_count': len(contexts)
    }

def get_allowed_sources(category: str, policy: dict) -> list:
    """
    Return RAG sources allowed for this category and mode.
    """
    # Map categories to sources
    source_map = {
        'weather': [weather_api],
        'news': [news_rss, news_api],
        'events': [ticketmaster, meetup],
        'airports': [airport_status_api],
        'flights': [flight_tracking_api],
        'sports': [sports_db, espn_api],
        'recipes': [spoonacular],
        'streaming': [justwatch, tmdb],
        'dining': [yelp, google_places],
        'property_info': [property_vector_db],

        # Owner-only categories
        'owner_calendar': [owner_cal_api],
        'security_logs': [security_db]
    }

    sources = source_map.get(category, [])

    # Filter out blocked sources
    blocked = policy['info_categories']['deny']
    if category in blocked:
        return []

    return sources

def filter_contexts_by_domain(contexts: list, allowed_domains: list) -> list:
    """
    Filter web search results by domain allowlist.
    """
    if "*" in allowed_domains:
        return contexts  # No filtering

    filtered = []
    for ctx in contexts:
        if ctx.get('source_type') == 'web':
            domain = extract_domain(ctx['url'])
            if any(matches_pattern(domain, pattern) for pattern in allowed_domains):
                filtered.append(ctx)
        else:
            # Non-web sources always included
            filtered.append(ctx)

    return filtered
```

### 4. Sharing Tools

**Share Node with Mode Awareness:**

```python
async def share_opt(state: GraphState) -> GraphState:
    """
    Handle SMS/email sharing requests with mode-aware restrictions.
    """
    if not state.get('share_requested'):
        return state  # No sharing requested

    policy = state['policy']
    share_config = policy['sharing']

    # Check if sharing enabled for this mode
    if state['share_type'] == 'sms' and not share_config['sms_enabled']:
        return {
            **state,
            'share_result': {
                'success': False,
                'reason': 'SMS sharing not enabled in guest mode'
            }
        }

    if state['share_type'] == 'email' and not share_config['email_enabled']:
        return {
            **state,
            'share_result': {
                'success': False,
                'reason': 'Email sharing not enabled in guest mode'
            }
        }

    # Check rate limits
    mode = state['mode']
    stay_id = state.get('stay_id')

    if mode == 'guest':
        # Check daily limits
        sms_count_today = await get_sms_count_today(stay_id)
        if sms_count_today >= share_config['max_sms_per_day']:
            return {
                **state,
                'share_result': {
                    'success': False,
                    'reason': f"Daily SMS limit ({share_config['max_sms_per_day']}) reached"
                }
            }

    # Redact PII if required
    content = state['response']
    if share_config['redact_personal_data']:
        content = redact_pii(content)

    # Send via appropriate service
    if state['share_type'] == 'sms':
        result = await twilio_client.send_sms(
            to=state['share_destination'],
            body=content
        )
    elif state['share_type'] == 'email':
        result = await email_client.send_email(
            to=state['share_destination'],
            subject=f"From your Airbnb: {state['share_subject']}",
            body=content
        )

    # Log sharing event (without content in guest mode)
    await log_share_event(
        mode=mode,
        stay_id=stay_id,
        share_type=state['share_type'],
        destination=mask_contact(state['share_destination']),  # Mask in logs
        success=result['success'],
        content=None if mode == 'guest' else content  # Only log content in owner mode
    )

    return {
        **state,
        'share_result': result
    }
```

---

## G) Manual Toggles & Owner Override

### 1. Voice PIN Authentication

**Wake Word → PIN Challenge:**

```
Guest: "Jarvis, switch to owner mode"
Athena: "Please say your 4-digit PIN"
Guest: "1 2 3 4"
Athena: "Incorrect PIN. Guest mode remains active."

---

Owner: "Jarvis, switch to owner mode"
Athena: "Please say your 4-digit PIN"
Owner: "5 7 8 9"
Athena: "Owner mode activated. Full access enabled."
```

**Implementation:**

```python
# In orchestrator, handle special "mode switch" intent

async def handle_mode_switch_request(state: GraphState) -> GraphState:
    """
    Handle "switch to owner mode" requests.
    """
    requested_mode = extract_requested_mode(state['text'])  # "owner" or "guest"

    if requested_mode == "owner":
        # Initiate PIN challenge
        return {
            **state,
            'response': "Please say your 4-digit PIN",
            'awaiting_pin': True,
            'pin_attempts': 0
        }
    elif requested_mode == "guest":
        # No PIN needed to switch to guest mode
        await mode_service.set_override("guest")
        return {
            **state,
            'response': "Guest mode activated. Privacy settings applied."
        }

async def handle_pin_response(state: GraphState) -> GraphState:
    """
    Validate PIN and switch mode.
    """
    pin = extract_pin_from_text(state['text'])
    correct_pin = config.get('mode_override_pin', '1234')

    if pin == correct_pin:
        await mode_service.set_override("owner")

        # Optional: set timeout
        timeout_minutes = config.get('owner_mode_timeout_minutes', 60)
        if timeout_minutes:
            await schedule_auto_revert(timeout_minutes)

        return {
            **state,
            'response': f"Owner mode activated. Full access enabled for {timeout_minutes} minutes.",
            'mode': 'owner',
            'awaiting_pin': False
        }
    else:
        attempts = state.get('pin_attempts', 0) + 1

        if attempts >= 3:
            # Lock out after 3 failed attempts
            await security_log_failed_pin_attempts(state['room'], attempts)
            return {
                **state,
                'response': "Too many incorrect attempts. Guest mode remains active.",
                'awaiting_pin': False
            }
        else:
            return {
                **state,
                'response': f"Incorrect PIN. {3 - attempts} attempts remaining.",
                'awaiting_pin': True,
                'pin_attempts': attempts
            }
```

### 2. Home Assistant UI Toggle

**Lovelace Card:**

```yaml
# ui-lovelace.yaml
type: entities
title: Project Athena Mode
entities:
  - entity: sensor.project_athena_mode
    name: Current Mode
    icon: mdi:account-check

  - entity: sensor.project_athena_mode_reason
    name: Mode Reason

  - type: divider

  - entity: input_boolean.guest_mode_override
    name: Manual Override
    icon: mdi:account-lock

  - type: buttons
    entities:
      - entity: script.athena_force_guest_mode
        name: Force Guest Mode
        icon: mdi:account-multiple
        tap_action:
          action: call-service
          service: script.athena_force_guest_mode

      - entity: script.athena_force_owner_mode
        name: Force Owner Mode
        icon: mdi:account-star
        tap_action:
          action: call-service
          service: script.athena_force_owner_mode

      - entity: script.athena_auto_mode
        name: Auto Mode
        icon: mdi:calendar-clock
        tap_action:
          action: call-service
          service: script.athena_auto_mode
```

**Scripts:**

```yaml
# scripts.yaml
athena_force_guest_mode:
  sequence:
    - service: rest_command.athena_mode_override
      data:
        mode: "guest"
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.guest_mode_override

athena_force_owner_mode:
  sequence:
    - service: rest_command.athena_mode_override
      data:
        mode: "owner"
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.guest_mode_override

athena_auto_mode:
  sequence:
    - service: rest_command.athena_mode_override
      data:
        mode: null  # Clear override
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.guest_mode_override

# REST commands
rest_command:
  athena_mode_override:
    url: "http://192.168.10.167:8001/mode/override"
    method: POST
    headers:
      Authorization: "Bearer {{ states('input_text.athena_api_key') }}"
      Content-Type: "application/json"
    payload: '{"mode": "{{ mode }}"}'
```

### 3. Mode Service API

**Endpoints:**

```python
from fastapi import FastAPI, HTTPException, Header
from typing import Optional

app = FastAPI()

@app.get("/mode/current")
async def get_current_mode() -> dict:
    """
    Get current mode and reason.
    """
    mode, reason, stay_id = await determine_current_mode()

    # Get next mode change (if any)
    next_change = await get_next_mode_change()

    return {
        "mode": mode,
        "reason": reason,
        "stay_id": stay_id,
        "next_change": next_change,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/mode/override")
async def set_mode_override(
    request: ModeOverrideRequest,
    authorization: str = Header(...)
) -> dict:
    """
    Manually override mode.

    Request body:
    {
        "mode": "guest" | "owner" | null,  # null = auto mode
        "duration_minutes": 60,             # optional, default from config
        "pin": "1234"                       # required for owner mode
    }
    """
    # Verify API key
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Validate PIN if switching to owner mode
    if request.mode == "owner":
        if not request.pin or request.pin != config.owner_pin:
            await security_log_failed_override_attempt()
            raise HTTPException(status_code=403, detail="Invalid PIN")

    # Set override
    if request.mode is None:
        # Clear override, return to auto mode
        await clear_mode_override()
        mode, reason, _ = await determine_current_mode()

        return {
            "status": "success",
            "mode": mode,
            "reason": "auto_mode_restored",
            "message": "Automatic mode detection restored"
        }
    else:
        # Set manual override
        duration_minutes = request.duration_minutes or config.default_override_duration
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

        await set_mode_override(request.mode, expires_at)

        # Schedule auto-revert if timeout configured
        if duration_minutes:
            await schedule_auto_revert(expires_at)

        return {
            "status": "success",
            "mode": request.mode,
            "reason": "manual_override",
            "expires_at": expires_at.isoformat() if duration_minutes else None,
            "message": f"{request.mode.title()} mode activated"
        }

@app.get("/mode/schedule")
async def get_mode_schedule(
    days: int = 7
) -> dict:
    """
    Get upcoming mode changes based on bookings.
    """
    bookings = await get_upcoming_bookings(days=days)

    schedule = []
    for booking in bookings:
        schedule.append({
            "start": booking.start_time.isoformat(),
            "end": booking.end_time.isoformat(),
            "mode": "guest",
            "stay_id": booking.stay_id,
            "guest_name": booking.guest_name if booking.guest_name else "Guest"
        })

    return {
        "schedule": schedule,
        "default_mode": config.default_mode
    }
```

---

## H) Tracking, Analytics, and Feedback

### Request/Response Logging Schema

**PostgreSQL Tables:**

```sql
-- Request envelope
CREATE TABLE requests (
    request_id VARCHAR(64) PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    mode VARCHAR(16) NOT NULL,
    stay_id VARCHAR(64),
    room VARCHAR(64),
    device_id VARCHAR(64),

    -- Request data (PII scrubbed if guest mode)
    text_normalized TEXT,
    text_hash VARCHAR(64),  -- For deduplication

    -- Routing
    pipeline VARCHAR(32),  -- "control" or "knowledge"
    intent VARCHAR(64),

    -- Performance
    latency_ms_total INTEGER,
    latency_ms_stt INTEGER,
    latency_ms_classify INTEGER,
    latency_ms_route INTEGER,
    latency_ms_retrieve INTEGER,
    latency_ms_synthesize INTEGER,
    latency_ms_validate INTEGER,
    latency_ms_tts INTEGER,

    -- Outcome
    success BOOLEAN,
    error_type VARCHAR(64),
    error_message TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_requests_timestamp ON requests(timestamp DESC);
CREATE INDEX idx_requests_mode ON requests(mode, timestamp DESC);
CREATE INDEX idx_requests_stay ON requests(stay_id, timestamp DESC);
CREATE INDEX idx_requests_success ON requests(success, mode);

-- Response data
CREATE TABLE responses (
    response_id VARCHAR(64) PRIMARY KEY,
    request_id VARCHAR(64) REFERENCES requests(request_id) ON DELETE CASCADE,

    -- Response content (null if guest mode + pii_scrub)
    text TEXT,
    text_hash VARCHAR(64),

    -- Model info
    models_used JSONB,  -- [{"name": "llama-3.1-8b", "role": "primary"}, ...]

    -- RAG info
    sources_retrieved INTEGER,
    sources_used INTEGER,
    categories JSONB,  -- ["weather", "news"]

    -- Validation
    validation_passed BOOLEAN,
    validation_details JSONB,  -- {"policy": "pass", "retrieval": "pass", "cross_model": "triggered"}
    retrieval_confidence FLOAT,
    cross_model_used BOOLEAN,

    -- Citations
    citations JSONB,  -- [{"source": "weather.gov", "freshness": "5min", "url": "..."}]

    -- Sharing
    share_requested BOOLEAN DEFAULT FALSE,
    share_type VARCHAR(16),  -- "sms" or "email"
    share_success BOOLEAN,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_responses_request ON responses(request_id);

-- Answer feedback
CREATE TABLE answer_feedback (
    feedback_id VARCHAR(64) PRIMARY KEY,
    request_id VARCHAR(64) REFERENCES requests(request_id),
    response_id VARCHAR(64) REFERENCES responses(response_id),

    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    mode VARCHAR(16),

    -- Feedback
    rating VARCHAR(16),  -- "good", "bad", "neutral"
    reason VARCHAR(64),  -- "wrong_info", "incomplete", "off_topic", "helpful"
    comment TEXT,

    -- Context
    categories JSONB,
    models_used JSONB,
    retrieval_confidence FLOAT,

    -- Follow-up
    retest_requested BOOLEAN DEFAULT FALSE,
    retest_completed BOOLEAN DEFAULT FALSE,
    retest_outcome VARCHAR(16),

    -- Admin notes
    reviewed BOOLEAN DEFAULT FALSE,
    admin_notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_feedback_rating ON answer_feedback(rating, timestamp DESC);
CREATE INDEX idx_feedback_reviewed ON answer_feedback(reviewed, timestamp DESC);
CREATE INDEX idx_feedback_mode ON answer_feedback(mode, rating);

-- Share events (minimal logging for guest mode)
CREATE TABLE share_events (
    event_id VARCHAR(64) PRIMARY KEY,
    request_id VARCHAR(64) REFERENCES requests(request_id),

    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    mode VARCHAR(16),
    stay_id VARCHAR(64),

    share_type VARCHAR(16),  -- "sms" or "email"
    destination_hash VARCHAR(64),  -- Hashed phone/email (never plaintext)

    success BOOLEAN,
    error_message TEXT,

    -- Content NOT logged in guest mode (only delivery status)
    content_type VARCHAR(64),  -- "directions", "recipe", "recommendation"
    content_hash VARCHAR(64),   -- For deduplication

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_share_events_mode ON share_events(mode, timestamp DESC);
CREATE INDEX idx_share_events_stay ON share_events(stay_id, timestamp DESC);
```

### Prometheus Metrics

**Metrics Exported:**

```python
from prometheus_client import Counter, Histogram, Gauge, Enum

# Request metrics
requests_total = Counter(
    'athena_requests_total',
    'Total requests by mode and pipeline',
    ['mode', 'pipeline', 'intent']
)

request_duration_seconds = Histogram(
    'athena_request_duration_seconds',
    'Request duration by mode and stage',
    ['mode', 'pipeline', 'stage'],
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

request_success_rate = Gauge(
    'athena_request_success_rate',
    'Success rate by mode (rolling 5min)',
    ['mode', 'pipeline']
)

# Mode metrics
current_mode = Enum(
    'athena_current_mode',
    'Current system mode',
    states=['guest', 'owner']
)

mode_switches_total = Counter(
    'athena_mode_switches_total',
    'Total mode switches',
    ['from_mode', 'to_mode', 'reason']
)

# Denial metrics
denials_total = Counter(
    'athena_denials_total',
    'Policy denials by reason',
    ['mode', 'reason', 'category']
)

# Validation metrics
validation_triggers_total = Counter(
    'athena_validation_triggers_total',
    'Validation triggers by type',
    ['mode', 'validation_type', 'outcome']
)

cross_model_usage = Counter(
    'athena_cross_model_usage_total',
    'Cross-model validation usage',
    ['mode', 'outcome']
)

# RAG metrics
rag_retrieval_total = Counter(
    'athena_rag_retrieval_total',
    'RAG retrievals by category and mode',
    ['mode', 'category', 'success']
)

rag_confidence = Histogram(
    'athena_rag_confidence',
    'RAG retrieval confidence scores',
    ['mode', 'category'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# Feedback metrics
feedback_total = Counter(
    'athena_feedback_total',
    'Feedback by rating and mode',
    ['mode', 'rating', 'reason']
)

feedback_bad_answer_rate = Gauge(
    'athena_bad_answer_rate',
    'Bad answer rate by mode (rolling 24h)',
    ['mode']
)

# Share metrics
shares_total = Counter(
    'athena_shares_total',
    'Share events by type and mode',
    ['mode', 'share_type', 'success']
)
```

### Grafana Dashboards

**Dashboard 1: Mode Overview**
- Current mode (gauge)
- Mode timeline (time series: guest vs owner over time)
- Upcoming mode changes (table from bookings)
- Mode switches (count by reason)
- Manual overrides (count)

**Dashboard 2: Performance**
- Request rate by mode (requests/min)
- Latency by stage (heatmap)
- Success rate by mode (gauge + time series)
- Error rate by type (pie chart)

**Dashboard 3: Policy Enforcement**
- Denials by reason (bar chart)
- Top denied domains/categories (table)
- Quiet hours activations (count)
- Permission violations (time series)

**Dashboard 4: Quality & Feedback**
- Bad answer rate (gauge)
- Feedback distribution (pie: good/bad/neutral)
- Top failure patterns (table)
- Retest outcomes (bar chart)

**Dashboard 5: RAG & Validation**
- Retrieval hit rate by category (bar chart)
- Confidence score distribution (histogram)
- Cross-model validation rate (gauge)
- Validation pass/fail (time series)

**Dashboard 6: Guest Experience**
- Active stays (count)
- Guest requests by room (bar chart)
- Share events (SMS vs email, time series)
- Top guest queries (table)

### Feedback Collection

**Voice Feedback:**

```python
# In orchestrator, detect feedback intent

async def handle_feedback_intent(state: GraphState) -> GraphState:
    """
    Handle "that answer was wrong" or "that was helpful" feedback.
    """
    feedback_type = extract_feedback_type(state['text'])  # "bad", "good", "neutral"

    # Get last request/response from session
    last_exchange = await get_last_exchange(state['device_id'])

    if not last_exchange:
        return {
            **state,
            'response': "I don't have a recent answer to give feedback on."
        }

    # Record feedback
    feedback_id = await record_feedback(
        request_id=last_exchange['request_id'],
        response_id=last_exchange['response_id'],
        rating=feedback_type,
        reason=None,  # Could ask follow-up: "What was wrong?"
        mode=state['mode']
    )

    # Acknowledge
    if feedback_type == "bad":
        return {
            **state,
            'response': "Thanks for letting me know. I'll try to improve. Would you like me to try answering again?"
        }
    elif feedback_type == "good":
        return {
            **state,
            'response': "Great! I'm glad I could help."
        }
```

**HA UI Feedback:**

```yaml
# Custom Lovelace card for recent answers

type: custom:auto-entities
card:
  type: entities
  title: Recent Athena Answers
filter:
  include:
    - entity_id: sensor.athena_recent_*
show_empty: false
card_mod:
  style: |
    ha-card {
      button {
        margin: 5px;
      }
    }

# Each answer sensor has:
# - Text of question
# - Text of answer (truncated)
# - Timestamp
# - request_id for feedback submission
# - Thumbs up/down buttons

# Automation to submit feedback
automation:
  - alias: "Athena Feedback Submit"
    trigger:
      - platform: event
        event_type: athena_feedback_button_pressed
    action:
      - service: rest_command.submit_athena_feedback
        data:
          request_id: "{{ trigger.event.data.request_id }}"
          rating: "{{ trigger.event.data.rating }}"
          reason: "{{ trigger.event.data.reason }}"
```

### Nightly Improvement Analysis

**Background Job:**

```python
import asyncio
from datetime import datetime, timedelta
from collections import Counter

async def nightly_improvement_analysis():
    """
    Analyze bad answers and suggest improvements.
    Runs daily at 3 AM.
    """
    # Get yesterday's bad feedback
    yesterday = datetime.now() - timedelta(days=1)
    bad_feedback = await db.get_feedback(
        start=yesterday.replace(hour=0, minute=0),
        end=yesterday.replace(hour=23, minute=59),
        rating='bad'
    )

    if not bad_feedback:
        logger.info("No bad feedback yesterday. Skip analysis.")
        return

    # Cluster by failure pattern
    patterns = {
        'missing_source': [],
        'low_confidence': [],
        'wrong_category': [],
        'rate_limited': [],
        'stale_data': [],
        'hallucination': []
    }

    for feedback in bad_feedback:
        # Get full request/response context
        request = await db.get_request(feedback.request_id)
        response = await db.get_response(feedback.response_id)

        # Classify failure pattern
        if response.sources_used == 0:
            patterns['missing_source'].append(feedback)
        elif response.retrieval_confidence < 0.5:
            patterns['low_confidence'].append(feedback)
        elif not response.validation_passed:
            patterns['hallucination'].append(feedback)
        # ... other patterns

    # Generate report
    report = {
        'date': yesterday.date().isoformat(),
        'total_bad_feedback': len(bad_feedback),
        'patterns': {}
    }

    for pattern_name, items in patterns.items():
        if not items:
            continue

        # Analyze pattern
        categories = Counter(item.categories[0] for item in items if item.categories)
        models = Counter(item.models_used[0]['name'] for item in items if item.models_used)

        # Generate suggestions
        suggestions = generate_suggestions(pattern_name, items, categories, models)

        report['patterns'][pattern_name] = {
            'count': len(items),
            'categories': dict(categories.most_common(5)),
            'models': dict(models.most_common(3)),
            'suggestions': suggestions
        }

    # Save report
    await db.save_analysis_report(report)

    # Notify admin (optional)
    if report['total_bad_feedback'] > 10:  # Threshold
        await notify_admin(f"High bad feedback count: {report['total_bad_feedback']}")

    logger.info(f"Analysis complete: {report['total_bad_feedback']} bad answers analyzed")

def generate_suggestions(pattern: str, items: list, categories: Counter, models: Counter) -> list:
    """
    Generate actionable suggestions based on failure pattern.
    """
    suggestions = []

    if pattern == 'missing_source':
        top_category = categories.most_common(1)[0][0]
        suggestions.append(f"Add more RAG sources for category: {top_category}")
        suggestions.append(f"Check API availability for {top_category}")

    elif pattern == 'low_confidence':
        suggestions.append("Consider lowering retrieval confidence threshold")
        suggestions.append("Add more embedding vectors for common queries")
        suggestions.append("Enable cross-model validation for borderline cases")

    elif pattern == 'hallucination':
        top_model = models.most_common(1)[0][0]
        suggestions.append(f"Review {top_model} prompt template")
        suggestions.append("Enable stricter anti-hallucination guardrails")
        suggestions.append("Increase cross-model validation threshold")

    elif pattern == 'stale_data':
        top_category = categories.most_common(1)[0][0]
        suggestions.append(f"Reduce cache TTL for category: {top_category}")
        suggestions.append(f"Check API polling frequency")

    return suggestions
```

---

## I) UI & Guest Experience

### Guest Info Card (QR Code + Printed Card)

**Content:**

```
╔════════════════════════════════════════════════════════╗
║        Welcome to Your Airbnb at 912 South Clinton    ║
║                    Baltimore, MD                       ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  🎤 VOICE ASSISTANT - PROJECT ATHENA                  ║
║                                                        ║
║  Wake Words: Say "Jarvis" or "Athena"                ║
║                                                        ║
║  📍 Available in:                                     ║
║     • Kitchen  • Living Room  • Bedrooms  • Baths     ║
║                                                        ║
║  💡 What You Can Do:                                  ║
║     "Turn on the living room lights"                  ║
║     "Play relaxing music"                             ║
║     "Activate movie night scene"                      ║
║     "What's the weather tomorrow?"                    ║
║     "Where should I eat nearby?"                      ║
║     "Text me directions to the aquarium"              ║
║                                                        ║
║  🔒 Privacy First:                                    ║
║     • No recordings saved beyond your stay            ║
║     • No access to owner devices or areas             ║
║     • All data auto-deleted at checkout               ║
║                                                        ║
║  📱 More Info:                                        ║
║     [QR CODE] → Scan for full guide                   ║
║                                                        ║
║  Quiet Hours: 10 PM - 7 AM (whisper mode)            ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

**QR Code Links To:**
- Full guest guide (wiki page or static site)
- Example commands by category
- Local recommendations (restaurants, attractions)
- Emergency contacts
- Check-out instructions

### Owner Admin Page (Web UI)

**Tech Stack:**
- Frontend: React + Tailwind CSS
- Backend: FastAPI (served alongside Mode Service)
- Auth: Simple API key or HA OAuth

**Pages:**

**1. Dashboard (Home)**
- Current mode indicator (large badge)
- Mode reason (booking, override, default)
- Next mode change countdown
- Quick stats (requests/hour, success rate, denials)
- Active stay info (if guest mode)

**2. Mode Control**
- Auto/Manual toggle
- Force Guest/Owner buttons with PIN prompt
- Booking calendar view (upcoming stays)
- Mode history (timeline of switches)

**3. Scope Settings**
- Edit `security_modes.yaml` via UI
- Domain/entity allowlists/denylists
- Category toggles
- Caps (brightness, volume)
- Quiet hours config
- Share settings

**4. Live Metrics**
- Grafana dashboards embedded
- Real-time request feed (last 20)
- Latency charts
- Success rate gauges
- Denial reasons pie chart

**5. Feedback Review**
- Recent answers with thumbs up/down
- Filter by rating, mode, category
- Retest button (re-run query now)
- Admin notes field
- Mark as reviewed

**6. Guest Data Management**
- Current stay details
- Guest usage stats (anonymized)
- Data retention countdown
- Manual purge button (force immediate deletion)
- Export anonymized metrics

**7. System Health**
- Service status (gateway, orchestrator, mode service, vector DB)
- Model status (loaded, inference times)
- RAG source status (API health checks)
- Background job status (calendar poll, analysis)

**Mock UI (Dashboard):**

```
┌─────────────────────────────────────────────────────────┐
│  Project Athena Admin                        [Logout]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Current Mode: [GUEST MODE]  🟢                        │
│  Reason: Active Airbnb booking (Stay #abc123)          │
│  Next Change: Checkout in 2d 14h (Nov 13, 11:00 AM)   │
│                                                         │
│  ┌─────────────┬─────────────┬─────────────┐          │
│  │ Auto Mode   │ Force Guest │ Force Owner │          │
│  │  [Active]   │  [ Button ] │  [ Button ] │          │
│  └─────────────┴─────────────┴─────────────┘          │
│                                                         │
│  Quick Stats (Last Hour):                              │
│  ┌──────────────────┬──────────────────┐              │
│  │ Requests: 47     │ Success: 94%     │              │
│  │ Denials: 3       │ Avg Latency: 2.1s│              │
│  └──────────────────┴──────────────────┘              │
│                                                         │
│  Active Stay:                                          │
│  Guest: [Redacted]                                     │
│  Check-in: Nov 11, 3:00 PM                            │
│  Check-out: Nov 13, 11:00 AM                          │
│  Usage: 47 requests (23 control, 24 info)             │
│                                                         │
│  Recent Activity:                                      │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 10:45 AM  Kitchen    "weather tomorrow"    ✓   │  │
│  │ 10:42 AM  Living    "turn on lights"       ✓   │  │
│  │ 10:38 AM  Kitchen    "unlock door"         ✗   │  │
│  │           (Denied: entity restricted)          │  │
│  │ 10:35 AM  Living    "play jazz"            ✓   │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  [View Full Dashboard] [Feedback Review] [Settings]   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## J) Home Assistant & Pipeline Wiring

### No Major Changes to Pipelines

**Existing Design Preserved:**
- Two Assist Pipelines: **Control (Local)** and **Knowledge (LLM)**
- STT/TTS via Wyoming (Faster-Whisper + Piper)
- OpenAI Conversation integration pointing to gateway

**Mode Determination Happens Server-Side:**
- HA Voice devices send requests as normal
- Gateway queries Mode Service before forwarding to orchestrator
- No HA-side mode detection needed

### Optional: Mode Sensors for Dashboards

**Expose mode to HA for visibility:**

```python
# Mode Service exposes MQTT or webhook to update HA sensors

import asyncio
from homeassistant_api import Client

ha_client = Client(config.ha_url, config.ha_token)

async def update_ha_sensors(mode: str, reason: str, stay_id: str):
    """
    Update HA sensors with current mode.
    """
    await ha_client.set_state(
        'sensor.project_athena_mode',
        state=mode,
        attributes={
            'reason': reason,
            'stay_id': stay_id,
            'updated_at': datetime.now().isoformat()
        }
    )

    await ha_client.set_state(
        'binary_sensor.guest_mode_active',
        state='on' if mode == 'guest' else 'off'
    )
```

**HA Configuration:**

```yaml
# configuration.yaml

# MQTT sensors (if using MQTT bridge)
mqtt:
  sensor:
    - name: "Project Athena Mode"
      state_topic: "athena/mode"
      json_attributes_topic: "athena/mode/attributes"
      icon: mdi:account-check

    - name: "Project Athena Mode Reason"
      state_topic: "athena/mode/reason"
      icon: mdi:information

  binary_sensor:
    - name: "Guest Mode Active"
      state_topic: "athena/mode/guest_active"
      payload_on: "true"
      payload_off: "false"
      device_class: presence
      icon: mdi:account-multiple

# Automations (optional)
automation:
  # Notify owner when guest mode activates
  - alias: "Athena Guest Mode Started"
    trigger:
      - platform: state
        entity_id: binary_sensor.guest_mode_active
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Guest mode activated for stay {{ state_attr('sensor.project_athena_mode', 'stay_id') }}"

  # Auto-purge reminder
  - alias: "Athena Guest Data Purge Reminder"
    trigger:
      - platform: state
        entity_id: binary_sensor.guest_mode_active
        to: "off"
        for: "01:00:00"  # 1 hour after guest mode ends
    action:
      - service: notify.mobile_app
        data:
          message: "Guest data purge scheduled. All guest logs will be deleted."
```

---

## K) LangGraph & Gateway Updates

### Gateway Request Enrichment

**Add Mode Metadata:**

```python
from fastapi import FastAPI, Request, Header
from typing import Optional

app = FastAPI()

@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    x_athena_room: Optional[str] = Header(None),
    x_athena_device_id: Optional[str] = Header(None)
):
    """
    OpenAI-compatible chat completions endpoint.
    Enriches requests with mode metadata before forwarding.
    """
    body = await request.json()

    # Query Mode Service for current mode
    mode_response = await http_client.get("http://localhost:8001/mode/current")
    mode_data = mode_response.json()

    # Enrich request metadata
    metadata = body.get('metadata', {})
    metadata.update({
        'mode': mode_data['mode'],
        'mode_reason': mode_data['reason'],
        'stay_id': mode_data.get('stay_id'),
        'room': x_athena_room or metadata.get('room', 'unknown'),
        'device_id': x_athena_device_id or metadata.get('device_id', 'unknown'),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'request_id': generate_request_id()
    })

    body['metadata'] = metadata

    # Forward to orchestrator
    response = await http_client.post(
        "http://localhost:8002/query",
        json=body
    )

    return response.json()
```

### Orchestrator Preflight Node

**Add as First Node in LangGraph:**

```python
from langgraph.graph import StateGraph, END

# Define graph
graph = StateGraph(GraphState)

# Add nodes
graph.add_node("preflight_check", preflight_check)  # NEW: first node
graph.add_node("classify", classify_intent)
graph.add_node("route_control", route_control)
graph.add_node("route_info", route_info)
graph.add_node("retrieve", retrieve_context)
graph.add_node("synthesize", synthesize_answer)
graph.add_node("validate", validate_answer)
graph.add_node("share_opt", share_optional)
graph.add_node("finalize", finalize_response)

# Define edges
graph.set_entry_point("preflight_check")  # Start here

graph.add_conditional_edges(
    "preflight_check",
    lambda state: "denied" if state.get('intent') == 'denied' else "classify",
    {
        "denied": "finalize",  # Early exit for policy violations
        "classify": "classify"
    }
)

graph.add_conditional_edges(
    "classify",
    lambda state: state['intent'],
    {
        "control": "route_control",
        "info": "route_info",
        "complex": "route_info"
    }
)

# ... rest of graph edges
```

### Policy Loading

**Load Mode Policy from Config:**

```python
import yaml
from pathlib import Path

class PolicyManager:
    def __init__(self, config_path: str = "config/security_modes.yaml"):
        self.config_path = Path(config_path)
        self._policies = None
        self._load_policies()

    def _load_policies(self):
        with open(self.config_path) as f:
            self._policies = yaml.safe_load(f)

    def get_policy(self, mode: str) -> dict:
        """
        Get policy for given mode.
        """
        if mode not in self._policies['modes']:
            raise ValueError(f"Unknown mode: {mode}")

        return self._policies['modes'][mode]

    def reload(self):
        """
        Reload policies from disk (for live updates).
        """
        self._load_policies()

# Global instance
policy_manager = PolicyManager()

def load_policy(mode: str) -> dict:
    return policy_manager.get_policy(mode)
```

---

## L) Data Retention & Privacy

### PII Scrubbing

**Scrub Function:**

```python
import re
from typing import Optional

def redact_pii(text: str, mode: str = "guest") -> str:
    """
    Redact personally identifiable information from text.
    More aggressive in guest mode.
    """
    if mode != "guest":
        return text  # Owner mode: preserve full text

    # Email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)

    # Phone numbers (US format)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b', '[PHONE]', text)

    # Credit card numbers
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CC_NUMBER]', text)

    # SSN
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)

    # Street addresses (simple pattern)
    text = re.sub(r'\b\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Boulevard|Blvd)\b', '[ADDRESS]', text, flags=re.IGNORECASE)

    # Names (if guest name is known from booking)
    # guest_name = get_guest_name_from_stay(stay_id)
    # if guest_name:
    #     text = text.replace(guest_name, '[GUEST_NAME]')

    return text

def mask_contact(contact: str) -> str:
    """
    Mask phone/email for logging.
    Examples:
      +15551234567 → +1555***4567
      john@example.com → j***@example.com
    """
    if '@' in contact:
        # Email
        local, domain = contact.split('@')
        return f"{local[0]}***@{domain}"
    else:
        # Phone
        if len(contact) > 7:
            return f"{contact[:4]}***{contact[-4:]}"
        return "***"
```

### Automatic Purge on Checkout

**Purge Job:**

```python
import asyncio
from datetime import datetime, timedelta

async def guest_data_purge_job():
    """
    Background job to purge guest data after checkout.
    Runs every hour.
    """
    while True:
        try:
            await purge_expired_stays()
        except Exception as e:
            logger.error(f"Purge job failed: {e}")

        await asyncio.sleep(3600)  # 1 hour

async def purge_expired_stays():
    """
    Find stays that ended > buffer time ago and purge data.
    """
    buffer_hours = config.get('retention', {}).get('purge_delay_hours', 1)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=buffer_hours)

    # Find ended stays
    ended_stays = await db.execute(
        "SELECT stay_id, end_time FROM bookings WHERE end_time < %s AND NOT cancelled",
        (cutoff,)
    )

    for stay in ended_stays:
        stay_id = stay['stay_id']
        logger.info(f"Purging data for stay {stay_id} (ended {stay['end_time']})")

        # Delete requests/responses for this stay
        deleted_requests = await db.execute(
            "DELETE FROM requests WHERE stay_id = %s RETURNING request_id",
            (stay_id,)
        )

        # Cascade deletes responses and feedback automatically (ON DELETE CASCADE)

        # Delete share events
        await db.execute(
            "DELETE FROM share_events WHERE stay_id = %s",
            (stay_id,)
        )

        # Delete vector DB entries (if tagged with stay_id)
        await vector_db.delete_collection(f"stay_{stay_id}")

        # Mark booking as purged
        await db.execute(
            "UPDATE bookings SET data_purged = TRUE, purged_at = NOW() WHERE stay_id = %s",
            (stay_id,)
        )

        logger.info(f"Purged {len(deleted_requests)} requests for stay {stay_id}")

        # Emit audit event
        await audit_log.record(
            event='guest_data_purged',
            stay_id=stay_id,
            records_deleted=len(deleted_requests),
            timestamp=datetime.now(timezone.utc)
        )

# Start background job
asyncio.create_task(guest_data_purge_job())
```

### Manual Purge (Owner Action)

**API Endpoint:**

```python
@app.post("/admin/purge/{stay_id}")
async def manual_purge_stay(
    stay_id: str,
    authorization: str = Header(...)
):
    """
    Manually purge guest data for a stay.
    Requires admin authorization.
    """
    # Verify admin API key
    if not verify_admin_key(authorization):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if stay exists
    stay = await db.get_booking(stay_id)
    if not stay:
        raise HTTPException(status_code=404, detail="Stay not found")

    # Purge data
    deleted = await purge_stay_data(stay_id)

    return {
        "status": "success",
        "stay_id": stay_id,
        "records_deleted": deleted,
        "message": f"All data for stay {stay_id} has been permanently deleted"
    }

async def purge_stay_data(stay_id: str) -> int:
    """
    Purge all data associated with a stay.
    Returns count of deleted records.
    """
    # Delete from all tables
    count = 0

    count += await db.execute("DELETE FROM requests WHERE stay_id = %s", (stay_id,))
    count += await db.execute("DELETE FROM share_events WHERE stay_id = %s", (stay_id,))

    # Vector DB
    await vector_db.delete_collection(f"stay_{stay_id}")

    # Mark booking
    await db.execute(
        "UPDATE bookings SET data_purged = TRUE, purged_at = NOW() WHERE stay_id = %s",
        (stay_id,)
    )

    return count
```

---

## M) Testing Matrix

### Test Cases

**1. Mode Determination**
- [ ] Auto mode activates 2h before check-in
- [ ] Auto mode deactivates 1h after checkout
- [ ] Manual override takes precedence over calendar
- [ ] Owner PIN correctly switches to owner mode
- [ ] Invalid PIN keeps guest mode active (3 attempts max)
- [ ] Owner mode timeout reverts to auto after configured duration
- [ ] Calendar poll detects new bookings within 10 minutes

**2. Permission Enforcement**
- [ ] Guest denied access to locks
- [ ] Guest denied access to alarm system
- [ ] Guest denied access to owner bedroom climate
- [ ] Guest allowed to control living room lights
- [ ] Guest brightness capped at 85%
- [ ] Guest volume capped at 60%
- [ ] Quiet hours prevent media player use (10 PM - 7 AM)
- [ ] Quiet hours allow lights at low levels
- [ ] Guest denied access to owner calendar category
- [ ] Guest allowed access to weather category

**3. Information Queries**
- [ ] Guest weather query succeeds with proper cache
- [ ] Guest airport query triggers high-stakes validation
- [ ] Guest "where to eat" query returns nearby with distance
- [ ] Guest streaming query returns availability across 8 services
- [ ] Owner query accesses owner-only calendar
- [ ] Cross-model validation triggers for flight times
- [ ] Bad answer marked via voice feedback
- [ ] Bad answer marked via HA UI

**4. Sharing Functionality**
- [ ] Guest "text me directions" sends SMS successfully
- [ ] Guest SMS rate-limited after 10/day
- [ ] Guest email limited to 5/day
- [ ] PII redacted in shared content (guest mode)
- [ ] Full content shared in owner mode (no redaction)
- [ ] Share event logged with masked destination
- [ ] Share content NOT logged in guest mode

**5. Data Retention**
- [ ] Guest logs PII-scrubbed on write
- [ ] Owner logs preserve full text
- [ ] Guest data auto-purged 1h after checkout
- [ ] Manual purge deletes all stay data immediately
- [ ] Purge audit event recorded
- [ ] Anonymized metrics retained after purge

**6. Feedback Loop**
- [ ] Voice "that was wrong" records bad feedback
- [ ] HA UI thumbs down records bad feedback with reason
- [ ] Retest button re-runs query with fresh data
- [ ] Nightly analysis identifies top failure patterns
- [ ] Suggestions generated for missing sources
- [ ] Suggestions generated for low confidence

**7. Integration**
- [ ] iCal poll updates booking cache every 10 minutes
- [ ] Mode change event emitted on check-in
- [ ] Mode change event emitted on checkout
- [ ] HA sensor reflects current mode
- [ ] HA binary_sensor shows guest mode active
- [ ] Grafana dashboard displays mode timeline

**8. Edge Cases**
- [ ] Early check-in (before buffer) activates guest mode
- [ ] Late checkout (after buffer) extends guest mode
- [ ] Booking cancelled → guest mode not activated
- [ ] Overlapping bookings → guest mode remains active
- [ ] Network outage → calendar poll retries, mode unchanged
- [ ] Mode Service down → gateway returns cached mode

---

## N) New Components to Build

### 1. Mode Service

**Location:** `apps/mode_service/`

**Tech Stack:**
- FastAPI (Python)
- PostgreSQL (booking storage)
- APScheduler (iCal polling)

**Endpoints:**
- `GET /mode/current`
- `POST /mode/override`
- `GET /mode/schedule`
- `GET /health`

**Background Jobs:**
- iCal polling (every 10 minutes)
- Mode expiry check (every 1 minute)
- Booking cleanup (daily)

**Dependencies:**
- `icalendar` - iCal parsing
- `httpx` - Async HTTP client
- `sqlalchemy` - Database ORM
- `apscheduler` - Background jobs

### 2. Policy/Scope Module

**Location:** `apps/orchestrator/policy.py`

**Responsibilities:**
- Load `security_modes.yaml`
- Compute effective permissions by mode
- Validate requests against policy
- Format denial messages

**No separate service - embedded in orchestrator.**

### 3. Feedback API

**Location:** `apps/feedback_service/`

**Tech Stack:**
- FastAPI (Python)
- PostgreSQL (feedback storage)

**Endpoints:**
- `POST /feedback`
- `GET /feedback/review`
- `POST /feedback/{feedback_id}/retest`
- `GET /feedback/analysis`

**Background Jobs:**
- Nightly analysis (3 AM)
- Bad answer clustering

### 4. Admin Web UI

**Location:** `apps/admin_ui/`

**Tech Stack:**
- Frontend: React + Vite + Tailwind CSS
- Backend: Served by Mode Service or standalone
- Charts: Recharts or Chart.js

**Pages:**
- Dashboard
- Mode Control
- Scope Settings
- Live Metrics (Grafana embed)
- Feedback Review
- Guest Data Management
- System Health

**Build:**
```bash
cd apps/admin_ui
npm install
npm run build
# Output to apps/admin_ui/dist
# Serve via FastAPI static files
```

---

## O) Implementation Delta Tasks

**Phase 1: Mode Service Foundation**
1. [ ] Create `apps/mode_service/` structure
2. [ ] Implement `/mode/current` endpoint
3. [ ] Implement `/mode/override` endpoint
4. [ ] Add PostgreSQL `bookings` table
5. [ ] Build iCal connector with polling
6. [ ] Test calendar sync end-to-end
7. [ ] Add mode change event emission
8. [ ] Create HA sensors for mode visibility

**Phase 2: Policy Enforcement**
1. [ ] Define `config/security_modes.yaml` schema
2. [ ] Build PolicyManager class
3. [ ] Add `preflight_check` node to LangGraph
4. [ ] Implement domain/entity allowlist checks
5. [ ] Implement category allowlist checks
6. [ ] Add quiet hours enforcement
7. [ ] Add brightness/volume caps
8. [ ] Format friendly denial messages
9. [ ] Test all denial scenarios

**Phase 3: Gateway Integration**
1. [ ] Add Mode Service client to gateway
2. [ ] Enrich requests with mode metadata
3. [ ] Pass metadata to orchestrator
4. [ ] Update all LangGraph nodes to be mode-aware
5. [ ] Filter RAG sources by mode policy
6. [ ] Apply web search domain filtering
7. [ ] Test control pipeline with guest mode
8. [ ] Test knowledge pipeline with guest mode

**Phase 4: Sharing & PII Protection**
1. [ ] Build `redact_pii()` function
2. [ ] Build `mask_contact()` function
3. [ ] Update `share_opt` node with mode awareness
4. [ ] Add SMS/email rate limiting per stay
5. [ ] Apply PII scrubbing to shared content
6. [ ] Log share events with masked destinations
7. [ ] Test SMS sharing end-to-end
8. [ ] Test email sharing end-to-end

**Phase 5: Data Retention & Purge**
1. [ ] Add `stay_id` to all logged requests
2. [ ] Apply PII scrubbing on log write (guest mode)
3. [ ] Build `guest_data_purge_job()` background task
4. [ ] Add manual purge API endpoint
5. [ ] Test auto-purge on checkout + 1h
6. [ ] Test manual purge via API
7. [ ] Verify anonymized metrics retained
8. [ ] Add purge audit logging

**Phase 6: Feedback System**
1. [ ] Create `answer_feedback` table
2. [ ] Build Feedback API service
3. [ ] Add voice feedback intent detection
4. [ ] Add HA UI feedback buttons
5. [ ] Build nightly analysis job
6. [ ] Implement failure pattern clustering
7. [ ] Generate suggestions from patterns
8. [ ] Test feedback loop end-to-end

**Phase 7: Metrics & Dashboards**
1. [ ] Add Prometheus metrics (mode, denials, validation, RAG, feedback)
2. [ ] Create Grafana dashboard: Mode Overview
3. [ ] Create Grafana dashboard: Performance
4. [ ] Create Grafana dashboard: Policy Enforcement
5. [ ] Create Grafana dashboard: Quality & Feedback
6. [ ] Create Grafana dashboard: RAG & Validation
7. [ ] Create Grafana dashboard: Guest Experience
8. [ ] Set up alerts (bad answer rate, success rate, mode stuck)

**Phase 8: Admin UI**
1. [ ] Initialize React app (`apps/admin_ui/`)
2. [ ] Build Dashboard page
3. [ ] Build Mode Control page
4. [ ] Build Scope Settings page (YAML editor)
5. [ ] Build Live Metrics page (Grafana embeds)
6. [ ] Build Feedback Review page
7. [ ] Build Guest Data Management page
8. [ ] Build System Health page
9. [ ] Add API authentication
10. [ ] Deploy admin UI

**Phase 9: Documentation & Guest UX**
1. [ ] Design guest info card
2. [ ] Create QR code for full guide
3. [ ] Write guest guide page (wiki or static site)
4. [ ] List example commands by category
5. [ ] Add local recommendations
6. [ ] Print physical guest cards
7. [ ] Place in each room with voice device

**Phase 10: Testing & Validation**
1. [ ] Run full testing matrix (47 test cases above)
2. [ ] Simulate guest stay (calendar → auto mode → queries → checkout → purge)
3. [ ] Test manual override scenarios
4. [ ] Test denial messages for usability
5. [ ] Validate PII scrubbing accuracy
6. [ ] Verify cross-model validation triggers
7. [ ] Load test (100 requests/min, guest + owner mix)
8. [ ] Security audit (API key protection, PIN brute-force, data leakage)

---

## P) Success Criteria

### Phase 1 Complete When:
- [ ] Mode Service returns correct mode based on calendar
- [ ] Manual override takes precedence
- [ ] iCal polling updates bookings every 10 minutes
- [ ] Mode change events emitted on check-in/checkout

### Phase 2 Complete When:
- [ ] Guest denied access to 100% of restricted entities
- [ ] Guest allowed access to 100% of permitted entities
- [ ] Brightness/volume caps enforced
- [ ] Quiet hours prevent media, allow lights
- [ ] Friendly denial messages returned

### Phase 3 Complete When:
- [ ] Gateway enriches all requests with mode metadata
- [ ] Orchestrator preflight gate rejects policy violations early
- [ ] RAG sources filtered by mode policy
- [ ] Control pipeline respects domain/entity allowlists
- [ ] Knowledge pipeline respects category allowlists

### Phase 4 Complete When:
- [ ] SMS/email sharing works end-to-end
- [ ] PII redacted in guest mode shares
- [ ] Rate limits enforced (10 SMS/day, 5 email/day)
- [ ] Share events logged with masked destinations
- [ ] No content logged in guest mode

### Phase 5 Complete When:
- [ ] Auto-purge deletes guest data 1h after checkout
- [ ] Manual purge API works correctly
- [ ] Anonymized metrics retained after purge
- [ ] Purge audit events recorded

### Phase 6 Complete When:
- [ ] Voice "that was wrong" records feedback
- [ ] HA UI thumbs down records feedback with reason
- [ ] Retest re-runs query with fresh data
- [ ] Nightly analysis identifies patterns and generates suggestions

### Phase 7 Complete When:
- [ ] All Prometheus metrics exported
- [ ] All Grafana dashboards deployed
- [ ] Dashboards show real-time data
- [ ] Alerts configured and tested

### Phase 8 Complete When:
- [ ] Admin UI accessible via browser
- [ ] All pages functional
- [ ] Mode control works (auto/manual toggles)
- [ ] Feedback review queue works
- [ ] Manual purge button works

### Phase 9 Complete When:
- [ ] Guest info cards printed and placed
- [ ] QR code links to working guide page
- [ ] Guide includes all necessary info
- [ ] Example commands cover all categories

### Phase 10 Complete When:
- [ ] All 47 test cases pass
- [ ] End-to-end guest simulation successful
- [ ] Load test meets SLOs (≤2.5s control, ≤4.0s knowledge)
- [ ] Security audit passes (no vulnerabilities)

---

## Q) Timeline Estimate

**Assumptions:**
- 1 developer
- 4-6 hours/day
- Includes testing and documentation

**Phase 1 (Mode Service):** 3-4 days
**Phase 2 (Policy Enforcement):** 2-3 days
**Phase 3 (Gateway Integration):** 2-3 days
**Phase 4 (Sharing & PII):** 2 days
**Phase 5 (Data Retention):** 2 days
**Phase 6 (Feedback System):** 3-4 days
**Phase 7 (Metrics & Dashboards):** 2-3 days
**Phase 8 (Admin UI):** 4-5 days
**Phase 9 (Guest UX):** 1-2 days
**Phase 10 (Testing):** 3-4 days

**Total:** ~24-33 days (5-7 weeks)

**Parallel Work Opportunities:**
- Admin UI can be built in parallel with backend (Phase 8 || Phases 1-6)
- Guest UX (Phase 9) can start anytime
- Metrics/Dashboards (Phase 7) can be incremental

**Realistic Timeline:** 6-8 weeks for full implementation

---

## R) Open Questions & Decisions

1. **Vector DB Choice:** Qdrant vs Weaviate vs Chroma?
   - Recommendation: **Qdrant** (mature, performant, good Python client)

2. **Admin UI Auth:** Simple API key vs HA OAuth vs Auth0?
   - Recommendation: **API key for MVP**, upgrade to OAuth later

3. **iCal Poll Interval:** 10 minutes vs 5 minutes vs 15 minutes?
   - Recommendation: **10 minutes** (balance between freshness and API load)

4. **Owner Mode Timeout:** 60 minutes vs persist until toggle?
   - Recommendation: **60 minutes with configurable timeout**

5. **PII Scrubbing Aggressiveness:** Current patterns sufficient?
   - Recommendation: **Start with current patterns, expand based on logs**

6. **Cross-Model Validation Threshold:** Always for guest high-stakes vs configurable?
   - Recommendation: **Always for guest mode + high-stakes, configurable for owner**

7. **Share Rate Limits:** 10 SMS/day, 5 email/day too strict?
   - Recommendation: **Start strict, increase based on feedback**

8. **Purge Delay:** 1 hour after checkout sufficient?
   - Recommendation: **1 hour is good, configurable in case of late checkout issues**

9. **Admin UI Deployment:** Same Mac Studio vs separate?
   - Recommendation: **Same Mac Studio**, serve via Mode Service or gateway

10. **Guest Name Extraction:** Parse from iCal summary or leave null?
    - Recommendation: **Attempt to parse, but don't rely on it** (Airbnb may not include)

---

## Conclusion

This plan provides a complete, implementable design for **Guest Mode, permission scoping, and quality tracking** that integrates seamlessly with the new Project Athena architecture.

**Key Benefits:**
- ✅ **Automatic guest mode** via Airbnb calendar (no manual work)
- ✅ **Privacy-first** with PII scrubbing and auto-purge
- ✅ **Configurable security** with YAML-based policy
- ✅ **Comprehensive tracking** with metrics, dashboards, and feedback
- ✅ **Continuous improvement** via nightly analysis and suggestions
- ✅ **Great guest UX** with voice control + SMS/email sharing
- ✅ **Owner visibility** with admin UI and HA integration

**Next Steps:**
1. Review and approve plan
2. Prioritize phases (recommend Mode Service → Policy → Integration → Feedback → UI)
3. Begin Phase 1 implementation
4. Iterate based on testing and feedback

All components are **clean, modular, and maintainable**, fitting naturally into the existing Mac Studio/mini architecture with Docker Compose deployment.
