# Repository Map

## Scope and intent
This is a small full-stack double-entry ledger with daily interest accrual. The requested target is a clean rebuild, so this map distinguishes durable domain behavior from replaceable scaffolding.

## Topology
- `backend/`: Python API, ORM models, migrations, ledger engine, and tests.
- `frontend/`: React/Vite/TypeScript SPA, Tailwind/shadcn-style primitives, API client, and Vitest tests.
- `e2e/`: repository-level Playwright configuration and `smoke.spec.ts`.
- `docker-compose.yml`: PostgreSQL, LocalStack, app profile, and test profile.
- `infra/k8s/`: Minikube-oriented namespace, API/frontend Deployments and Services, ConfigMap/Secret, and accrual CronJob.
- `.kiro/specs/core-ledger/`: current requirements, design, error strategy, test strategy, and task ledger.
- `.kiro/hooks/`: untracked, disabled SpecShip observation hooks present before recon.

## Entrypoints
- API: `backend/main.py`, FastAPI app, `/health`, router inclusion.
- API routes: `backend/api/routes.py`, `/api/*`.
- Frontend: `frontend/src/main.tsx` -> `frontend/src/App.tsx`.
- Production frontend: `frontend/Dockerfile` -> nginx; proxy in `frontend/nginx.conf`.
- Migration entrypoint: `backend/alembic.ini` and `backend/migrations/env.py`.
- Scheduled accrual reference: `infra/k8s/accrual-cronjob.yaml` invokes missing `backend.jobs.accrual`.

## Current runtime evidence
- `docker compose config`: passes.
- `docker compose --profile test run --rm api-test`: 24 passed; 43.21% engine coverage; configured container threshold only 20%.
- `docker compose --profile test run --rm frontend-test`: 6 passed; 30.06% total reported coverage.
- Live API smoke: `/health` returned 200; `/api/accounts` returned `[]`; `/api/rate-schedule` returned three seeded rows.
- Playwright command was attempted twice and aborted by the tool runner before a result; treat E2E as unverified, not passing.
