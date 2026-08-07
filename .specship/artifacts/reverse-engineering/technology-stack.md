# Technology Stack

## Declared stack
Evidence: `README.md`, `backend/pyproject.toml`, `frontend/package.json`, Dockerfiles, and `docker-compose.yml`.

- Runtime: Python 3.12 (`backend/Dockerfile`), Node 26 (`frontend/Dockerfile`).
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg, Alembic, Uvicorn.
- Backend tests: pytest, pytest-asyncio, pytest-cov, Hypothesis, testcontainers dependency, httpx, aiosqlite dependency.
- Frontend: React 18, TypeScript 5, Vite 5, TanStack Query v5, Vitest, Playwright, Tailwind CSS 3, Radix Slot, CVA, lucide-react.
- Package manager: pnpm 11 with `frontend/pnpm-lock.yaml` and `packageManager` in `frontend/package.json`.
- Persistence: PostgreSQL 15; numeric money columns are PostgreSQL `NUMERIC(18,4)`.
- Local object-store dependency: LocalStack 3 configured for S3, but no S3 implementation is present in the inspected source.
- Deployment: Docker Compose and Minikube Kubernetes manifests; nginx serves the built SPA and proxies `/api/`.

## Version/quality observations
- Dependency ranges are mostly open (`>=` or `^`), so a clean rebuild should pin a tested dependency set.
- `backend/pyproject.toml` declares a 70% coverage threshold, while Docker commands enforce only 20%; `frontend/vite.config.ts` enforces only 5% thresholds and the container reports about 30%.
- The frontend build emits a CJS Vite API deprecation warning and a module-type warning for `postcss.config.js`.
- README says Node 26 and pnpm 11; actual container test output used Python 3.12.13 and Vitest 1.6.1.
