# HelloThereLogs

HelloThereLogs  is a self-hosted Warcraft Logs Classic Fresh analysis application. This is Phase 1: the API/frontend foundation, server-side WCL authentication transport, deployment, and health check. The report dashboard is intentionally not implemented yet.

## Start on Unraid or Docker

1. Create a Warcraft Logs API client in the Warcraft Logs account client management page.
2. Copy `.env.example` to `.env`; fill in `WCL_CLIENT_ID` and `WCL_CLIENT_SECRET`. Keep `.env` private.
3. Run `docker compose up --build -d` from this directory.
4. Open `http://YOUR_UNRAID_HOST:8080`. Set `LOGLOOM_PORT` in `.env` to change the host port.
5. Check `http://YOUR_UNRAID_HOST:8080/api/health` for `{"status":"ok","service":"logloom-api"}`.

Docker Compose creates the persistent `logloom_data` volume for SQLite. The frontend's nginx proxies `/api/` to FastAPI. Warcraft Logs credentials are only passed to the backend container and are never compiled into browser assets. OAuth is requested lazily when a backend WCL operation is invoked; health checks do not require configured credentials.

## Local development

Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`.

Frontend: `cd frontend && npm install && npm run dev`. Vite serves the frontend; in the deployed configuration nginx routes API requests to FastAPI. For local frontend development, use a Vite proxy or browse via the Compose frontend.

Run backend checks with `cd backend && pytest`. Build the frontend with `cd frontend && npm run build`.

## Warcraft Logs API verification

The Fresh schema documentation is published at [Fresh v2 API docs](https://fresh.warcraftlogs.com/v2-api-docs/warcraft/). OAuth flow details are documented at [Warcraft Logs API docs](https://www.warcraftlogs.com/api/docs). The documented public API uses GraphQL and the client-credentials flow: POST `grant_type=client_credentials` to `https://www.warcraftlogs.com/oauth/token` using HTTP Basic credentials (`client_id:client_secret`), then pass the returned token as `Authorization: Bearer …`. The app defaults GraphQL to `https://fresh.warcraftlogs.com/api/v2/client`; both URLs can be changed via backend environment settings.

Fresh's documented `ReportData.report(code: String, allowUnlisted: Boolean)` returns `Report`. `Report` documents `code`, `title`, `startTime`, `endTime`, `fights(...)`, `masterData(translate)`, `events(...)`, and `table(...)`. `ReportFight` includes `id`, `encounterID`, `name`, `startTime`, `endTime`, `kill`, `fightPercentage`, and participant ID/spec arrays. Fight times are relative milliseconds from report start; report start/end are UNIX milliseconds. Events accept documented filters including `dataType`, `fightIDs`, `startTime`, `endTime`, `sourceID`, `targetID`, `abilityID`, `filterExpression`, and `limit` (documented 100–10000; default 300). `table` returns JSON and supports `dataType`, fight/time/source/target filters, `viewBy`, and related filters. Values/enums must follow the live schema; dashboard queries will be implemented against that schema in a later phase.

The documented GraphQL shape for a report lookup is `query ReportOverview($code: String!) { reportData { report(code: $code) { code title startTime endTime fights { id encounterID name startTime endTime kill fightPercentage } } } }`; the `reportData`, `report`, and fight field names come from the Fresh schema. Table/event calls are nested under `report` and take schema-defined arguments; event types use the `EventDataType` enum, whose live values should be read from the current schema before use. `filterExpression` accepts Warcraft Logs' site query language; its grammar is not fully specified by the field description in the Fresh schema, so Logloom will not invent or rewrite expressions. A query can ask for the live point state as `query { rateLimitData { limitPerHour pointsSpentThisHour pointsResetIn } }`.

The schema exposes `rateLimitData { limitPerHour pointsSpentThisHour pointsResetIn }`, allowing an installation to observe its own point quota rather than assume a fixed allowance. API points are distinct from raw request counts. Limits may depend on the API client/account; handle API errors and respect the returned budget.

## Configuration

| Variable | Purpose |
| --- | --- |
| `WCL_CLIENT_ID`, `WCL_CLIENT_SECRET` | Server-side WCL OAuth client credentials |
| `WCL_TOKEN_URL` | OAuth token endpoint |
| `WCL_GRAPHQL_URL` | Fresh GraphQL client endpoint |
| `DATABASE_URL` | SQLite URL; Compose sets this to its persistent volume |
| `FRONTEND_ORIGIN` | Allowed browser origin for direct API development |
| `LOGLOOM_PORT` | Optional host port for nginx, default `8080` |
