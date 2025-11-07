# Project Athena - AI Voice Assistant

A next-generation AI voice assistant system designed for complete smart home integration with privacy-first, local processing.

## Quick Start

- **Documentation:** [Wiki Page](https://wiki.xmojo.net/homelab/projects/project-athena)
- **Setup Guide:** See [CLAUDE.md](CLAUDE.md) for development guidance
- **Current Status:** Athena Lite proof-of-concept ready for testing

## Key Features

- **Fast Response Times:** 2-5 second end-to-end response
- **100% Local Processing:** No cloud dependencies, complete privacy
- **Dual Wake Words:** "Jarvis" and "Athena" for different interaction modes
- **Multi-Zone Coverage:** 10 zones throughout the home
- **Home Assistant Integration:** Seamless device control

## Architecture

```
Wyoming Devices → Jetson → Proxmox Services → Home Assistant
    (10 zones)     (Wake)    (STT/TTS/LLM)    (Device Control)
```

## Current Implementation Status

### ✅ Completed
- **Athena Lite:** Proof-of-concept on jetson-01 (192.168.10.62)
- **Wake Word Detection:** Dual wake words (Jarvis + Athena)
- **Response Optimization:** 2.5-5 second response times
- **Home Assistant Integration:** API connectivity established

### 🔄 In Progress
- **Phase 1:** Core voice pipeline (3 test zones)
- **Wyoming Integration:** Protocol setup and device deployment

### 📋 Planned
- **Phase 2:** Full 10-zone deployment with RAG
- **Phase 3:** Learning and optimization
- **Phase 4:** Voice identification

## Hardware Requirements

- **2x NVIDIA Jetson Orin Nano Super** (wake word detection)
- **10x Wyoming Voice Devices** (microphone arrays per zone)
- **Proxmox Cluster** (STT, TTS, LLM processing)
- **Home Assistant** (device control hub)

## Directory Structure

```
project-athena/
├── src/
│   ├── jetson/                 # Jetson implementation
│   │   ├── llm_webhook_service.py
│   │   ├── athena_lite.py
│   │   ├── athena_lite_llm.py
│   │   └── config/
│   └── ha-integration/         # HA integration code
├── config/
│   ├── ha/                     # HA configuration fragments
│   ├── models.yaml             # AI model specifications
│   ├── network.yaml            # Network configuration
│   └── zones.yaml              # Zone definitions
├── scripts/
│   ├── deployment/             # Deployment automation
│   └── monitoring/             # Monitoring and health checks
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── docs/                       # Documentation
├── thoughts/                   # Research and plans
└── manifests/                  # Kubernetes manifests (future)
```

## Getting Started

1. **Review Documentation:** Read [CLAUDE.md](CLAUDE.md) and [Wiki](https://wiki.xmojo.net/homelab/projects/project-athena)
2. **Check Prerequisites:** Ensure access to jetson-01 and thor cluster
3. **Test Athena Lite:** Verify proof-of-concept functionality
4. **Plan Deployment:** Review phase implementation strategy

## Related Repositories

- **Homelab Infrastructure:** `/Users/jaystuart/dev/kubernetes/k8s-home-lab/`
- **Smart Benefit Wallet:** `/Users/jaystuart/dev/Monarch/`

## Resources

- **Wiki:** https://wiki.xmojo.net/homelab/projects/project-athena
- **Plane Project Management:** https://plane.xmojo.net
- **Home Assistant:** https://192.168.10.168:8123

---

**Maintained By:** Jay Stuart
**Last Updated:** November 3, 2025