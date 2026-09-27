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
- The analysis dashboard groups player comparisons by class, makes full leaderboards expandable, shows player and ability uptime, and gives per-player review prompts tied to recorded deaths, friendly fire, and uptime observations. It computes friendly fire from outgoing damage events where both source and target belong to the selected fight roster; NPC-target damage is excluded. Friendly fire is marked incomplete if event data is unavailable or still paginated after the bounded page fetch.
- Itemization summaries show average item level and separate enchant/gem counts and details, alongside auras and consumable-like casts. Missing event/detail payloads are labeled as unavailable. Consumables are identified heuristically by cast name; gear enrichment depends on WCL player detail payloads.
- The top bar includes a persistent light/dark selector and a persistent text-size control. Font sizes use `rem` so the control scales the interface consistently.
- Suggestions and summaries are evidence-led review prompts, not grades or class/spec rotation prescriptions.
- The encounter review is organized around overall raid performance: survival, critical moments, roster composition, buff coverage, and then output context. Damage taken is presented as a signal to investigate, not automatically labeled avoidable; that judgment needs encounter mechanics and assignment context.
- Backend diagnostics log report failures and WCL OAuth/GraphQL failures. Keep secrets and bearer tokens out of logs.

## Important implementation details

- Compose route: `GET /api/reports/{report_code}/fights/{fight_id}/analysis`.
- Analysis query and caching live in `backend/app/services/report_service.py`; API routing and error mapping live in `backend/app/api/reports.py`.
- Current analysis fields use WCL `TableDataType` values `DamageDone`, `Healing`, `DamageTaken`, `Casts`, `Interrupts`, and `Buffs`, scoped to a fight ID. Death, interrupt, combatant, and per-player outgoing damage data are requested as event streams. Master data actors are filtered against the selected fight roster before returning them to the frontend.
- The UI is in `frontend/src/App.tsx`, with analysis-specific styles in `frontend/src/analysis.css`.
- WCL `table` responses are JSON-shaped and may contain nested data. Inspect real response shapes before writing analysis rules; do not assume the first scalar value or table row means the same thing across table types.
- Public client-credentials access cannot read private reports. The application currently expects accessible public Fresh reports.
- Do not equate raw DPS/HPS, zero interrupts, deaths, or buff uptime with player skill without encounter context, role/assignment context, and class/game-version-aware interpretation.

## Known limitations and next work

The current review is a first functional data layer, not the finished guild coach. In particular:

1. Validate analysis table shapes against representative Fresh reports. The current page makes roster mix, reported buff coverage, and death/interrupt moments easier to scan; source attribution and uptime meaning still depend on the actual WCL payload.
2. Add incoming damage events around each death so the timeline can show a short pre-death recap. Keep “avoidable” classification out until encounter-specific mechanics and player assignments can support it.
3. Add missed dangerous casts and interrupt opportunities; successful interrupts alone do not show whether kick coverage was complete.
4. Identify external raid buffs reliably from provider/target fields, then compare coverage with the classes present and fight timing. Do not infer a missing buff from a low generic uptime average.
5. Build per-player and raid evidence summaries across pulls and progression attempts; distinguish role, class, assignment, fight length, and kill/wipe context.
6. Add class/spec/game-version-aware suggestions backed by explicit evidence or maintained rules. Keep recommendations explainable and label uncertainty; avoid unsupported benchmark claims.
7. Validate gear, gems, enchants, and consumables against real response samples; current enrichment shows reported item level/enchant/gem fields and detects likely consumable casts by name.
8. Finish paging death and interrupt event streams, and handle archive/access failures and API rate limits deliberately. Friendly damage follows event pagination with a bounded six-page cap. Cache expensive report analysis using the existing cache.
9. Add mocked backend coverage for analysis response shapes, invalid fight IDs, caching, and WCL failures. Build the frontend in an environment with npm dependencies installed.

## Development and validation

- Full stack: `docker compose up --build -d`; stop with `docker compose down`.
- Backend tests: `cd backend && pytest`.
- Frontend build: `cd frontend && npm run build`.
- Current contributor shell may not have `npm` installed, and Docker socket access can be unavailable; report those limitations rather than assuming a build or live WCL query succeeded.
- For `feat/clean-player-comparison`, `.venv/bin/python -m pytest` passed all 17 backend tests and `docker compose build` passed, including the frontend `tsc -b` and Vite production build. No live Compose/WCL report validation has been run. `git diff --check` passes.
- Keep API calls server-side and use mocked Warcraft Logs responses in tests. Never make tests depend on private reports or real credentials.

## WSL access notes

The user runs Docker from Ubuntu in WSL 2 and accesses it from a Windows 11 host. Docker output confirmed `0.0.0.0:8080->80/tcp`; `curl http://127.0.0.1:8080/api/health` succeeded in WSL; Windows `Test-NetConnection` to the current WSL IP on port 8080 succeeded. Backend port 8000 is intentionally not published to Windows. The WSL IP can change after restart; use `hostname -I` to retrieve it. The user reached the frontend successfully.

## Publishing preference

The user explicitly wants repository work pushed to GitHub by default. Finish coherent changes with a commit and push; do not leave completed work only in the local workspace. For substantial features or broad refactors, create a focused feature branch, push it, and open a GitHub pull request. Small fixes and documentation-only changes can go directly to `main` unless the user says otherwise. Check status and review staged files first; never stage `.env`, secrets, databases, or build output. Upstream is `origin` (`https://github.com/steffenlongva/hellotherelogs.git`).
