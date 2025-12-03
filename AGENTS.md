# Repository Guidelines

## Project Structure & Modules
- `src/agcluster/container/` – FastAPI backend: `api/` endpoints, `core/` orchestration (session, container, translation), `models/` Pydantic schemas, and `ui/` Next.js dashboard.
- `tests/` – Pytest suites split into `unit/` and `integration/`; markers also cover `e2e` (Docker-backed).
- `e2e/agcluster.spec.ts` – Root Playwright checks against a running stack.
- `docker/`, `docker-compose.yml`, `configs/`, `.env.example` – Deployment assets; copy `.env.example` to `.env` before local runs.
- `docs/`, `examples/` – Reference material and sample agent configurations.

## Build, Test, and Development Commands
- Backend setup: `pip install -e ".[dev]"` (Python 3.11+). Start stack: `docker compose up -d`; rebuild images with `docker compose build`.
- API-only run (dev): `uvicorn agcluster.container.api.main:app --reload` after setting `ANTHROPIC_API_KEY` and other env vars.
- Backend tests: `pytest tests/` (all), `pytest tests/unit`, `pytest tests/integration`, or `pytest --cov=agcluster.container tests/`.
- UI workspace (`src/agcluster/container/ui`): `npm install`, then `npm run dev` for Next.js, `npm run build`/`npm start` for production, `npm test` for Vitest, `npm run test:e2e` for Playwright UI flows.
- Root Playwright smoke (if stack is up): `npm test` from repo root runs `playwright test`.

## Coding Style & Naming Conventions
- Python: Black and Ruff with 100-char lines; optional mypy (`mypy src/agcluster`). Prefer typed function signatures in new code.
- Tests: filenames `test_*.py`; classes `Test*`; functions `test_*`. Use pytest markers `@pytest.mark.unit|integration|e2e` and keep fixtures in `tests/conftest.py`.
- TypeScript/React: ESLint + TypeScript; follow existing component patterns in `src/agcluster/container/ui`. Use PascalCase for components, camelCase for hooks/utilities.
- Tailwind is locked to v3; avoid `@apply` in new styles—prefer utility classes or scoped CSS modules.

## Testing Guidelines
- Add unit tests for new services/models; integration tests for API surface changes; Playwright for end-to-end UI/agent flows.
- Aim to keep coverage gaps small (HTML report in `htmlcov/` from `pytest --cov`). Include edge cases around Docker/session lifecycle and file handling.
- For UI changes, pair Vitest component coverage with Playwright scenarios that validate auth, upload/download, and agent launch flows.
- Record any required Docker/ENV prerequisites in the test description to keep CI reproducible.

## Commit & Pull Request Guidelines
- Use conventional commits when possible (`feat:`, `fix:`, `chore:`, `docs:`); keep subjects imperative and under ~72 chars.
- PRs should include: concise summary, linked issue/Linear ticket, test plan with commands run, and screenshots/GIFs for UI changes.
- Keep commits scoped; avoid mixing backend and UI refactors unless tightly coupled. Update docs/config examples when behavior changes.
