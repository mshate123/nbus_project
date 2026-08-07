# Test Baseline

## Commands and results

| Command | Result | Evidence/notes |
|---|---|---|
| `docker compose config` | PASS | Compose rendered successfully. |
| `docker compose --profile test run --rm api-test` | PASS: 24 passed | 2 integration, 3 property, 19 unit; engine coverage 43.21%; Docker threshold 20%. |
| `docker compose --profile test run --rm frontend-test` | PASS: 6 passed | One test file, all tests for `RateSchedule`; reported total coverage 30.06%. |
| `curl /health`, `/api/accounts`, `/api/rate-schedule` against app | PASS | Health OK; accounts empty; three rates returned. |
| Playwright E2E host run | FAIL: browser executable missing | `CI=1 pnpm exec playwright test --config ../e2e/playwright.config.ts --reporter=line` reached Playwright but failed before launch because the host Chromium headless shell was absent from `~/Library/Caches/ms-playwright`. |
| Playwright E2E container run | FAIL: smoke timeout | Containerized Playwright launched Chromium and loaded `/`, but `GET /api/rate-schedule` returned 404 through nginx; the test timed out waiting for an OK response. |
| Direct API vs frontend proxy | API PASS, proxy FAIL | `localhost:8000/api/rate-schedule` returned 200; `localhost:3000/api/rate-schedule` returned 404. Root cause is recorded in `e2e-triage.md`. |
| `git status` | BASELINE CAPTURED | Only pre-existing untracked `.kiro/hooks/*` files were present before recon artifacts. |

## Test gaps
- No API route tests for request/response/error contracts.
- No reversal tests despite implemented service and route.
- No accrual integration/idempotency tests.
- Property tests validate pure input invariant, not persisted posting behavior; spec asks for post-write validation.
- Integration fixture says testcontainers but uses `DATABASE_URL` and creates schema directly; no testcontainers lifecycle is implemented in the file.
- No frontend tests for App, AccountList, AccountStatement, API errors, empty accounts, or accessibility.
- Declared 70% backend and 60% frontend targets are not enforced by active Docker commands.

## E2E triage task
Create a rebuild task: run the smoke test from a deterministic container with the app stack healthy; then add a create/post -> verify statement -> reverse -> verify balance flow. Record browser evidence. Do not treat the interrupted host invocation as a product failure until the command path itself is made observable.
