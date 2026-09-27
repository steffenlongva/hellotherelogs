# Repository Guidelines

## Handoff and scope

- Read `PROJECT_STATUS.md` before implementation work. Keep it current when implementation status, known limitations, or next priorities change.
- Keep `README.md` focused on setup and user-facing behavior; use `PROJECT_STATUS.md` for contributor handoff and roadmap details.
- Preserve unrelated working-tree changes. Never inspect or commit `.env` contents, credentials, tokens, local databases, or generated build output.

## Project structure

hellotherelogs is a self-hosted Warcraft Logs Fresh report analysis app. The FastAPI service is in `backend/app/`: routes in `api/`, settings and database setup in `core/`, and WCL access, normalization, and caching in `services/`. Put backend tests and reusable response fixtures in `backend/tests/`. The React/TypeScript client and styles live in `frontend/src/`; Vite and nginx configuration live in `frontend/`. Compose and deployment settings belong at the repository root.

## Development commands

- `docker compose up --build -d` builds and starts the stack; `docker compose down` stops it.
- `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000` starts the API locally.
- `cd backend && pytest` runs backend tests.
- `cd frontend && npm install && npm run dev` starts Vite; its `/api` proxy expects the API on port 8000.
- `cd frontend && npm run build` type-checks and builds the production client.

## Style and testing

Use four spaces and type annotations for public Python functions; use `snake_case` for Python modules and functions, and name pytest files `test_*.py`. Mock Warcraft Logs responses so tests need no credentials or private reports. Cover parsing, normalization, API errors, pagination, and cache behavior when those paths change.

Use two spaces in TypeScript/TSX, `PascalCase` for components and types, and `camelCase` for values and functions. Keep components focused and reuse installed dependencies. There is no separate formatter or linter configured; follow the surrounding code.

## Analysis and data safety

Treat Warcraft Logs payloads as nested, version-specific data: inspect representative shapes before adding interpretation. Scope player metrics to the selected fight roster. Present suggestions as evidence-led prompts; do not label deaths, damage taken, raw output, uptime, or missing interrupts as player fault without encounter, role, and assignment context. Keep OAuth credentials and API calls on the backend, document configuration in `.env.example`, and keep secrets out of logs and browser code.

## Commits and pull requests

Recent commits use concise imperative subjects in sentence case (for example, `Focus encounter review on raid performance`). PRs should summarize behavior and configuration changes, list validation and results, link related issues, and include screenshots for visible UI changes. Push completed work to `origin`; use a focused feature branch and PR for substantial features or broad refactors. Keep documentation-only changes proportional.
