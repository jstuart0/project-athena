# AGENTS.md - Project Athena

Guidance to AI agents working on Project Athena (voice assistant). Use this as the primary operator quick-reference. For full detail, see `CLAUDE.md`, `CONTINUATION_INSTRUCTIONS.md`, and `SESSION_HANDOFF.md`.

## Scope and Boundaries
- This repo is **Project Athena only** (voice assistant stack). Infrastructure lives in `/Users/jaystuart/dev/kubernetes/k8s-home-lab/`. Smart Benefit Wallet is in `/Users/jaystuart/dev/Monarch/`.
- Included: wake word (OpenWakeWord), STT (Faster-Whisper), TTS (Piper), LLMs (Phi-3, Llama-3.1), RAG, Wyoming integration, HA voice, orchestration, Kubernetes manifests, Jetson setup, monitoring/backups.
- Excluded: general homelab infra, cluster mgmt, DNS/SSL, non-voice apps.

## Hosts and Network (Phase 1)
- Mac Studio M4 64GB: `192.168.10.167` — gateway (8000), orchestrator (8001), RAG (8010-8012), Ollama (11434). Project path: `/Users/jaystuart/dev/project-athena/`.
- Mac mini M4 16GB: `192.168.10.181` — Qdrant `6333`, Redis `6379` (docker-compose deployment).
- Home Assistant: `192.168.10.168` / https://ha.xmojo.net.
- Jetson-01: `192.168.10.62` (Athena Lite archived). Jetson-02 planned at `192.168.10.63`.
- Planned Wyoming devices: `192.168.10.71-80` (10 zones).
- Thor k8s API: `192.168.10.222:6443`; private registry `192.168.10.222:30500` (amd64 images required).

## Credentials (stored in thor cluster, namespace `automation`)
- HA token/URL: `home-assistant-credentials` secret.
- Mac Studio access: `mac-studio-credentials` secret (SSH command, key, password).
- Project endpoints: `project-athena-credentials` secret (qdrant-url, redis-url, gateway-url).
- To fetch: `kubectl config use-context thor` then `kubectl -n automation get secret <name> -o jsonpath='{.data.<field>}' | base64 -d`.

## Current Status (from latest handoff)
- Phase 0: Complete.
- Phase 1 services: Mac Studio + Mac mini set up; admin interface built; deployment to thor pending image push.
- Phase 3 gateway: Configured and was running; needs verification after connectivity restoration.
- Phase 4 RAG services (weather/airports/sports): Implemented; deployment pending.
- Blockers noted: Mac Studio connectivity loss (restore network); Mac mini SSH may need enabling.

## Home Assistant Voice Integration (critical)
- Configure **OpenAI Conversation** via HA UI (not YAML):
  - Name: `Athena (Mac Studio)`; Base URL `http://192.168.10.167:8001/v1`; Model `athena-medium`; API key `sk-athena-9fd1ef6c8ed1eb0278f5133095c60271`; Max Tokens 500; Temp 0.7.
- Create Assist pipelines:
  - "Athena Control": STT Faster Whisper (`local_whisper`), conversation agent `athena-fast`, TTS Piper (`local_piper`).
  - "Athena Knowledge": STT Faster Whisper, agent `athena-medium`, TTS Piper.
- Test voice flows: device control, weather/sports/airport queries; target 2-5s end-to-end.

## Common Commands
- Switch context: `kubectl config use-context thor`.
- HA token: `kubectl -n automation get secret home-assistant-credentials -o jsonpath='{.data.long-lived-token}' | base64 -d`.
- Mac Studio SSH: `ssh jstuart@192.168.10.167` (passwordless expected).
- Check gateway locally (Mac Studio): `curl -s -X POST http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer <key>" -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'`.
- Deploy k8s services (thor): `kubectl apply -f manifests/athena-orchestration/` etc.; status: `kubectl -n athena get all`.
- Docker builds for thor: `docker buildx build --platform linux/amd64 -t 192.168.10.222:30500/<image>:tag . --push`.

## Phases and Tasks (abridged)
- Phase 1 (Core voice 3 zones): order/deploy 3 Wyoming devices, multi-zone routing on Jetson, deploy STT/TTS/LLM services on Proxmox, test pipeline.
- Phase 2 (Full 10 zones + RAG): add 7 devices, bring up jetson-02, deploy vector DB, integrate Phi-3/Llama-3.1, add context-aware responses.
- Phase 3: Learning/optimization. Phase 4: Voice identification.

## Verification and Testing
- Day 1 prerequisite check: `bash scripts/verify_day1.sh` (where applicable).
- Jetson Lite (archived): `ssh jstuart@192.168.10.62 "cd /mnt/nvme/athena-lite && python3 athena_lite.py --test"`.
- Mac mini services health: `curl http://192.168.10.181:6333/healthz`; `redis-cli -h 192.168.10.181 PING`.
- k8s health: `kubectl -n athena get pods`; logs: `kubectl -n athena logs -f deployment/athena-orchestration`.

## Notes for Agents
- Respect repo boundaries; do not touch homelab infra or unrelated projects.
- Build images for **amd64** before deploying to thor; avoid ARM images.
- If network to Mac Studio is down, restore connectivity before proceeding.
- Update wiki (`https://wiki.xmojo.net/homelab/projects/project-athena`) after major changes.
- For deeper task context, consult `thoughts/shared/` plans and research.

**Maintained by:** Jay Stuart — last synced from `CLAUDE.md` and handoff docs (Nov 2025)
