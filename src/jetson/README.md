# Jetson LLM Webhook Service

## Overview

Flask-based webhook service running on Jetson Orin Nano (192.168.10.62:5000) that processes voice commands with LLM intelligence.

## Components

- **llm_webhook_service.py** - Main Flask service with 3 endpoints
- **athena_lite.py** - Original Athena Lite voice pipeline
- **athena_lite_llm.py** - Enhanced version with LLM integration
- **config/** - Configuration files for HA integration

## Deployment

See [scripts/deployment/README.md](../../scripts/deployment/README.md) for deployment procedures.

## Current Deployment

- **Location:** `/mnt/nvme/athena-lite/` on jetson-01
- **Service:** Manual start (no systemd yet)
- **Port:** 5000
- **Status:** Operational but not production-ready
