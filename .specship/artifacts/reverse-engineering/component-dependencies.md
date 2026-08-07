# Component Dependencies and Data Flow

## Request path
`frontend/src/components/*` -> `frontend/src/lib/api.ts` -> nginx `/api/` proxy in `frontend/nginx.conf` -> FastAPI router in `backend/api/routes.py` -> request-scoped `AsyncSession` from `backend/main.py` -> ORM/services -> PostgreSQL.

## Write path
`POST /api/journal-entries` -> Pydantic lines -> `PostingService.validate_entry` -> sorted UUID account locks -> `JournalEntry` and `JournalLine` flush -> route commit/refresh -> JSON response.

## Read path
`GET /accounts/{id}/balance` -> `BalanceService.get_balance` -> posted journal line aggregate -> normal-balance direction. Statement follows posted entries ordered by `posted_at` and line creation time, maintaining a Decimal running balance.

## Accrual path
Kubernetes CronJob intends to invoke `python -m backend.jobs.accrual`; that module is absent. The existing `AccrualService` reads account code `4000`, standard rate tier, active accounts, computes daily interest, and calls `PostingService` inside nested savepoints. A partial unique index is intended to make account/date accrual idempotent.

## Important dependency risks
- `backend/api/routes.py` imports top-level `models` and `engine`, coupling execution to `PYTHONPATH`/working directory conventions.
- `frontend/nginx.conf` assumes the backend service hostname `api`; Kubernetes frontend manifest exposes container port 3000 although nginx listens on 80.
- `docker-compose.yml` does not attach `localstack` as an explicit dependency of `api`, despite declaring LocalStack in the stack.
- The UI has no mutation path, so the only current E2E flow is read-only rate display.
