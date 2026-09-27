# hellotherelogs

hellotherelogs is a self-hosted Warcraft Logs Classic Fresh report reader. It loads public report data through the Fresh Warcraft Logs GraphQL API; Warcraft Logs credentials remain in FastAPI and are never sent to the browser.

## Deploy on Unraid

Unraid can run the prebuilt app images from GitHub Container Registry (GHCR); it does not need WSL or a local build toolchain. The repository workflow builds and publishes separate `linux/amd64` backend and frontend images to:

- `ghcr.io/steffenlongva/hellotherelogs-backend`
- `ghcr.io/steffenlongva/hellotherelogs-frontend`

Pushes to `main` publish the `latest` tag and a commit-specific `sha-...` tag. Version tags such as `v1.2.0` publish matching image tags. Pull requests build both images without publishing them.

1. After the first workflow run, open each image package under the GitHub account's **Packages** tab. In **Package settings**, change visibility to **Public** if you want Unraid to pull without registry credentials. GHCR personal packages are private by default. Making a package public is a permanent visibility change on GitHub. If you prefer private packages, keep them private and sign in to GHCR on Unraid with a GitHub personal access token (classic) that has `read:packages` permission.
2. Copy or clone this repository on Unraid, for example under `/mnt/user/appdata/hellotherelogs`. The source is only needed for the Compose and environment files; Compose pulls the published images and does not build them.
3. Copy `.env.unraid.example` to `.env` in that directory and enter `WCL_CLIENT_ID` and `WCL_CLIENT_SECRET` from your Warcraft Logs V2 API client. Keep this file private; credentials are passed only to the backend container.
4. From the directory containing the files, run:

   ```sh
   docker compose -f docker-compose.unraid.yml pull
   docker compose -f docker-compose.unraid.yml up -d
   ```

5. Open `http://UNRAID_ADDRESS:8080`. Set `HELLOTHERELOGS_PORT` in `.env` to use a different host port. SQLite data is stored in the named `hellotherelogs_data` volume and remains across container updates.

To update to the latest main build, run the same `pull` and `up -d` commands again. For a reproducible deployment, set both image variables in `.env` to the same `sha-...` tag or release tag instead of `latest`. Back up the `hellotherelogs_data` volume along with your other app data.

For a private GHCR package, log in once on Unraid before pulling:

```sh
docker login ghcr.io --username YOUR_GITHUB_USERNAME
```

Enter a personal access token (classic) with `read:packages` when prompted. Docker stores the login on the Unraid host; do not put this token in the Compose file or repository.

## Run locally with Docker Compose

1. Create a Warcraft Logs **V2 API client** in the Warcraft Logs account client management page.
2. Copy `.env.example` to `.env`, then set `WCL_CLIENT_ID` and `WCL_CLIENT_SECRET`.
3. Run `docker compose up --build -d` from this directory.
4. Open `http://localhost:8080` on the local machine. If running Docker inside WSL 2, localhost forwarding is usually available; otherwise get the WSL address with `hostname -I` inside Ubuntu and open `http://WSL_ADDRESS:8080` from Windows. Set `HELLOTHERELOGS_PORT` to change the host port or `HELLOTHERELOGS_BIND_ADDRESS` to change the bind address.
5. Visit `/api/health` to check the API. Compose persists SQLite data in the `hellotherelogs_data` volume.

## Local development

Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`.

Frontend: `cd frontend && npm install && npm run dev`. Vite proxies `/api` to `http://localhost:8000`.

Run `cd backend && pytest` for backend tests and `cd frontend && npm run build` for a production frontend build.

## Warcraft Logs API versions and schema

Warcraft Logs supports two API versions. **V1 is a REST API using a V1 key**, which provides access to non-private site data and has separate V1 documentation/playground. **V2 is GraphQL and uses OAuth client credentials**. hellotherelogs uses V2; a V1 key cannot be used as the V2 client ID or secret. The V2 client-credentials exchange posts `grant_type=client_credentials` with HTTP Basic credentials to `https://www.warcraftlogs.com/oauth/token`; requests then send the returned Bearer token to GraphQL. Defaults are `https://fresh.warcraftlogs.com/api/v2/client` for Fresh GraphQL and the Warcraft Logs OAuth token URL. Both are backend settings. See the [Warcraft Logs API documentation](https://www.warcraftlogs.com/api/docs) and [Fresh V2 schema](https://fresh.warcraftlogs.com/v2-api-docs/warcraft/).

The report query follows documented `Query.reportData.report(code:)` fields: `code`, `title`, `startTime`, `endTime`, `zone { name }`, `guild { name }`, and `fights`. The Fresh `ReportFight` schema documents `id`, `encounterID`, `name`, `startTime`, `endTime`, `kill`, `fightPercentage`, and `friendlyPlayers`. Report start/end values are UNIX milliseconds; fight times are millisecond offsets from report start. Normalization derives report duration from report start/end and fight duration from fight end/start. Boss progression groups fights by nonzero `encounterID`, counting `kill: true` as kills and `kill: false` as wipes; it preserves null kill values without treating them as wipes.

Selected-fight review scopes the player roster to the fight's `friendlyPlayers`, then queries Warcraft Logs tables for damage, healing, damage taken, casts, interrupts, and buff uptime. Friendly fire is computed from outgoing damage events whose source and target are both players in the selected fight, excluding NPC damage. The dashboard groups players by class for side-by-side comparison, lets each top-five board expand to the full roster, and shows player/ability uptime, death and interrupt timelines, and concise per-player review suggestions. Itemization is summarized as average item level with separate enchant and gem counts/details, alongside auras and consumable-like casts returned by WCL. The light/dark selector and text-size slider are available in the top bar; both preferences persist in that browser. Some optional fields depend on the report, and consumable matching is heuristic, so absent detail is labeled unavailable rather than treated as proof that an item was not used. Suggestions are evidence-led prompts, not grades or class-specific rotation prescriptions. API usage is observable via `rateLimitData { limitPerHour pointsSpentThisHour pointsResetIn }`; the app does not assume one fixed quota.

## Report workflow

Paste a Fresh URL such as `https://fresh.warcraftlogs.com/reports/REPORTCODE`, choose **ANALYZE LOG**, then the app navigates to `/reports/REPORTCODE`. The backend validates the Fresh report URL, retrieves and normalizes report/fight data, and caches the JSON representations in SQLite for `CACHE_TTL_SECONDS` (default 900 seconds).

## Configuration

| Variable | Purpose |
| --- | --- |
| `WCL_CLIENT_ID`, `WCL_CLIENT_SECRET` | Backend-only V2 OAuth client credentials |
| `WCL_TOKEN_URL` | OAuth token endpoint |
| `WCL_GRAPHQL_URL` | Fresh V2 GraphQL endpoint |
| `DATABASE_URL` | SQLite URL; Compose uses the persistent volume |
| `CACHE_TTL_SECONDS` | Normalized report/fight cache lifetime |
| `FRONTEND_ORIGIN` | CORS origin for direct API access |
| `HELLOTHERELOGS_PORT` | Optional nginx host port (default `8080`) |
| `HELLOTHERELOGS_BIND_ADDRESS` | Host interface Docker publishes on (default `0.0.0.0`, all interfaces) |

Unraid deployment uses `.env.unraid.example` and `docker-compose.unraid.yml`. `HELLOTHERELOGS_BACKEND_IMAGE` and `HELLOTHERELOGS_FRONTEND_IMAGE` can override the default GHCR `latest` tags to pin a release or commit image.

## Contributing

See [AGENTS.md](AGENTS.md) for repository conventions and [PROJECT_STATUS.md](PROJECT_STATUS.md) for the implementation handoff, current limitations, and next analysis work.
