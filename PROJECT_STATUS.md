# Project status and handoff

This file is the persistent handoff for contributors continuing hellotherelogs. Read it with `AGENTS.md` before implementation work, then update it when the project state changes.

## Product

hellotherelogs is a self-hosted Warcraft Logs Fresh raid analysis app, currently aimed at Classic Fresh reports. The user wants a guild improvement tool with raid-wide and per-player views: damage, healing, ability/buff uptime, deaths, interrupts, and practical suggestions. The intent is to keep expanding this into an evidence-led review tool, not just a report viewer.

## Current state

- The React/TypeScript frontend lives in `frontend/`; the FastAPI backend lives in `backend/`.
- Docker Compose serves the frontend through nginx on host port 8080 by default. Nginx proxies `/api` to FastAPI inside Compose. Compose explicitly binds the frontend host port to `0.0.0.0` by default, which is useful for Windows access to Docker running in WSL 2.
- Warcraft Logs V2 OAuth client credentials are loaded only in the backend. The user confirmed that valid V2 credentials fixed token acquisition and public Fresh reports now load. Do not ask the user to paste credentials and never inspect or commit `.env` contents.
- The report page shows report metadata, boss progression, attempts, and trash fights.
- A selected-pull review endpoint uses the selected fight's `friendlyPlayers` roster, WCL tables for damage, healing, damage taken, friendly fire, casts, interrupts, and buffs, plus death/interrupt/combatant events and player details where available. Results are cached using the existing SQLite cache and TTL.
- The analysis dashboard includes per-player totals, top-five damage/healing/damage-taken/friendly-fire cards, death and interrupt event timelines, and available gear/auras/consumable-like casts. Missing event/detail payloads are labeled as unavailable. Consumables are identified heuristically by cast name; gear enrichment depends on WCL player detail payloads.
- The top bar includes a persistent light/dark selector and a persistent text-size control. Font sizes use `rem` so the control scales the interface consistently.
- Suggestions and summaries are evidence-led review prompts, not grades or class/spec rotation prescriptions.
- Backend diagnostics log report failures and WCL OAuth/GraphQL failures. Keep secrets and bearer tokens out of logs.

## Important implementation details

- Compose route: `GET /api/reports/{report_code}/fights/{fight_id}/analysis`.
- Analysis query and caching live in `backend/app/services/report_service.py`; API routing and error mapping live in `backend/app/api/reports.py`.
- Current analysis fields use WCL `TableDataType` values `DamageDone`, `Healing`, `DamageTaken`, `Casts`, `Interrupts`, and `Buffs`, scoped to a fight ID. Death, interrupt, and combatant data are also requested as event streams. Master data actors are filtered against the selected fight roster before returning them to the frontend.
- The UI is in `frontend/src/App.tsx`, with analysis-specific styles in `frontend/src/analysis.css`.
- WCL `table` responses are JSON-shaped and may contain nested data. Inspect real response shapes before writing analysis rules; do not assume the first scalar value or table row means the same thing across table types.
- Public client-credentials access cannot read private reports. The application currently expects accessible public Fresh reports.
- Do not equate raw DPS/HPS, zero interrupts, deaths, or buff uptime with player skill without encounter context, role/assignment context, and class/game-version-aware interpretation.

## Known limitations and next work

The current review is a first functional data layer, not the finished guild coach. In particular:

1. Inspect representative Fresh table and event payloads to validate all player metric extraction, show per-ability uptime clearly, and improve event paging/truncation handling.
2. Add event-level death recaps (damage sources and timeline before death) and missed dangerous casts, rather than treating successful interrupts as the whole kick story.
3. Build per-player evidence summaries across pulls and progression attempts; distinguish role, class, assignment, fight length, and kill/wipe context.
4. Add class/spec/game-version-aware suggestions backed by explicit evidence or maintained rules. Keep recommendations explainable and label uncertainty; avoid unsupported benchmark claims.
5. Validate gear, gems, enchants, and consumables against real response samples; current enrichment shows fields present in player details and detects likely consumable casts by name.
6. Handle WCL pagination for event data, archive/access failures, and API rate limits deliberately. Cache expensive report analysis using the existing cache.
7. Add mocked backend coverage for analysis response shapes, invalid fight IDs, caching, and WCL failures. Build the frontend in an environment with npm dependencies installed.

## Development and validation

- Full stack: `docker compose up --build -d`; stop with `docker compose down`.
- Backend tests: `cd backend && pytest`.
- Frontend build: `cd frontend && npm run build`.
- Current contributor shell may not have `npm` installed, and Docker socket access can be unavailable; report those limitations rather than assuming a build or live WCL query succeeded.
- For the current `feat/raid-analytics-dashboard` work, host `npm` and the repo `.venv` are absent. `docker compose build` succeeded, including the frontend `tsc -b` and Vite production build; Python tests could not run because `pytest` is not installed in the host environment. No live Compose/WCL validation has been run. `git diff --check` passes.
- Keep API calls server-side and use mocked Warcraft Logs responses in tests. Never make tests depend on private reports or real credentials.

## WSL access notes

The user runs Docker from Ubuntu in WSL 2 and accesses it from a Windows 11 host. Docker output confirmed `0.0.0.0:8080->80/tcp`; `curl http://127.0.0.1:8080/api/health` succeeded in WSL; Windows `Test-NetConnection` to the current WSL IP on port 8080 succeeded. Backend port 8000 is intentionally not published to Windows. The WSL IP can change after restart; use `hostname -I` to retrieve it. The user reached the frontend successfully.

## Publishing preference

The user explicitly wants repository work pushed to GitHub by default. Finish coherent changes with a commit and push; do not leave completed work only in the local workspace. For substantial features or broad refactors, create a focused feature branch, push it, and open a GitHub pull request. Small fixes and documentation-only changes can go directly to `main` unless the user says otherwise. Check status and review staged files first; never stage `.env`, secrets, databases, or build output. Upstream is `origin` (`https://github.com/steffenlongva/hellotherelogs.git`).
