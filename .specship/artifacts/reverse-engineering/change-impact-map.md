# Change Impact Map for Clean Rebuild

## Likely replacement areas

| Area | Current files | Impact | Rebuild action |
|---|---|---|---|
| Domain/schema | `backend/models.py`, `backend/migrations/` | Data integrity and compatibility | Redesign schema/constraints first; decide migration/data import policy |
| Configuration/runtime | `backend/main.py`, `.env.example`, Dockerfiles | Startup, health, secrets | Replace with typed settings and explicit app/test profiles |
| Posting API | `backend/api/routes.py`, `engine/posting_service.py` | Core write contract | Preserve balanced atomic posting; add route tests and structured errors |
| Balance/statement | `engine/balance_service.py`, frontend statement components | Customer-visible balances | Preserve direct read semantics and deterministic ordering |
| Reversal | `engine/reversal_service.py`, route | Auditability | Preserve offset-only reversal and one-reversal rule; expose browser flow |
| Accrual | `engine/accrual_service.py`, missing `backend.jobs.accrual`, CronJob | Scheduled money movement | Implement explicit runner/commit/retry/idempotency contract |
| Rate schedule | migration, factories, route, UI | Interest calculation | Resolve tier/rate ownership and conflicting seed data |
| Frontend | `frontend/src/App.tsx`, components, API client | User workflow | Rebuild shell and accessible feature states around contract |
| E2E | `e2e/smoke.spec.ts`, Playwright config | Release proof | First fix task: deterministic container execution; then full CRUD-like ledger flow |
| Deployment | Compose, nginx, K8s | Operability | Choose one supported deployment path; remove broken/unconsumed manifests |

## Files/areas to avoid treating as source of truth
- `.kiro/specs/core-ledger/tasks.md`: useful intent/history, not proof of completion; T6.3 is open and several checked tasks are contradicted by implementation.
- `backend/tests/fixtures/factories.py`: test/demo data only; it conflicts with migration seeds and must not define production truth.
- `README.md`: contains stale E2E and test-result statements; verify against commands.
- `.kiro/hooks/`: pre-existing untracked disabled hooks; do not modify during recon.

## Explicit triage task
**REBUILD-T0.1: Stabilize browser validation path.** Root cause is now confirmed in `e2e-triage.md`: host Playwright lacks its Chromium executable, and the supported container path exposes an nginx `proxy_pass` trailing-slash rewrite that turns `/api/rate-schedule` into `/rate-schedule` and receives backend 404. Rebuild task T0.1a must preserve `/api` through the proxy, keep Chromium containerized, and prove the smoke test reaches a typed pass/fail result. Acceptance: `/api/rate-schedule` is 200 through nginx; smoke test passes in the container; direct backend/proxy checks distinguish routing from backend failures; no unrelated feature changes. This is a planning/build task, not a recon edit.

## Downstream risks
- Existing data cannot be safely assumed compatible because rates and schema semantics conflict.
- Changing missing-account semantics or error shape can break clients.
- Removing LocalStack/K8s is safe only if export and deployment are explicitly out of rebuild scope.
