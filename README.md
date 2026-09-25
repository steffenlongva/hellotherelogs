# hellotherelogs

hellotherelogs is a self-hosted Warcraft Logs Classic Fresh report reader. It loads public report data through the Fresh Warcraft Logs GraphQL API; Warcraft Logs credentials remain in FastAPI and are never sent to the browser.

## Start with Docker Compose

1. Create a Warcraft Logs **V2 API client** in the Warcraft Logs account client management page.
2. Copy `.env.example` to `.env`, then set `WCL_CLIENT_ID` and `WCL_CLIENT_SECRET`.
3. Run `docker compose up --build -d` from this directory.
4. Open `http://YOUR_UNRAID_HOST:8080`; set `HELLOTHERELOGS_PORT` to change the host port.
5. Visit `/api/health` to check the API. Compose persists SQLite data in the `hellotherelogs_data` volume.

## Local development

Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`.

Frontend: `cd frontend && npm install && npm run dev`. Vite proxies `/api` to `http://localhost:8000`.

Run `cd backend && pytest` for backend tests and `cd frontend && npm run build` for a production frontend build.

## Warcraft Logs API versions and schema

Warcraft Logs supports two API versions. **V1 is a REST API using a V1 key**, which provides access to non-private site data and has separate V1 documentation/playground. **V2 is GraphQL and uses OAuth client credentials**. hellotherelogs uses V2; a V1 key cannot be used as the V2 client ID or secret. The V2 client-credentials exchange posts `grant_type=client_credentials` with HTTP Basic credentials to `https://www.warcraftlogs.com/oauth/token`; requests then send the returned Bearer token to GraphQL. Defaults are `https://fresh.warcraftlogs.com/api/v2/client` for Fresh GraphQL and the Warcraft Logs OAuth token URL. Both are backend settings. See the [Warcraft Logs API documentation](https://www.warcraftlogs.com/api/docs) and [Fresh V2 schema](https://fresh.warcraftlogs.com/v2-api-docs/warcraft/).

The report query follows documented `Query.reportData.report(code:)` fields: `code`, `title`, `startTime`, `endTime`, `zone { name }`, `guild { name }`, and `fights`. The Fresh `ReportFight` schema documents `id`, `encounterID`, `name`, `startTime`, `endTime`, `kill`, `fightPercentage`, and `friendlyPlayers`. Report start/end values are UNIX milliseconds; fight times are millisecond offsets from report start. Normalization derives report duration from report start/end and fight duration from fight end/start. Boss progression groups fights by nonzero `encounterID`, counting `kill: true` as kills and `kill: false` as wipes; it preserves null kill values without treating them as wipes.

Event/table exploration is not part of this phase. The schema describes `events` and `table` as report fields with typed filters, and `filterExpression` as Warcraft Logs site query language. The exact enum values/expressions must be taken from the live Fresh schema/site query language rather than guessed. API usage is observable via `rateLimitData { limitPerHour pointsSpentThisHour pointsResetIn }`; the app does not assume one fixed quota.

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
