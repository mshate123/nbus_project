# Code Quality Assessment

## High-risk gaps
1. Missing `backend.jobs.accrual` makes the scheduled production behavior nonfunctional (`infra/k8s/accrual-cronjob.yaml`).
2. `AUTH_STUB_TOKEN` is unused; every API route is public.
3. No API tests or mutation E2E tests cover the primary write/reversal flows.
4. Coverage gates are materially weaker than the spec claims.
5. Database does not enforce append-only posted rows or entry-level balance.
6. Rate-tier model is incomplete and inconsistent between migration and fixture data.
7. Kubernetes frontend port 3000 conflicts with nginx port 80.

## Medium-risk debt
- Module-global engine/session factory complicates test isolation and configuration.
- Route response mapping is duplicated for posted and reversing entries.
- Accrual catches broad `Exception`, converts domain/database failures into result strings, and does not explicitly commit.
- `BalanceService` accepts `str` IDs while callers and ORM expect UUIDs.
- `PostingService` validates `Decimal(str(...))` but invalid numeric strings can escape as decimal exceptions rather than `PostingError`.
- `normal_balance` is unconstrained text.
- `DateTime` ordering lacks a deterministic entry-ID tie-breaker.
- Migration downgrade uses `CASCADE`, which is risky for shared/partial schemas.
- Frontend test excludes all test files from TypeScript compilation, and shallow tests can pass without rendering DOM.

## Dead or misleading code/configuration
- `frontend/.env.example`/Kubernetes `VITE_API_BASE_URL` are dead because the client hardcodes `/api`.
- LocalStack/S3 variables and Compose service have no consuming code.
- Fixture factory docstring references `seed.py` and UI mock fallback responses, neither found in tracked files.
- Kubernetes accrual CronJob points to a nonexistent module.
- README says Playwright directory has no runnable tests, but `e2e/smoke.spec.ts` is tracked; README is stale.
- `frontend/src/components/ui/button.tsx` exists but no current feature uses Button.

## Clean rebuild recommendation
Keep the ledger domain model and invariants as behavioral inputs. Rebuild boundaries around settings, repository/use-case services, API schemas, job runner, database constraints, browser flows, and deployment. Remove unused LocalStack/S3 and Minikube manifests unless the new contract explicitly requires them.
