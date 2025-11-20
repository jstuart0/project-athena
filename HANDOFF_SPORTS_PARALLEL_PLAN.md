# Handoff: External API Keys + Parallel Sports RAG

## What changed in code
- Added `ExternalAPIKey` model and Alembic migration `012_add_external_api_keys.py` (admin backend).
- Added API routes for external API keys (CRUD + public service-to-service endpoint) and wired router into admin backend.
- Refactored `src/rag/sports/main.py` to:
  - Fetch API configs from Admin API (`/api/external-api-keys/public/{service_name}/key`) with env fallbacks.
  - Do parallel team search across TheSportsDB, ESPN, API-Football; provider-aware normalization of team IDs (`espn:<sport>:<id>`, `api-football:<id>`, numeric for TheSportsDB).
  - Provider-aware next/last events using the prefixed IDs.
- Admin frontend: added “External API Keys” tab with basic list/create/edit/delete calling the new backend routes.

## What still needs to be done (not possible under current sandbox)
1) Run migration on admin DB: `alembic upgrade head` (in `admin/backend`) to apply `012_add_external_api_keys.py`.
2) Seed external API keys (via new UI tab or API):
   - `thesportsdb`: endpoint `https://www.thesportsdb.com/api/v1/json/3` (or paid key endpoint/key).
   - `api-football`: endpoint `https://v3.football.api-sports.io`, real key.
   - `espn`: no key; optional endpoint override.
   - Enable = true.
3) Ensure sports RAG env has `ADMIN_API_URL` (and `SERVICE_API_KEY` if required by admin) set; keep port 8012.
4) Restart sports RAG service on 8012 and verify:
   - `curl http://localhost:8012/health`
   - `curl "http://localhost:8012/sports/teams/search?query=Ravens" | jq`
   - Use returned `idTeam` (prefixed) for `/sports/events/<id>/next`.
5) Re-test HA/gateway voice query: “what is the american football schedule for this week?” to confirm live data path instead of fallback.

## Risks/notes
- Admin DB migration is required or routes/model will 404/500.
- Admin API must be reachable from sports RAG for key fetch; otherwise it falls back to env keys.
- Orchestrator routing should point sports to 8012 (DB intent_routing or env `RAG_SPORTS_URL`).
- Team IDs are now provider-prefixed; callers should pass back the returned `idTeam` into events endpoints.
