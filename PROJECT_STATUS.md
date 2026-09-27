# Project status and handoff

This file is the persistent handoff for contributors continuing hellotherelogs. Read it with `AGENTS.md` before implementation work, then update it when the project state changes.

## Product

hellotherelogs is a self-hosted Warcraft Logs Fresh raid analysis app, currently aimed at Classic Fresh reports. The user wants a guild improvement tool with raid-wide and per-player views: damage, healing, ability/buff uptime, deaths, interrupts, and practical suggestions. The intent is to keep expanding this into an evidence-led review tool, not just a report viewer.

## Current state

- The React/TypeScript frontend lives in `frontend/`; the FastAPI backend lives in `backend/`.
- Docker Compose serves the frontend through nginx on host port 8080 by default. Nginx proxies `/api` to FastAPI inside Compose. The root Compose file builds locally for development; `docker-compose.unraid.yml` pulls the published amd64 images from GHCR for server deployment.
- `.github/workflows/publish-images.yml` builds backend and frontend images on pull requests and publishes them on pushes to `main` and version tags. Main builds publish `latest` and commit SHA tags. GHCR packages under the personal account default to private; an admin must explicitly make both packages public for anonymous Unraid pulls, or configure registry login on Unraid for private pulls.
- Unraid uses `.env.unraid.example` as a template for backend WCL credentials and deployment settings. `docker-compose.unraid.yml` stores SQLite under `/mnt/user/appdata/hellotherelogs/data` by default. Compose Manager Plus can pull scheduled GHCR image updates; confirm plugin compatibility with the installed Unraid version.
- Warcraft Logs V2 OAuth client credentials are loaded only in the backend. The user confirmed that valid V2 credentials fixed token acquisition and public Fresh reports now load. Do not ask the user to paste credentials and never inspect or commit `.env` contents.
- The report page shows report metadata, boss progression, attempts, and trash fights.
- A selected-pull review endpoint uses the selected fight's `friendlyPlayers` roster, WCL tables for damage, healing, damage taken, friendly fire, casts, interrupts, and buffs, plus death/interrupt/combatant events and player details where available. Results are cached using the existing SQLite cache and TTL.
- The analysis dashboard groups player comparisons by class, makes full leaderboards expandable, shows player and ability uptime, and gives per-player review prompts tied to recorded deaths, friendly fire, and uptime observations. It computes friendly fire from outgoing damage events where both source and target belong to the selected fight roster; NPC-target damage is excluded. Friendly fire is marked incomplete if event data is unavailable or still paginated after the bounded page fetch.
- Itemization summaries show average item level and separate enchant/gem counts and details, alongside auras and consumable-like casts. Missing event/detail payloads are labeled as unavailable. Consumables are identified heuristically by cast name; gear enrichment depends on WCL player detail payloads.
- The top bar includes persistent Dark, Light, Catppuccin Mocha, Tokyo Night, and Nord themes plus a persistent text-size slider. The default font scale is 1.1, centered in the slider's range; font sizes use `rem` so it scales the interface consistently.
- The frontend header shows the built commit prefix and UTC build date. GitHub Actions passes both values into the frontend image so the currently deployed Unraid build can be identified after image updates.
- The encounter page includes a four-part learning plan for survival, interrupt assignments, raid coverage, and cooldown planning. It distinguishes observed evidence from topics that need review and states where the current report data cannot confirm an issue.
- The selected-pull view has two public cohort sources: recent two-week parses surfaced through up to ten roster characters' same-spec, item-level-bracket rankings; or public execution-ranked kills. It examines up to 25 candidate reports in batches and returns up to five that pass the duration, composition, and item-level filters. WCL links are included. Wipes do not receive kill-to-kill benchmarks.
- Benchmark analysis verifies encounter, difficulty, kill state, and raid size. Strict/balanced modes additionally apply duration, class-composition, and item-level filters when source data supports them; broad mode relaxes these filters. It compares raid DPS/HPS, damage taken per second, deaths, landed interrupts, and per-player DPS/HPS, damage taken, ability uptime, and cast rates. Per-player distributions give each reference report one sample; exact spec peers are preferred and unknown-spec same-class peers are fallback matches. Raid review highlights need at least three references and explain what data warrants follow-up. Recent comparisons are roster-seeded and not representative random samples; execution-ranked kills are aspirational. Neither successful interrupts nor damage/output alone establish mistakes or missed-kick opportunities.
- Fight analysis also requests Warcraft Logs report rankings for two-week parses and best-score rankings. Where WCL returns player percentile fields, both appear separately in the class comparison; a low recent percentile prompts a review of cast choices and uptime. Percentiles are WCL context, not an explanation or a guild-composition-matched metric delta.
- Critical-moment names fall back to the selected-fight actor roster when WCL events provide actor IDs without names. Uptime parsing supports WCL's nested `data.auras` table shape, calculates percentages from `totalUptime` and `totalTime`, and includes a Debuffs table for class-applied debuffs.
- Learning-plan topics use expandable disclosure cards so review steps can grow without crowding the encounter page.
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

1. Validate analysis table shapes against representative Fresh reports. Source attribution, uptime meaning, and external-buff identification still depend on the actual WCL payload.
2. Add missed dangerous casts and interrupt opportunities; successful interrupts alone do not show whether kick coverage was complete.
3. Identify external raid buffs reliably from provider/target fields, then compare coverage with the classes present and fight timing. Do not infer a missing buff from a low generic uptime average.
4. Build per-player and raid evidence summaries across pulls and progression attempts; distinguish role, class, assignment, fight length, and kill/wipe context.
5. Add class/spec/game-version-aware suggestions backed by explicit evidence or maintained rules. Keep recommendations explainable and label uncertainty; avoid unsupported benchmark claims.
6. Validate gear, gems, enchants, and consumables against real response samples; current enrichment shows reported item level/enchant/gem fields and detects likely consumable casts by name.
7. Finish paging death and interrupt event streams, and handle archive/access failures and API rate limits deliberately. Friendly damage follows event pagination with a bounded six-page cap. Cache expensive report analysis using the existing cache.
8. Add mocked backend coverage for analysis response shapes, invalid fight IDs, caching, and WCL failures. Build the frontend in an environment with npm dependencies installed.
9. Validate both benchmark cohorts against live Fresh response shapes and public reports. Recent matching queries up to ten roster characters, inspects up to 25 surfaced reports, and returns at most five; its sample is limited and potentially biased toward those profiles. Execution mode also returns up to five leaderboard kills. Improve role resolution and fit-phase matching, compare wipe progression separately from kills, and report uncertainty for small cohorts. Validate cast, cooldown, and uptime table interpretation before adding stronger player-specific suggestions. Interrupt opportunities still need enemy cast/failure events; successful interrupts alone cannot establish missed kicks.

## Development and validation

- Full stack: `docker compose up --build -d`; stop with `docker compose down`.
- Backend tests: `cd backend && pytest`.
- Frontend build: `cd frontend && npm run build`.
- Current contributor shell may not have `npm` installed, and Docker socket access can be unavailable; report those limitations rather than assuming a build or live WCL query succeeded.
- For `feat/clean-player-comparison`, `.venv/bin/python -m pytest` passed all 17 backend tests and `docker compose build` passed, including the frontend `tsc -b` and Vite production build. No live Compose/WCL report validation has been run. `git diff --check` passes.
- `feat/peer-log-benchmarks` was merged as PR #8 (`6b09600`); the main push workflow completed successfully and published backend and frontend GHCR images.
- On `feat/benchmark-evidence-highlights`, `.venv/bin/python -m pytest -q` passes 24 tests and `docker compose build` passes, including frontend TypeScript and Vite. Benchmark service tests use mocked ranking/report payloads; no live Fresh response or rendered browser comparison has been validated yet.
- Keep API calls server-side and use mocked Warcraft Logs responses in tests. Never make tests depend on private reports or real credentials.

## Local WSL development notes

The user currently develops from Ubuntu in WSL 2 and has accessed the app from a Windows 11 host. This is a development setup only; the intended long-term deployment is on a separate Unraid server using GHCR images. Backend port 8000 remains internal to Compose.

## Publishing preference

The user explicitly wants repository work pushed to GitHub by default. Finish coherent changes with a commit and push; do not leave completed work only in the local workspace. For substantial features or broad refactors, create a focused feature branch, push it, and open a GitHub pull request. Small fixes and documentation-only changes can go directly to `main` unless the user says otherwise. Check status and review staged files first; never stage `.env`, secrets, databases, or build output. Upstream is `origin` (`https://github.com/steffenlongva/hellotherelogs.git`).
