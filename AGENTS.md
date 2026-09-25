# Repository Guidelines

## Project Structure & Module Organization

Logloom is a self-hosted Warcraft Logs Fresh analytics application. Keep the Python API in `backend/` and the React/TypeScript client in `frontend/`. Backend route handlers belong under `backend/app/api/`; API configuration, WCL client, persistence, and schemas should remain in their own modules. Put pytest tests under `backend/tests/`. Keep Vite source and assets under `frontend/src/`. Deployment files such as `docker-compose.yml`, Dockerfiles, and nginx configuration should live at the repository root or in a clearly named `deploy/` directory. Do not commit generated build output, local databases, or credentials.

## Build, Test, and Development Commands

Use the repository root for Compose commands:

- `docker compose up --build` builds and starts the full local stack.
- `docker compose down` stops the stack.
- `cd backend && pytest` runs the API test suite.
- `cd frontend && npm run dev` starts the Vite development server.
- `cd frontend && npm run build` type-checks and builds the production frontend.

When dependencies are installed in containers, use the corresponding service commands (for example, `docker compose run --rm backend pytest`).

## Coding Style & Naming Conventions

Use four spaces for Python indentation, type annotate public functions, and use `snake_case` for modules and functions. Name tests `test_*.py`. Use two spaces for TypeScript/TSX indentation, `PascalCase` for React components and types, and `camelCase` for values and functions. Keep components focused and place reusable UI in `frontend/src/components/`. Follow the existing formatter and linter configuration when present; avoid introducing a second tool for the same job.

## Testing Guidelines

Use pytest for backend behavior and add focused tests alongside API and service changes. Test health/configuration and WCL client behavior without requiring live credentials; mock network responses. The frontend production build is the baseline check for TypeScript and bundling. Run tests and builds before submitting changes, and never make tests depend on private Warcraft Logs data.

## Commit & Pull Request Guidelines

There is no Git history yet to establish a commit convention. Use concise imperative subjects, such as `Add WCL token caching`. Pull requests should explain the change and its impact, list test/build commands and results, link related issues, and include screenshots for visible UI changes. Call out configuration or deployment changes explicitly.

## Security & Configuration

Keep Warcraft Logs client secrets exclusively on the backend. Read credentials from environment configuration, document required variables in `.env.example`, and never commit `.env`, tokens, or SQLite files. The browser must call the FastAPI service rather than Warcraft Logs directly.
