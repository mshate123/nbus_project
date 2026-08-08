# nbus_project — Core Ledger

Full-stack double-entry ledger with balance, statement, reversal, and rate-schedule views. Docker Compose is the canonical application and test entrypoint; no host Python, Node.js, or pnpm installation is required.

## Architecture

- **Frontend:** React 18 + TypeScript 5 + Vite, TanStack Query, Tailwind CSS, and shadcn-style components. Production assets are served by nginx on port 3000.
- **Backend:** Python 3.12 + FastAPI, Pydantic, SQLAlchemy 2 async, Alembic, and Uvicorn on port 8000.
- **Database:** PostgreSQL 15. Alembic applies the migrations in `backend/migrations/versions/`.
- **API boundary:** REST endpoints are under `/api`. The frontend nginx proxy preserves the `/api` prefix when forwarding to the backend.
- **Browser verification:** Playwright runs in the dedicated Compose `e2e-test` container with Chromium installed in the image.
- **Local infrastructure:** Docker and Docker Compose orchestrate the full stack — PostgreSQL, the FastAPI backend, the Vite/React frontend, and isolated test containers for backend, frontend, and Playwright e2e.

The current Kiro specification and its contract/test artifacts are in `.kiro/specs/core-ledger/`. Repository reconnaissance evidence is retained in `.specship/artifacts/reverse-engineering/`.

## Prerequisites

For the documented Docker Compose workflow:

- Docker Engine with the Compose plugin (`docker compose`)
- Ports 3000, 4566, 5432, and 8000 available

No host Python, Node.js, or pnpm installation is required; the Compose images provide them. If you run frontend commands directly on the host instead of through Docker, install:

- Node.js 26.x (the frontend image uses `node:26-bookworm-slim`)
- pnpm 11.20.0 (declared by `frontend/package.json`)

## Environment

Compose supplies the normal local values. `.env.example` documents equivalent host-oriented values; do not commit real credentials.

| Variable | Required | Local value/source |
|---|---:|---|
| `DATABASE_URL` | Yes for API/test containers | Compose sets PostgreSQL URLs for `api` and `api-test` |
| `AUTH_STUB_TOKEN` | Yes for the API container | Compose value: `dev-token` |

## Start and stop

Start the application stack:

```bash
docker compose --profile app up --build
```

Run it in the background:

```bash
docker compose --profile app up -d --build
```

Service URLs:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- FastAPI docs: <http://localhost:8000/docs>
- Backend health: <http://localhost:8000/health>

Verify the API and frontend proxy:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/api/rate-schedule
curl -fsS http://localhost:3000/api/rate-schedule
```

Stop containers without deleting volumes:

```bash
docker compose --profile app down
```

Reset local persisted database and LocalStack data (destructive):

```bash
docker compose --profile app down -v
docker compose --profile app up -d --build
```

## Tests

### Run all tests

This single command starts the app stack for E2E tests, runs the full backend/API suite, runs the frontend suite, runs E2E tests, and removes the test containers and volumes when finished:

```bash
docker compose --profile app up -d --build && docker compose --profile test run --rm api-test && docker compose --profile test run --rm frontend-test && docker compose --profile app --profile test run --rm e2e-test; status=$?; docker compose --profile app --profile test down -v; exit $status
```

This command was verified successfully in the current repository.

### Run individual suites

#### Backend/API tests

Run the full backend suite, including unit, integration, property, and API contract-shape tests:

```bash
docker compose --profile test run --rm api-test
```

To run an individual backend suite:

```bash
# Unit tests
docker compose --profile test run --rm api-test pytest tests/unit -q

# Integration and database tests
docker compose --profile test run --rm api-test pytest tests/integration -q

# Property tests
docker compose --profile test run --rm api-test pytest tests/property -q

# API contract-shape tests
docker compose --profile test run --rm api-test pytest tests/api -q
```

The API contract tests are located in `backend/tests/api/`; there is no separate Compose service named `contract-test`.

#### Frontend tests

```bash
docker compose --profile test run --rm frontend-test
```

The current frontend suite is Vitest-based and is discovered from `frontend/tests/`.

#### E2E tests

Start the app stack first, then run the dedicated browser container:

```bash
docker compose --profile app up -d --build
docker compose --profile app --profile test run --rm e2e-test
docker compose --profile app --profile test down -v
```

The browser runner uses Chromium from its container image rather than a host browser cache. 

## Typecheck, build, and lint

The frontend `build` script runs TypeScript checking before creating the Vite production bundle. Run it through the frontend test image:

```bash
docker compose --profile test run --rm frontend-test pnpm build
```

# MY JOURNEY:

I began by researching fintech project ideas with Claude and Gemini and chose to build a **Core Ledger & Interest Accrual** system. After the initial unit tests, integration tests, and application stack were healthy, further research led me to a public repository that demonstrated how to set up SpecShip for Kiro. I borrowed heavily from its templates, hooks, and MCPs for this exercise to reduce churn and unnecessary token usage.

I installed the SpecShip prerequisites and added Kiro Superpowers for brainstorming, writing implementation plans, subagent-driven development, TDD, and debugging. I then performed a repository reconnaissance and synthesized the findings back into the original codebase.

### Reconnaissance prompt

> Using SpecShip recon, reverse engineer this repository thoroughly into `.specship/artifacts/reverse-engineering/`.
>
> I am planning a complete clean rebuild, not an incremental patch. Analyze:
>
> 1. The full architecture, component mapping, technology stack, and data models.
> 2. Existing Kiro specs in `.kiro/specs/`, cross-referenced against current implementation gaps.
> 3. Dead code, anti-patterns, technical debt, and components that should be restructured or removed.
> 4. Baseline behaviors to preserve versus legacy structures to retire.
The reconnaissance identified a Playwright E2E routing issue that caused the browser test to fail. I recorded it as a follow-up triage task so the recon could be completed without losing the finding. I later used Kiro's investigation workflow to create an RCA triage issue, then incorporated the triage fix into Spec mode while rewriting the specifications.

### Test organization

```
backend/tests/
  unit/
  integration/
  property/
  api/
  fixtures/
frontend/tests/
  unit/
    components/
e2e/
  helpers/
  playwright.config.ts
  preflight.spec.ts
  smoke.spec.ts
```


I used TDD with red/green testing guardrails and organized the project around Docker Compose profiles for the application and test stacks.
I switched to another model to perform code reviews, fixed all found issues and added final polish.

### Coverage and remaining work

The application and test workflows run successfully, but the implementation has not yet met all target coverage thresholds. The current state is documented here rather than hidden:

- **Backend engine target:** 70%; current: **84%** (61 tests passing; `balance_service` 100%, `posting_service` 97%, `accrual_service` 96%, `reversal_service` 36%).
- **Frontend target:** 60%; current: **30%** (6 tests passing; `RateSchedule` 100%). Pre-existing gap — no tests for `AccountList`, `AccountStatement`, `App`.
- **E2E (Playwright):** 7 tests passed (preflight health, readiness, frontend, seeding, proxy contract, smoke).

The remaining backend coverage gap is `reversal_service` (36%). Frontend coverage requires additional component tests for `AccountList`, `AccountStatement`, and `App` to meet the 60% threshold.

The final stack verification confirmed healthy PostgreSQL, API, and frontend services; API health returned `{"status":"ok"}`; the frontend returned HTTP 200; and the frontend proxy returned the seeded rate schedule successfully.
