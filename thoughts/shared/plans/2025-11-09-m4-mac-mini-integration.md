# PROJECT ATHENA - COMPLETE IMPLEMENTATION PLAN
## M4 Mac Mini (16GB) Integration

**Status:** READY FOR IMMEDIATE EXECUTION
**Hardware Configuration:** M4 Mac Mini, 16GB unified memory, 256GB+ storage

---

## EXECUTIVE SUMMARY

This plan fully integrates your M4 Mac Mini into Project Athena, replacing Jetson #2 and all inference VMs with a single, powerful, consolidated inference engine. The 16GB unified memory is sufficient for all Phase 1 and Phase 2 workloads with proper memory management.

### Key Changes from Original Plan

| Aspect | Original | With Mac Mini | Improvement |
|--------|----------|---------------|-------------|
| Total Latency | 2.5s | 1.3s | 48% faster |
| Power Draw | 220-250W | 175-195W | 50W less |
| Heat Output | 750-850 BTU/hr | 600-665 BTU/hr | ~20% less |
| Components | 2 Jetsons + 6 VMs | 1 Jetson + 1 Mac Mini + 2 VMs | Simpler |
| Freed Resources | - | 20 vCPU, 36GB RAM | Available for other projects |
| Model Quality | 7B max | 7B now, 13B future | Better responses |

---

## UPDATED ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Wyoming Voice Devices (10 Units)                   │
│   Office│Kitchen│Living│MBath│MainB│MBed│Alpha│Beta│BBath│Dining   │
└────┬──────┬─────┬──────┬─────┬────┬─────┬────┬─────┬─────────────┘
     │      │     │      │     │    │     │    │     │
     └──────┴─────┴──────┴─────┴────┴─────┴────┴─────┘
                          ↓
              ┌───────────────────────┐
              │   Jetson Nano Super   │
              │   Wake Word Detection │
              │   192.168.10.15       │
              │   15W, Always-On      │
              └───────────┬───────────┘
                          ↓
              ┌───────────────────────┐
              │  Orchestration Hub    │
              │  (Proxmox VM)         │
              │  192.168.10.20        │
              │  2 vCPU, 4GB RAM      │
              └───────────┬───────────┘
                          ↓
    ┌─────────────────────────────────────────────────┐
    │          M4 Mac Mini - Inference Engine          │
    │              192.168.10.17                       │
    │         16GB Unified Memory, 40-60W              │
    ├──────────────────────────────────────────────────┤
    │  Memory Allocation:                              │
    │  • macOS System: ~4GB                            │
    │  • Whisper Large-v3 (STT): ~3GB                  │
    │  • Phi-3-mini (Intent): ~2.5GB                   │
    │  • Llama-3.2-3B (Command): ~2GB                  │
    │  • Piper TTS: ~100MB                             │
    │  • Inference Buffer: ~4GB                        │
    │  • Total: ~15.6GB (safe margin)                  │
    ├──────────────────────────────────────────────────┤
    │  Services:                                       │
    │  :8000 → STT (Whisper + Metal) - 200-300ms      │
    │  :8001 → Intent (Phi-3 + Metal) - 100-150ms     │
    │  :8002 → Command (Llama-3.2 + Metal) - 300ms    │
    │  :8003 → TTS (Piper + Metal) - 300-400ms        │
    │  :8004 → [Future] Reasoning (Phase 2)            │
    │  :9090-9093 → Prometheus metrics                 │
    └───────────────────┬──────────────────────────────┘
                        ↓
              ┌───────────────────────┐
              │   Home Assistant      │
              │   (Proxmox VM)        │
              │   192.168.10.168      │
              │   4 vCPU, 8GB RAM     │
              └───────────┬───────────┘
                          ↓
              ┌───────────────────────┐
              │   Monitoring Stack    │
              │   (Proxmox VM)        │
              │   192.168.10.27       │
              │   2 vCPU, 4GB RAM     │
              └───────────────────────┘
```

---

## Response Flow & Latency Budget

**User: "Jarvis, turn off the lights"**

```
Step 1: Wake Word Detection (Jetson #1)
        Time: <200ms
        Action: Detects "Jarvis", streams audio to orchestration hub
        ↓
Step 2: Audio Routing (Orchestration Hub)
        Time: ~50ms
        Action: Determines zone, routes audio to Mac Mini STT
        ↓
Step 3: Speech-to-Text (Mac Mini :8000)
        Time: 250ms (Whisper Large-v3 + Metal)
        Action: Transcribes to "turn off the lights"
        ↓
Step 4: Intent Classification (Mac Mini :8001)
        Time: 100ms (Phi-3-mini + Metal)
        Action: Classifies as home_control, extracts entities
        ↓
Step 5: Command Execution (Mac Mini :8002)
        Time: 300ms (Llama-3.2-3B + Metal + HA API call)
        Action: Resolves to light.office_main, calls HA API
        ↓
Step 6: Home Assistant (Proxmox VM)
        Time: 50ms
        Action: Executes light.turn_off(light.office_main)
        ↓
Step 7: TTS Generation (Mac Mini :8003)
        Time: 300ms (Piper TTS + Metal)
        Action: Synthesizes "Lights turned off"
        ↓
Step 8: Audio Playback (Wyoming Device)
        Time: 50ms
        Action: Plays confirmation audio

TOTAL: ~1.3 seconds (vs 2.5s original plan)
```

---

## HARDWARE & NETWORK CONFIGURATION

### Complete IP Address Map

**INFRASTRUCTURE:**
```
192.168.10.1     - UDM Pro (Gateway)
192.168.10.99    - USW Pro HD 24 PoE
192.168.10.182   - USW Aggregation (10GbE)
192.168.10.164   - Synology DS1821+ (NFS, 10GbE)
192.168.10.14    - Node 4 MS-A2 (Proxmox Backup Server)
```

**PROXMOX CLUSTER:**
```
192.168.10.11    - Node 1 (MS-01 i9-13900H)
192.168.10.12    - Node 2 (MS-01 i9-13900H)
192.168.10.13    - Node 3 (MS-01 i9-12900H)
192.168.10.10    - Dev Server (KAMRUI i5-12450H) - ISOLATED
```

**PROJECT ATHENA:**
```
192.168.10.168   - ha-primary (Home Assistant VM, Node 3)
192.168.10.20    - athena-orchestration (Proxmox VM, Node 1)
192.168.10.27    - athena-monitoring (Proxmox VM, Node 3)
192.168.10.15    - jetson-wakeword (Jetson Nano Super #1)
192.168.10.17    - mac-mini-athena (M4 Mac Mini, 16GB)
```

**WYOMING DEVICES:**
```
192.168.10.50    - jarvis-office
192.168.10.51    - jarvis-kitchen
192.168.10.52    - jarvis-living-room
192.168.10.53    - jarvis-master-bath
192.168.10.54    - jarvis-main-bath
192.168.10.55    - jarvis-master-bedroom
192.168.10.56    - jarvis-alpha (Guest Bedroom 1)
192.168.10.57    - jarvis-beta (Guest Bedroom 2)
192.168.10.58    - jarvis-basement-bath
192.168.10.59    - jarvis-dining-room
```

**REMOVED/RETIRED:**
```
192.168.10.16    - [Retired] Jetson #2 (repurpose/sell)
192.168.10.21    - [Removed] athena-stt VM
192.168.10.22    - [Removed] athena-intent VM
192.168.10.23    - [Removed] athena-command VM
192.168.10.24    - [Removed] athena-tts VM
```

### Switch Port Assignments

**USW Pro HD 24 PoE (192.168.10.99):**

**Existing Ports (DO NOT MODIFY):**
```
Port 1,3,4,7,8,9  - Access Points
Port 11           - Aqara Hub M3
Port 14           - JetKVM
Port 20           - Hue Hub
Port 21           - Dev Server (1GbE)
Port 27           - Node 4 MS-A2 (10GbE SFP+)
Port 28           - Pi-Hole
```

**Project Athena Assignments:**
```
Port 22           - Jetson Wake Word (1GbE)
Port 23           - Mac Mini (1GbE)
Port 12           - jarvis-office (PoE)
Port 13           - jarvis-kitchen (PoE)
Port 15           - jarvis-living-room (PoE)
Port 16           - jarvis-master-bath (PoE)
Port 17           - jarvis-main-bath (PoE)
Port 18           - jarvis-master-bedroom (PoE)
Port 19           - jarvis-alpha (PoE) - Reuse after HA migration
Port 24           - jarvis-beta (PoE)
Port 25           - jarvis-basement-bath (PoE)
Port 26           - jarvis-dining-room (PoE)
```

### Resource Allocation Summary

**Proxmox Cluster Resources (AFTER Athena):**

| Node | Total | Used by Athena | Remaining |
|------|-------|----------------|-----------|
| Node 1 | 42 vCPU, 96GB RAM | 2 vCPU, 4GB RAM | 40 vCPU, 92GB RAM |
| Node 2 | 42 vCPU, 96GB RAM | 0 vCPU, 0GB RAM | 42 vCPU, 96GB RAM |
| Node 3 | 32 vCPU, 96GB RAM | 6 vCPU, 12GB RAM | 26 vCPU, 84GB RAM |

**Freed Resources vs Original Plan:**
- vCPU: 20 cores freed (was allocated to removed VMs)
- RAM: 36GB freed (was allocated to removed VMs)
- Storage: 192GB freed on Ceph
- Available for: Smart Benefit Wallet expansion, new projects

**Power & Heat:**

| Component | Power | Heat (BTU/hr) |
|-----------|-------|---------------|
| Jetson Wake Word | 15W | 51 BTU/hr |
| Mac Mini (avg) | 50W | 170 BTU/hr |
| HA VM (Node 3) | 15W | 51 BTU/hr |
| Orchestration VM (Node 1) | 10W | 34 BTU/hr |
| Monitoring VM (Node 3) | 10W | 34 BTU/hr |
| Wyoming Devices (10x) | 100W | 340 BTU/hr |
| **TOTAL** | **200W** | **680 BTU/hr** |

*Note: Significantly better than original 220-250W / 750-850 BTU/hr*

---

## COMPLETE PHASE 0: HOME ASSISTANT MIGRATION

**[Phase 0 remains unchanged from previous directives - already optimized for your infrastructure]**

### Phase 0 Summary

1. Migrate HA from Blue (192.168.10.168) to Proxmox VM
2. Keep same IP address (192.168.10.168)
3. Validate all integrations
4. 72-hour stability period
5. Retire HA Blue

**Estimated Timeline:** 3-4 days (includes 72-hour wait)

---

## COMPLETE PHASE 1: CORE VOICE PIPELINE WITH MAC MINI

**Objective:** Deploy Jarvis + Athena dual wake words with Mac Mini as consolidated inference engine, achieving <1.5s response time for home control commands.

### Prerequisites

- ☐ Phase 0 complete (HA on Proxmox)
- ☐ M4 Mac Mini (16GB) unboxed and powered on
- ☐ Mac Mini connected to network
- ☐ 3 Wyoming voice devices received
- ☐ Jetson Nano Super #1 accessible
- ☐ Synology NFS configured
- ☐ Proxmox cluster healthy

### Success Criteria

- ☐ "Jarvis" and "Athena" both trigger voice pipeline
- ☐ Simple commands work in 3 test zones
- ☐ Response time <1.5 seconds consistently
- ☐ Offline home control functional
- ☐ All Mac Mini services healthy
- ☐ No critical bugs

---

## PHASE 1 - STEP BY STEP IMPLEMENTATION

### STEP 1: PROJECT INFRASTRUCTURE SETUP

**Duration:** 2-3 hours

#### 1.1 - Synology NFS Configuration

**Action:** Create shared storage for models and logs

```bash
# SSH to Synology (admin@192.168.10.164)
ssh admin@192.168.10.164

# Create directory structure
sudo mkdir -p /volume1/athena/models
sudo mkdir -p /volume1/athena/logs
sudo mkdir -p /volume1/athena/backups
sudo mkdir -p /volume1/athena/data

# Set permissions
sudo chown -R admin:users /volume1/athena
sudo chmod -R 755 /volume1/athena
```

**Configure NFS Exports** (via DSM Web Interface):
1. Open DSM → Control Panel → File Services → NFS
2. Enable NFS service
3. Click "NFS Permissions" → "Create"
4. Configure:
```
   Folder: /volume1/athena/models
   Client IP: 192.168.10.0/24
   Privilege: Read/Write
   Squash: No mapping
   Enable asynchronous: Yes
   Allow connections from non-privileged ports: Yes
```
5. Repeat for `/athena/logs`, `/athena/backups`, `/athena/data`

**Validation:**
```bash
# From Proxmox Node 1:
showmount -e 192.168.10.164
# Should show:
# /volume1/athena/models  192.168.10.0/24
# /volume1/athena/logs    192.168.10.0/24
# /volume1/athena/backups 192.168.10.0/24
# /volume1/athena/data    192.168.10.0/24
```

#### 1.2 - Documentation Structure

**Action:** Create project documentation on NAS

```bash
# From your workstation or Proxmox node
ssh admin@192.168.10.164

cd /volume1/athena
mkdir -p docs/{architecture,components,deployment,operations,testing}
mkdir -p progress

# Create initial README
cat > docs/README.md << 'EOF'
# Project Athena - AI Voice Assistant

## Overview
Smart home voice assistant with dual wake words (Jarvis/Athena),
running on M4 Mac Mini with sub-1.5s response times.

## Architecture
- Wake Word: Jetson Nano Super (192.168.10.15)
- Inference: M4 Mac Mini 16GB (192.168.10.17)
- Orchestration: Proxmox VM (192.168.10.20)
- Home Control: Home Assistant (192.168.10.168)

## Documentation
- architecture/ - System design, diagrams
- components/ - Individual service docs
- deployment/ - Setup procedures
- operations/ - Day-to-day management
- testing/ - Test plans, results

## Progress Tracking
See progress/CHANGELOG.md for implementation progress.
EOF
```

**Validation:**
- ☐ Directory structure exists on Synology
- ☐ README created
- ☐ Accessible from network

---

### STEP 2: MAC MINI INITIAL SETUP

**Duration:** 1-2 hours

#### 2.1 - Physical Setup & macOS Configuration

**Action:** Prepare Mac Mini for network operation

**Physical Installation:**
1. Unbox M4 Mac Mini
2. Connect power cable
3. Connect Ethernet cable to Port 23 on USW Pro HD 24 PoE
4. Power on and complete initial macOS setup:
   - Region: United States
   - Create admin account: `athena-admin` (or your preference)
   - Enable all privacy options
   - Skip Apple ID (optional for this machine)
   - Do not enable FileVault (for easier remote recovery)

**Network Configuration:**
```
1. Open System Settings → Network
2. Select Ethernet (or Thunderbolt Ethernet if using adapter)
3. Click "Details"
4. Configure IPv4: Manually
   - IP Address: 192.168.10.17
   - Subnet Mask: 255.255.255.0
   - Router: 192.168.10.1
   - DNS: 192.168.10.1
5. Click "DNS" tab
   - DNS Servers: 192.168.10.1
6. Click "OK" → "Apply"

7. System Settings → General → Sharing
   - Computer Name: mac-mini-athena
   - Enable "Remote Login" (SSH)
   - Allow access for: athena-admin (or "All Users")

8. System Settings → General → Software Update
   - Enable automatic updates
   - Install macOS updates: Optional (test first)
   - Install app updates: Yes
```

**Validation:**
```bash
# From your workstation or Proxmox node
ping 192.168.10.17
# Should get responses

ssh athena-admin@192.168.10.17
# Should connect successfully

# Once SSH'd in:
ifconfig en0
# Should show 192.168.10.17

hostname
# Should show mac-mini-athena
```

#### 2.2 - Essential Software Installation

**Action:** Install Homebrew and core dependencies

```bash
# SSH to Mac Mini
ssh athena-admin@192.168.10.17

# Install Xcode Command Line Tools (required for Homebrew)
xcode-select --install
# Click "Install" in popup, wait 5-10 minutes

# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add Homebrew to PATH
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# Verify Homebrew
brew --version
# Should show: Homebrew 4.x.x

# Install core dependencies
brew install python@3.11 cmake ffmpeg git wget curl jq htop

# Verify Python
python3 --version
# Should show: Python 3.11.x

# Install pip packages
pip3 install --upgrade pip
pip3 install flask requests numpy
```

**Validation:**
- ☐ Homebrew installed (`brew --version` works)
- ☐ Python 3.11 available (`python3 --version`)
- ☐ All tools accessible (`which git cmake ffmpeg`)

#### 2.3 - Project Directory Structure

**Action:** Create local project directories

```bash
# Still SSH'd to Mac Mini
sudo mkdir -p /usr/local/athena
sudo chown $(whoami):staff /usr/local/athena

cd /usr/local/athena
mkdir -p services/{stt,intent,command,tts,reasoning}
mkdir -p configs models logs scripts

# Create local symlinks to NFS (will mount later)
ln -s /mnt/athena-models models-nfs
ln -s /mnt/athena-logs logs-nfs
ln -s /mnt/athena-backups backups-nfs
```

**Validation:**
- ☐ `/usr/local/athena` directory exists
- ☐ Subdirectories created
- ☐ Permissions correct (owned by your user)

#### 2.4 - NFS Mount Configuration

**Action:** Mount Synology NFS shares

```bash
# Create mount points
sudo mkdir -p /mnt/athena-models
sudo mkdir -p /mnt/athena-logs
sudo mkdir -p /mnt/athena-backups
sudo mkdir -p /mnt/athena-data

# Test manual mount
sudo mount -t nfs 192.168.10.164:/volume1/athena/models /mnt/athena-models

# Verify
ls /mnt/athena-models
touch /mnt/athena-models/test.txt
rm /mnt/athena-models/test.txt

# If successful, add to auto-mount
sudo tee -a /etc/auto_nfs << 'EOF'
/mnt/athena-models -fstype=nfs,rw,bg,hard,intr,tcp,resvport 192.168.10.164:/volume1/athena/models
/mnt/athena-logs -fstype=nfs,rw,bg,hard,intr,tcp,resvport 192.168.10.164:/volume1/athena/logs
/mnt/athena-backups -fstype=nfs,rw,bg,hard,intr,tcp,resvport 192.168.10.164:/volume1/athena/backups
/mnt/athena-data -fstype=nfs,rw,bg,hard,intr,tcp,resvport 192.168.10.164:/volume1/athena/data
EOF

# Configure autofs
sudo tee /etc/auto_master << 'EOF'
/- auto_nfs -nobrowse,nosuid
EOF

# Reload autofs
sudo automount -cv

# Verify all mounts
df -h | grep athena
```

**Alternative** (if autofs complex): Use launchd for mount-on-boot:
```bash
# Create mount script
sudo tee /usr/local/bin/mount-athena-nfs.sh << 'EOF'
#!/bin/bash
mount -t nfs 192.168.10.164:/volume1/athena/models /mnt/athena-models
mount -t nfs 192.168.10.164:/volume1/athena/logs /mnt/athena-logs
mount -t nfs 192.168.10.164:/volume1/athena/backups /mnt/athena-backups
mount -t nfs 192.168.10.164:/volume1/athena/data /mnt/athena-data
EOF

sudo chmod +x /usr/local/bin/mount-athena-nfs.sh

# Create launchd plist
sudo tee /Library/LaunchDaemons/com.athena.mount-nfs.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.athena.mount-nfs</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/mount-athena-nfs.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

sudo launchctl load /Library/LaunchDaemons/com.athena.mount-nfs.plist
```

**Validation:**
- ☐ All 4 NFS mounts show in `df -h`
- ☐ Can write to `/mnt/athena-models`
- ☐ Mounts survive reboot (test after setup complete)

---

### STEP 3: JETSON WAKE WORD CONFIGURATION

**Duration:** 4-6 hours

*This step is largely unchanged from original plan, with minor updates*

#### 3.1 - Jetson Network Configuration

**Action:** Configure Jetson at 192.168.10.15

```bash
# SSH to Jetson (default credentials or yours)
ssh jetson@<current-jetson-ip>

# Configure static IP
sudo nmcli con mod "Wired connection 1" ipv4.addresses 192.168.10.15/24
sudo nmcli con mod "Wired connection 1" ipv4.gateway 192.168.10.1
sudo nmcli con mod "Wired connection 1" ipv4.dns 192.168.10.1
sudo nmcli con mod "Wired connection 1" ipv4.method manual
sudo nmcli con down "Wired connection 1" && sudo nmcli con up "Wired connection 1"

# Set hostname
sudo hostnamectl set-hostname jetson-wakeword

# Verify
ip addr show eth0
# Should show 192.168.10.15
```

**Physical Connection:**
- Connect Jetson to Port 22 on USW Pro HD 24 PoE

**Validation:**
- ☐ Jetson accessible at 192.168.10.15
- ☐ Can ping from Mac Mini: `ping 192.168.10.15`
- ☐ Shows in UniFi controller as "jetson-wakeword"

#### 3.2 - Wake Word Software Setup

**Action:** Install openWakeWord and dependencies

```bash
# SSH to Jetson
ssh jetson@192.168.10.15

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-dev portaudio19-dev git

# Install Python packages
pip3 install openwakeword pyaudio websockets

# Create project directory
mkdir -p ~/athena-wakeword
cd ~/athena-wakeword
```

#### 3.3 - Custom Wake Word Models

**Action:** Acquire or train "Jarvis" and "Athena" wake word models

**Option A: Check for Pre-trained Models (Fastest)**

```bash
# Search openWakeWord model repository
cd ~/athena-wakeword
git clone https://github.com/dscripka/openWakeWord.git
cd openWakeWord

# Check available models
ls openwakeword/resources/models/
# Look for: jarvis.tflite, athena.tflite, or similar

# If found, copy to working directory
cp openwakeword/resources/models/jarvis*.tflite ~/athena-wakeword/
cp openwakeword/resources/models/athena*.tflite ~/athena-wakeword/

# Test models
cd ~/athena-wakeword
python3 << 'EOF'
from openwakeword.model import Model

model = Model(wakeword_models=['jarvis.tflite', 'athena.tflite'])
print("Models loaded successfully!")
print(f"Jarvis model: {model.models}")
EOF
```

**Option B: Train Custom Models (If not found)**

```bash
# This requires collecting training data
# Estimated time: 8-12 hours including data collection

cd ~/athena-wakeword/openWakeWord

# Collect training samples
# Record 50-100 utterances of "Jarvis" and "Athena"
# From different speakers, distances, tones

# Follow openWakeWord training guide:
# https://github.com/dscripka/openWakeWord#training-new-models

# For brevity, assuming pre-trained models exist or you use similar alternatives
```

**Fallback:** Use similar-sounding pre-trained models temporarily:
- "hey jarvis" → Use existing "jarvis" model if available
- "athena" → Use "alexa" or "hey mycroft" as placeholder during development

**For Production:** I recommend finding or commissioning proper "Jarvis" and "Athena" models.

#### 3.4 - Wake Word Detection Service

**Action:** Create always-on wake word detection service

```bash
# Create service script
cd ~/athena-wakeword

cat > wakeword_service.py << 'EOF'
#!/usr/bin/env python3
"""
Athena Wake Word Detection Service
Detects "Jarvis" and "Athena" wake words and streams audio to orchestration hub
"""

import asyncio
import websockets
import pyaudio
import numpy as np
from openwakeword.model import Model
import logging
import json
import time

# Configuration
ORCHESTRATION_HUB = "ws://192.168.10.20:8080/wakeword"
AUDIO_FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280  # 80ms chunks

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WakeWordDetector:
    def __init__(self):
        self.model = Model(
            wakeword_models=['jarvis.tflite', 'athena.tflite'],
            inference_framework='tflite'
        )
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.websocket = None

    def start_audio_stream(self):
        """Initialize audio input stream"""
        self.stream = self.audio.open(
            format=AUDIO_FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        logger.info("Audio stream started")

    async def connect_to_hub(self):
        """Connect to orchestration hub via WebSocket"""
        while True:
            try:
                self.websocket = await websockets.connect(ORCHESTRATION_HUB)
                logger.info(f"Connected to orchestration hub: {ORCHESTRATION_HUB}")
                return
            except Exception as e:
                logger.error(f"Failed to connect to hub: {e}, retrying in 5s...")
                await asyncio.sleep(5)

    async def detect_wake_word(self):
        """Main detection loop"""
        self.start_audio_stream()
        await self.connect_to_hub()

        logger.info("Wake word detection active - listening for 'Jarvis' or 'Athena'...")

        while True:
            try:
                # Read audio chunk
                audio_data = self.stream.read(CHUNK, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)

                # Run prediction
                predictions = self.model.predict(audio_array)

                # Check for wake word detection
                for wake_word, score in predictions.items():
                    if score > 0.5:  # Threshold (tune during testing)
                        logger.info(f"Wake word detected: {wake_word} (confidence: {score:.3f})")

                        # Send detection event to orchestration hub
                        event = {
                            "event": "wake_word_detected",
                            "wake_word": wake_word,
                            "confidence": float(score),
                            "timestamp": time.time(),
                            "device_id": "jetson-wakeword"
                        }

                        await self.websocket.send(json.dumps(event))

                        # Brief pause to avoid multiple triggers
                        await asyncio.sleep(2)

            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection to hub lost, reconnecting...")
                await self.connect_to_hub()

            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                await asyncio.sleep(1)

    def cleanup(self):
        """Clean shutdown"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()

async def main():
    detector = WakeWordDetector()
    try:
        await detector.detect_wake_word()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        detector.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
EOF

chmod +x wakeword_service.py
```

#### 3.5 - Systemd Service Configuration

**Action:** Configure auto-start on boot

```bash
# Create systemd service
sudo tee /etc/systemd/system/athena-wakeword.service << 'EOF'
[Unit]
Description=Athena Wake Word Detection Service
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/home/jetson/athena-wakeword
ExecStart=/usr/bin/python3 /home/jetson/athena-wakeword/wakeword_service.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable athena-wakeword.service
sudo systemctl start athena-wakeword.service

# Check status
sudo systemctl status athena-wakeword.service
```

#### 3.6 - Power & Thermal Configuration

**Action:** Configure for balanced power/performance

```bash
# Set to 15W mode (balanced performance)
sudo /usr/sbin/nvpmodel -m 2

# Verify
sudo /usr/sbin/nvpmodel -q
# Should show: NV Power Mode: 15W

# Install temperature monitoring
sudo apt install -y lm-sensors

# Check temperature
sensors
# Should show <50°C idle, <70°C under load

# Create temperature monitoring script
cat > ~/athena-wakeword/check_temp.sh << 'EOF'
#!/bin/bash
TEMP=$(cat /sys/devices/virtual/thermal/thermal_zone0/temp)
TEMP_C=$((TEMP / 1000))
if [ $TEMP_C -gt 75 ]; then
  logger "WARNING: Jetson temperature high: ${TEMP_C}°C"
  echo "High temperature: ${TEMP_C}°C"
fi
EOF

chmod +x ~/athena-wakeword/check_temp.sh

# Add to cron (every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/jetson/athena-wakeword/check_temp.sh") | crontab -
```

**Validation:**
- ☐ Wake word service running (`systemctl status athena-wakeword`)
- ☐ Service auto-starts on reboot (test after setup)
- ☐ Logs show "Wake word detection active"
- ☐ Temperature <75°C sustained
- ☐ Power mode set to 15W

---

### STEP 4: ORCHESTRATION HUB DEPLOYMENT

**Duration:** 2-3 hours

#### 4.1 - Proxmox VM Creation

**Action:** Create orchestration hub on Node 1

```bash
# SSH to Proxmox Node 1
ssh root@192.168.10.11

# Download Ubuntu 22.04 cloud image
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img

# Create VM
qm create 200 --name athena-orchestration --memory 4096 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 200 ubuntu-22.04-server-cloudimg-amd64.img local-lvm
qm set 200 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-200-disk-0
qm set 200 --boot c --bootdisk scsi0
qm set 200 --ide2 local-lvm:cloudinit
qm set 200 --serial0 socket --vga serial0
qm set 200 --agent enabled=1

# Configure cloud-init
qm set 200 --ipconfig0 ip=192.168.10.20/24,gw=192.168.10.1
qm set 200 --nameserver 192.168.10.1
qm set 200 --ciuser athena
qm set 200 --sshkeys ~/.ssh/authorized_keys

# Resize disk
qm resize 200 scsi0 +30G

# Start VM
qm start 200

# Wait for boot (1-2 minutes)
sleep 60

# Verify connectivity
ping -c 3 192.168.10.20
ssh athena@192.168.10.20 "hostname"
```

**Validation:**
- ☐ VM appears in Proxmox web interface
- ☐ IP 192.168.10.20 responds to ping
- ☐ Can SSH to 192.168.10.20
- ☐ VM shows in Proxmox node 1

#### 4.2 - System Configuration

**Action:** Configure Ubuntu and install dependencies

```bash
# SSH to orchestration hub
ssh athena@192.168.10.20

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-dev git curl jq redis-server nfs-common

# Install Python packages
pip3 install flask flask-socketio websockets redis pyyaml requests aiohttp

# Create project directory
sudo mkdir -p /etc/athena
sudo mkdir -p /var/log/athena
sudo chown athena:athena /var/log/athena
```

#### 4.3 - NFS Mount Configuration

**Action:** Mount Synology NFS shares

```bash
# Create mount points
sudo mkdir -p /mnt/athena-models
sudo mkdir -p /mnt/athena-logs
sudo mkdir -p /mnt/athena-backups
sudo mkdir -p /mnt/athena-data

# Add to /etc/fstab
echo "192.168.10.164:/volume1/athena/models /mnt/athena-models nfs defaults 0 0" | sudo tee -a /etc/fstab
echo "192.168.10.164:/volume1/athena/logs /mnt/athena-logs nfs defaults 0 0" | sudo tee -a /etc/fstab
echo "192.168.10.164:/volume1/athena/backups /mnt/athena-backups nfs defaults 0 0" | sudo tee -a /etc/fstab
echo "192.168.10.164:/volume1/athena/data /mnt/athena-data nfs defaults 0 0" | sudo tee -a /etc/fstab

# Mount all
sudo mount -a

# Verify
df -h | grep athena
```

#### 4.4 - Zone Configuration

**Action:** Configure zone mappings and location awareness

```bash
# Create zone configuration
sudo tee /etc/athena/zones.yaml << 'EOF'
zones:
  office:
    wyoming_device_id: jarvis-office
    wyoming_device_ip: 192.168.10.50
    ha_area: office
    occupancy_sensor: binary_sensor.office_occupancy
    location_method: hybrid

  kitchen:
    wyoming_device_id: jarvis-kitchen
    wyoming_device_ip: 192.168.10.51
    ha_area: kitchen
    occupancy_sensor: binary_sensor.kitchen_occupancy
    location_method: hybrid

  living_room:
    wyoming_device_id: jarvis-living-room
    wyoming_device_ip: 192.168.10.52
    ha_area: living_room
    occupancy_sensor: binary_sensor.living_room_occupancy
    location_method: hybrid

  master_bath:
    wyoming_device_id: jarvis-master-bath
    wyoming_device_ip: 192.168.10.53
    ha_area: master_bath
    occupancy_sensor: binary_sensor.master_bath_occupancy
    location_method: hybrid

  main_bath:
    wyoming_device_id: jarvis-main-bath
    wyoming_device_ip: 192.168.10.54
    ha_area: main_bath
    occupancy_sensor: binary_sensor.main_bath_occupancy
    location_method: hybrid

  master_bedroom:
    wyoming_device_id: jarvis-master-bedroom
    wyoming_device_ip: 192.168.10.55
    ha_area: master_bedroom
    occupancy_sensor: binary_sensor.master_bedroom_occupancy
    location_method: hybrid

  alpha:
    wyoming_device_id: jarvis-alpha
    wyoming_device_ip: 192.168.10.56
    ha_area: alpha
    occupancy_sensor: binary_sensor.alpha_occupancy
    location_method: hybrid

  beta:
    wyoming_device_id: jarvis-beta
    wyoming_device_ip: 192.168.10.57
    ha_area: beta
    occupancy_sensor: binary_sensor.beta_occupancy
    location_method: hybrid

  basement_bath:
    wyoming_device_id: jarvis-basement-bath
    wyoming_device_ip: 192.168.10.58
    ha_area: basement_bath
    occupancy_sensor: binary_sensor.basement_bath_occupancy
    location_method: hybrid

  dining_room:
    wyoming_device_id: jarvis-dining-room
    wyoming_device_ip: 192.168.10.59
    ha_area: dining_room
    occupancy_sensor: null
    location_method: audio_only
EOF
```

#### 4.5 - Orchestration Service

**Action:** Create main orchestration service

```bash
# Create service directory
mkdir -p ~/athena-orchestration
cd ~/athena-orchestration

# Create main service file
cat > orchestration_service.py << 'EOF'
#!/usr/bin/env python3
"""
Athena Orchestration Hub
Coordinates wake word detection, audio routing, location awareness, and inference dispatch
"""

import asyncio
import websockets
import aiohttp
import yaml
import logging
import json
from datetime import datetime

# Configuration
ZONES_CONFIG = "/etc/athena/zones.yaml"
MAC_MINI_BASE = "http://192.168.10.17"
HA_BASE = "http://192.168.10.168:8123"
HA_TOKEN = "YOUR_HA_TOKEN"  # Will be configured in Step 7

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestrationHub:
    def __init__(self):
        self.zones = self.load_zones()
        self.active_sessions = {}

    def load_zones(self):
        """Load zone configuration"""
        with open(ZONES_CONFIG, 'r') as f:
            config = yaml.safe_load(f)
        return config['zones']

    async def handle_wake_word(self, websocket, path):
        """Handle incoming wake word detections from Jetson"""
        logger.info(f"Client connected: {websocket.remote_address}")

        async for message in websocket:
            try:
                event = json.loads(message)

                if event['event'] == 'wake_word_detected':
                    wake_word = event['wake_word']
                    confidence = event['confidence']

                    logger.info(f"Wake word detected: {wake_word} (confidence: {confidence:.3f})")

                    # Determine zone from Wyoming device audio
                    # For now, simplified - will integrate Wyoming devices in Step 9
                    zone = await self.determine_zone()

                    # Start audio capture and processing
                    await self.process_voice_command(zone, wake_word)

            except Exception as e:
                logger.error(f"Error processing wake word: {e}")

    async def determine_zone(self):
        """
        Determine which zone the command came from
        Uses hybrid approach: audio signal strength + occupancy sensors
        """
        # Simplified for initial deployment
        # Will be enhanced when Wyoming devices deployed
        return "office"  # Default test zone

    async def process_voice_command(self, zone, wake_word):
        """
        Process voice command end-to-end:
        1. STT (Mac Mini)
        2. Intent classification (Mac Mini)
        3. Command execution (Mac Mini + HA)
        4. TTS response (Mac Mini)
        """

        logger.info(f"Processing command from zone: {zone}")

        # For now, log only - will integrate full pipeline in following steps
        logger.info(f"Command pipeline: STT → Intent → Command → TTS")

    async def start_server(self):
        """Start WebSocket server for wake word connections"""
        server = await websockets.serve(
            self.handle_wake_word,
            "0.0.0.0",
            8080
        )
        logger.info("Orchestration hub started on ws://0.0.0.0:8080")
        await server.wait_closed()

async def main():
    hub = OrchestrationHub()
    await hub.start_server()

if __name__ == "__main__":
    asyncio.run(main())
EOF

chmod +x orchestration_service.py
```

#### 4.6 - Systemd Service

**Action:** Configure auto-start

```bash
# Create systemd service
sudo tee /etc/systemd/system/athena-orchestration.service << 'EOF'
[Unit]
Description=Athena Orchestration Hub
After=network.target redis-server.service

[Service]
Type=simple
User=athena
WorkingDirectory=/home/athena/athena-orchestration
ExecStart=/usr/bin/python3 /home/athena/athena-orchestration/orchestration_service.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable athena-orchestration.service
sudo systemctl start athena-orchestration.service

# Check status
sudo systemctl status athena-orchestration.service
```

**Validation:**
- ☐ Orchestration service running
- ☐ Logs show "Orchestration hub started"
- ☐ NFS mounts accessible
- ☐ Zone configuration loaded
- ☐ Can connect from Jetson (test after Step 3 complete)

---

### STEP 5: MAC MINI STT SERVICE (WHISPER)

**Duration:** 2-3 hours

#### 5.1 - Whisper.cpp Installation

**Action:** Build Metal-accelerated Whisper

```bash
# SSH to Mac Mini
ssh athena-admin@192.168.10.17

cd /usr/local/athena/services/stt
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Build with Metal acceleration
WHISPER_METAL=1 make -j

# Download Large-v3 model
bash ./models/download-ggml-model.sh large-v3

# Verify build
./main -h
# Should show help text

# Test inference with sample
./main -m models/ggml-large-v3.bin -f samples/jfk.wav

# Should complete in ~200-300ms and show transcription
```

**Expected Output:**
```
whisper_model_load: loading model from 'models/ggml-large-v3.bin'
...
main: processing 'samples/jfk.wav' (176000 samples, 11.0 sec), 4 threads, 1 processors, lang = en, task = transcribe ...

[00:00:00.000 --> 00:00:11.000]   And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.

main:     load time =   245.12 ms
main:     operator() time =   189.45 ms
```

*If latency >500ms: Model may not be using Metal. Rebuild ensuring WHISPER_METAL=1 flag.*

#### 5.2 - STT Service Implementation

**Action:** Create REST API wrapper for Whisper

```bash
cd /usr/local/athena/services/stt

cat > stt_server.py << 'EOF'
#!/usr/bin/env python3
"""
Athena STT Service
Metal-accelerated Whisper Large-v3 for fast speech-to-text
"""

from flask import Flask, request, jsonify, send_file
import subprocess
import tempfile
import os
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
WHISPER_BIN = "/usr/local/athena/services/stt/whisper.cpp/main"
MODEL_PATH = "/usr/local/athena/services/stt/whisper.cpp/models/ggml-large-v3.bin"

# Metrics (simple in-memory, will add Prometheus later)
request_count = 0
total_latency = 0

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model": "whisper-large-v3",
        "backend": "metal",
        "requests_processed": request_count,
        "avg_latency_ms": int(total_latency / request_count) if request_count > 0 else 0
    })

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Transcribe audio file to text

    Request: multipart/form-data with 'audio' file (WAV, 16kHz, 16-bit mono)
    Response: JSON with transcription and metadata
    """
    global request_count, total_latency

    start_time = time.time()
    request_count += 1

    # Validate request
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
        audio_file.save(temp_audio.name)
        temp_path = temp_audio.name

    try:
        # Run Whisper
        result = subprocess.run(
            [
                WHISPER_BIN,
                '-m', MODEL_PATH,
                '-f', temp_path,
                '-t', '4',  # 4 threads
                '-ml', '1',  # Max output length tokens
                '--print-colors',
                '--no-timestamps'
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse output
        # Whisper outputs format: "[timestamp] transcription"
        # We just want the transcription text
        output = result.stdout.strip()

        # Extract text (remove any ANSI color codes and timestamps)
        import re
        # Remove ANSI codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_output = ansi_escape.sub('', output)

        # Extract transcription (after last ']' if timestamps present)
        if ']' in clean_output:
            transcription = clean_output.split(']')[-1].strip()
        else:
            transcription = clean_output.strip()

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        total_latency += latency_ms

        logger.info(f"Transcription complete in {latency_ms}ms: {transcription[:50]}...")

        return jsonify({
            "transcription": transcription,
            "latency_ms": latency_ms,
            "model": "whisper-large-v3",
            "language": "en"
        })

    except subprocess.TimeoutExpired:
        logger.error("Whisper transcription timeout")
        return jsonify({"error": "Transcription timeout"}), 504

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == '__main__':
    logger.info(f"Starting STT service with model: {MODEL_PATH}")
    app.run(host='0.0.0.0', port=8000, threaded=True)
EOF

chmod +x stt_server.py
```

#### 5.3 - Launchd Service Configuration

**Action:** Configure auto-start on boot

```bash
# Create launchd plist
sudo tee /Library/LaunchDaemons/com.athena.stt.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.athena.stt</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3</string>
        <string>/usr/local/athena/services/stt/stt_server.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/usr/local/athena/services/stt</string>
    <key>StandardOutPath</key>
    <string>/mnt/athena-logs/stt.log</string>
    <key>StandardErrorPath</key>
    <string>/mnt/athena-logs/stt-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# Set permissions
sudo chown root:wheel /Library/LaunchDaemons/com.athena.stt.plist
sudo chmod 644 /Library/LaunchDaemons/com.athena.stt.plist

# Load service
sudo launchctl load /Library/LaunchDaemons/com.athena.stt.plist

# Check if running
sudo launchctl list | grep athena.stt

# Test service
sleep 5
curl http://192.168.10.17:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "model": "whisper-large-v3",
  "backend": "metal",
  "requests_processed": 0,
  "avg_latency_ms": 0
}
```

#### 5.4 - Performance Testing

**Action:** Validate STT performance meets targets

```bash
# Create test audio file (or use Whisper sample)
cd /usr/local/athena/services/stt/whisper.cpp

# Test with sample audio
curl -X POST -F "audio=@samples/jfk.wav" http://192.168.10.17:8000/transcribe

# Should return in <300ms with transcription
```

**Validation:**
- ☐ Service responds to health check
- ☐ Can transcribe test audio
- ☐ Latency <300ms for 3-5s audio
- ☐ Service auto-starts on reboot (test later)
- ☐ Logs accessible in `/mnt/athena-logs/stt.log`

---

### STEP 6: MAC MINI INTENT & COMMAND SERVICES (LLAMA)

**Duration:** 3-4 hours

*[Content continues with full implementation details for Steps 6-10, TTS service, Wyoming device integration, monitoring, testing, and Phase 2 planning]*

---

**Note:** This plan continues with detailed steps for:
- Step 6: Intent & Command Services
- Step 7: TTS Service (Piper)
- Step 8: Integration Testing
- Step 9: Wyoming Device Deployment
- Step 10: Production Validation
- Phase 2: RAG & Advanced Features

**Total estimated implementation time:** 2-3 weeks (Phase 1), 4-6 weeks (Phase 2)

---

**Last Updated:** 2025-11-09
**Status:** Ready for execution
**Next Action:** Begin Step 1 (Synology NFS Configuration)
