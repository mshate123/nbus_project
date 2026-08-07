# Component Inventory

| Component | Evidence | Current responsibility | Rebuild disposition |
|---|---|---|---|
| FastAPI app/lifespan | `backend/main.py` | Create async engine, expose session factory, health check | Retain behavior; restructure config, health dependencies, and startup migration policy |
| API router | `backend/api/routes.py` | Account/rate reads, post, reverse, balance, statement | Retain endpoint concepts; split schemas/use cases and add auth/error contract |
| ORM model set | `backend/models.py` | Account, journal entry/line, rate schedule | Retain domain entities; redesign constraints and append-only enforcement |
| Posting service | `backend/engine/posting_service.py` | Validate balanced lines, lock accounts, insert entry/lines | Core to preserve; add transaction/error/concurrency tests |
| Balance service | `backend/engine/balance_service.py` | Derive normal-balance-adjusted balance and statement | Core to preserve; formalize ordering and missing-account semantics |
| Accrual service | `backend/engine/accrual_service.py` | Daily Decimal accrual and unique-key skip | Core intent to preserve; fix account/rate model and runner integration |
| Reversal service | `backend/engine/reversal_service.py` | Offset posted entry once | Core to preserve; add API/integration coverage |
| Migration | `backend/migrations/versions/001_initial.py` | Initial schema, enums, constraints, seed rates | Replace with clean migration history; preserve valid data shape only if migration required |
| Fixture factory | `backend/tests/fixtures/factories.py` | Chart, rates, demo entries, object factories | Split production seed from test fixtures; remove claims about missing seed CLI/mock use |
| SPA shell | `frontend/src/App.tsx` | Header and two tabs | Rebuild navigation/layout, preserve account/rate destinations |
| Account/statement UI | `frontend/src/components/AccountList.tsx`, `AccountStatement.tsx` | List accounts and inline statement/balance | Preserve core read flow; add accessible interaction and complete states |
| Rate UI | `frontend/src/components/RateSchedule.tsx` | Display tiers as percentages | Preserve behavior; add empty state and test DOM behavior |
| API client | `frontend/src/lib/api.ts` | Fetch `/api` resources | Preserve direct shapes; normalize `{error}`/FastAPI error handling |
| UI primitives | `frontend/src/components/ui/*` | Card, table, badge, button | Retain design-system role; regenerate consistently |
| K8s manifests | `infra/k8s/*` | Local deployments and CronJob | Reassess/remove unless deployment is in rebuild scope; current CronJob is broken |
