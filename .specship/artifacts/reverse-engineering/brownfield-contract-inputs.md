# Brownfield Contract Inputs

## Scope Classification
- Type: clean-rebuild / architecture replacement, informed by brownfield recon
- Repo: `/Users/heathernoe/Desktop/gitrep/nbus_project`
- Affected components: full backend domain/API, frontend ledger UI, tests, and deployment path
- Recon mode: Full, because the rebuild crosses persistence, API, UI, scheduling, tests, and deployment.

## Existing Behavior To Preserve
1. When a balanced Decimal journal entry is submitted, the current engine validates it, locks accounts in sorted UUID order, and writes one posted entry with lines atomically (`backend/engine/posting_service.py`).
2. When a balance is requested, the current service derives it from posted lines using account normal-balance direction (`backend/engine/balance_service.py`).
3. When a posted entry is reversed, the current service creates a linked offsetting entry and rejects duplicate/self-reversal (`backend/engine/reversal_service.py`).
4. When accrual runs, the intended service computes daily interest with Decimal and uses account/date uniqueness for idempotency (`backend/engine/accrual_service.py`, migration).
5. The current UI provides account list -> statement expansion and a rate-schedule tab using direct API response shapes.

## New Or Changed Behavior To Define
1. Add a real, executable accrual job/command; the current Kubernetes reference points to missing `backend.jobs.accrual`.
2. Add authenticated route behavior or explicitly remove the unused auth promise.
3. Define account-to-rate-tier ownership; current accrual always reads `standard` despite requirements saying per-account tier.
4. Add API and browser coverage for posting, reversal, idempotency, and error paths.
5. Make deployment configuration coherent: nginx port, API proxy, readiness, migrations, and secrets.
6. Stabilize E2E orchestration after the prior `pnpm e2e` invocation was aborted before yielding a result.

## Regression Tests To Generate
1. Balanced/unbalanced/zero/precision-invalid entry behavior and no partial writes.
2. Concurrent ten-post scenario with exact final balance.
3. Balance and statement ordering/running-balance behavior for debit- and credit-normal accounts.
4. Reversal success, duplicate reversal, self-reversal, and non-posted rejection.
5. Accrual calculation, zero/negative balance handling, duplicate account/date no-op, and commit behavior.
6. API response shapes and error contract.
7. Browser: load seeded accounts/rates; post -> verify statement/balance; reverse -> verify offset and final balance.

## Files Likely To Change
| Area | Why | Risk | Required tests |
|---|---|---|---|
| New domain/schema modules | Clean boundaries and constraints | Data compatibility | migration/integration |
| API routes/schemas | Contract and auth | Client breakage | API contract tests |
| Accrual runner | Scheduled behavior currently absent | Duplicate money movement | idempotency/job tests |
| Frontend feature components | Complete user workflow | UI regression | Vitest + Playwright |
| Compose/deploy config | Make runtime deterministic | Startup failures | smoke/readiness tests |
| E2E config/specs | Stabilize browser proof; REBUILD-T0.1 | False release confidence | containerized E2E |

## Files To Avoid Treating As Truth
- `.kiro/specs/core-ledger/tasks.md` checked statuses; verify every claim against code/tests.
- `backend/tests/fixtures/factories.py` for production seed values.
- `README.md` for current test/E2E status.
- Existing K8s manifests until their runtime assumptions are corrected.

## Local Conventions Workers Must Follow
- Use exact Decimal/NUMERIC money arithmetic.
- Keep direct list/object API shapes unless the new contract deliberately versions them.
- Use async DB access and deterministic account lock ordering.
- Use Tailwind/shadcn-style primitives; no inline styles.
- Every UI feature covers happy, empty, loading, error, and responsive states.
- Tests must run in declared container paths; record RED/GREEN evidence for new tests.

## Baseline Commands
| Command | Current result | Notes |
|---|---|---|
| `docker compose config` | Pass | Configuration parses. |
| `docker compose --profile test run --rm api-test` | 24 passed, 43.21% engine coverage | Does not enforce declared 70/85/75% thresholds. |
| `docker compose --profile test run --rm frontend-test` | 6 passed, 30.06% coverage | Only RateSchedule has tests. |
| `curl` health/accounts/rates | Pass | Health OK; accounts empty; three rates. |
| `pnpm e2e` | Unverified/interrupted | Tool runner aborted before result; triage as REBUILD-T0.1. |

## Open Questions Blocking Contract
- Is statement export/S3 required in the clean rebuild, or should LocalStack be removed?
- Is Minikube a supported deployment target or historical scaffolding?
- Should missing accounts remain zero/empty or become 404?
- What is the authoritative rate schedule and how is a tier assigned to an account?
- What exact auth behavior is required by the rebuild?
- Is existing database data to be migrated, or is this a greenfield schema cutover?
