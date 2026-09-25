# Repository Guidelines

## Continuity and publishing

- Read `PROJECT_STATUS.md` before making changes. It is the durable handoff for the current product state, design decisions, known limitations, and next work.
- Update `PROJECT_STATUS.md` whenever implementation status or priorities change enough to affect the next contributor's work.
- The user wants completed repository work pushed to GitHub by default. After finishing a coherent change, commit it and push the branch to `origin`; do not leave completed work only in the local workspace. Never commit `.env`, credentials, tokens, local databases, or generated build output.
- For substantial features or broad refactors, create a focused feature branch, push it, and open a GitHub pull request for review. Keep small fixes and documentation-only changes proportional; they may be committed directly to `main` unless the user asks otherwise.
- Keep `README.md` focused on setup and user-facing behavior. Put contributor handoff and roadmap details in `PROJECT_STATUS.md`.

## Project Structure & Module Organization

hellotherelogs is a self-hosted Warcraft Logs Fresh analysis application. Keep the Python API in `backend/` and the React/TypeScript client in `frontend/`. Backend routes live in `backend/app/api/`; configuration, database/cache, WCL transport, report parsing, and normalization stay in focused modules under `backend/app/`. Put pytest tests under `backend/tests/` and Vite source/assets under `frontend/src/`. Keep Compose and deployment configuration at the repository root or under a clearly named deployment directory. Do not commit generated build output, local databases, or credentials.

## Build, Test, and Development Commands

- `docker compose up --build` builds and starts the full stack.
- `docker compose down` stops the stack.
- `cd backend && pytest` runs backend tests.
- `cd frontend && npm run dev` starts Vite; its `/api` proxy expects FastAPI on port 8000.
- `cd frontend && npm run build` type-checks and builds the frontend.

## Coding Style & Naming Conventions

Use four spaces in Python, type annotate public functions, and use `snake_case` for modules/functions. Name tests `test_*.py`. Use two spaces in TypeScript/TSX, `PascalCase` for components/types, and `camelCase` for values/functions. Keep UI components focused and reuse existing project dependencies.

## Testing Guidelines

Use pytest for backend behavior. Mock Warcraft Logs network responses so tests never require private reports or credentials. Cover parsers, report/fight normalization, API error mapping, and caching when those paths change. Run pytest and the frontend production build before submitting changes.

## Commit & Pull Request Guidelines

There is no established commit history. Use concise imperative commit subjects such as `Cache normalized report data`. Pull requests should summarize behavior and configuration changes, list validation commands/results, link related issues, and include screenshots for visible UI changes.

## Security & Configuration

Keep Warcraft Logs V2 client secrets on the backend. Read credentials from environment configuration, document variables in `.env.example`, and never commit `.env`, tokens, or SQLite files. The browser must call FastAPI rather than Warcraft Logs directly.
